# -*- coding: utf-8 -*-
"""六六方糖 · 自建开源推送服务（2026-11-07）

原理（与 Server酱 同源，可验证）：
  微信公众号「测试号」免费向所有人开放，提供模板消息接口：
    1. 用户扫码申请测试号 → 得 appID / appsecret
    2. 用户自己关注该测试号 → 得自己的 openid
    3. 服务端用 appID+appsecret 换 access_token（7200s 有效，需缓存）
    4. POST template/send → 关注者的微信立刻收到消息
  本服务把这四步封装成一行 HTTP：
    GET /send?key=你的key&title=标题&desp=内容

设计（从零、零第三方依赖、单文件）：
  · 纯 stdlib：http.server + urllib，无 flask 无 requests
  · 多用户：keys.json 里 key → openid 映射，谁部署谁发 key
  · token 缓存与自动续期（并发安全）
  · /health 健康端点（供监控 ping）
  · 全部请求进 log/requests.log 审计
  · 失败重试 1 次（token 过期自动刷新）

跑法：
  python3 方糖服务.py            # 默认 0.0.0.0:8787
  方糖服务.py --port 8788

开源约定（README 见同目录）：MIT，署名「六六量化 · 从零系列」。
"""
import os, sys, json, time, threading, urllib.request, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

WS = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(WS, "config.json")          # {"app_id": "", "app_secret": "", "template_id": ""}
KEYS = os.path.join(WS, "keys.json")           # {"your_key": {"openid": "oXXX", "name": "德轩"}}
LOG = os.path.join(WS, "log")
PORT = 8787
W_API = "https://api.weixin.qq.com/cgi-bin"

_lock = threading.Lock()
_token = {"v": "", "exp": 0}


def cfg():
    return json.load(open(CFG, encoding="utf-8"))


def keys():
    try:
        return json.load(open(KEYS, encoding="utf-8"))
    except Exception:
        return {}


def log(line):
    os.makedirs(LOG, exist_ok=True)
    with open(os.path.join(LOG, "requests.log"), "a", encoding="utf-8") as f:
        f.write("[%s] %s\n" % (time.strftime("%m-%d %H:%M:%S"), line))


def get_token(force=False):
    """access_token 缓存 7200s，提前 300s 续期；线程安全"""
    with _lock:
        if not force and _token["v"] and time.time() < _token["exp"] - 300:
            return _token["v"]
        c = cfg()
        u = ("%s/token?grant_type=client_credential&appid=%s&secret=%s"
             % (W_API, c["app_id"], c["app_secret"]))
        j = json.loads(urllib.request.urlopen(u, timeout=10).read().decode("utf-8"))
        if "access_token" not in j:
            raise RuntimeError("token 失败：%s" % json.dumps(j, ensure_ascii=False)[:120])
        _token["v"] = j["access_token"]
        _token["exp"] = time.time() + j.get("expires_in", 7200)
        return _token["v"]


def send_custom(openid, title, desp):
    """客服消息：普通会话形态，有横幅有提示音（不折叠）。
    限制：用户须 48h 内与测试号互动过（发过消息）。失败不阻塞模板消息。"""
    try:
        body = {"touser": openid, "msgtype": "text",
                "text": {"content": "🔔 %s\n%s" % (title[:60], desp[:400])}}
        u = "%s/message/custom/send?access_token=%s" % (W_API, get_token())
        req = urllib.request.Request(u, data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        j = json.loads(urllib.request.urlopen(req, timeout=10).read().decode("utf-8"))
        if j.get("errcode") == 45015:   # 超 48h 互动窗口
            j["note"] = "客服消息窗口过期（请用户给测试号发条消息）"
        return j
    except Exception as e:
        return {"errcode": -2, "errmsg": str(e)[:100]}


def send_wechat(openid, title, desp):
    """双发：客服消息（有提醒）+ 模板消息（留档）"""
    r_custom = send_custom(openid, title, desp)
    c = cfg()
    body = {
        "touser": openid,
        "template_id": c["template_id"],
        "topcolor": "#FF0000",
        "data": {
            "title": {"value": title[:40], "color": "#173177"},
            "content": {"value": desp[:500].replace("\n", "<br/>"), "color": "#173177"},
        },
    }
    for attempt in (1, 2):   # token 过期自动刷新重试 1 次
        try:
            u = "%s/message/template/send?access_token=%s" % (W_API, get_token(force=(attempt == 2)))
            req = urllib.request.Request(u, data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                                         headers={"Content-Type": "application/json"})
            j = json.loads(urllib.request.urlopen(req, timeout=10).read().decode("utf-8"))
            if j.get("errcode") == 40001 and attempt == 1:
                continue   # token 失效 → 强刷重试
            # 双发合并结果：模板为主，客服为辅（客服成功标注 remind_pushed）
            if r_custom.get("errcode") == 0:
                j["remind_pushed"] = True
            return j
        except Exception as e:
            if attempt == 2:
                return {"errcode": -1, "errmsg": str(e)[:120]}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, obj):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        self._handle()

    def do_POST(self):
        self._handle()

    def _handle(self):
        try:
            if self.path.startswith("/health"):
                self._send(200, {"ok": True, "service": "六六方糖", "keys": len(keys())})
                return
            if not self.path.startswith("/send"):
                self._send(404, {"errcode": 404, "errmsg": "only /send and /health"})
                return
            # 参数：query 或 JSON body 都收
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if self.command == "POST":
                ln = int(self.headers.get("Content-Length", 0) or 0)
                if ln:
                    raw = self.rfile.read(ln).decode("utf-8", errors="replace")
                    ct = (self.headers.get("Content-Type") or "")
                    if "json" in ct:
                        try:
                            body = json.loads(raw)
                            for k, v in body.items():
                                qs.setdefault(k, [v])
                        except Exception:
                            pass
                    else:
                        # form-urlencoded 兼容（curl --data-urlencode 默认格式）——
                        # 2026-11-07 实测：只解析 JSON 导致 curl 表单测试全变（无标题）（无内容）
                        for k, v in urllib.parse.parse_qs(raw).items():
                            qs.setdefault(k, v)   # parse_qs 的值已是 list，勿再包一层（嵌套 list 曾致 500）
            key = (qs.get("key") or [""])[0]
            title = (qs.get("title") or ["（无标题）"])[0]
            desp = (qs.get("desp") or [""])[0]
            user = keys().get(key)
            if not user:
                self._send(403, {"errcode": 403, "errmsg": "key 无效"})
                log("DENY key=%s…" % key[:6])
                return
            r = send_wechat(user["openid"], title, desp or "（无内容）")
            ok = r.get("errcode") == 0
            log("%s key=%s… title=%s → %s" % ("OK" if ok else "FAIL", key[:6], title[:30],
                                              json.dumps(r, ensure_ascii=False)[:80]))
            self._send(200 if ok else 502, r)
        except Exception as e:
            log("ERROR %s" % str(e)[:120])
            self._send(500, {"errcode": 500, "errmsg": str(e)[:120]})


if __name__ == "__main__":
    port = 8787
    if "--port" in sys.argv:
        port = int(sys.argv[sys.argv.index("--port") + 1])
    print("六六方糖 · 自建推送服务 → 0.0.0.0:%d" % port)
    print("  GET /send?key=xx&title=xx&desp=xx   推送到关注者微信")
    print("  GET /health                          健康检查")
    print("  配置：%s（app_id/app_secret/template_id）" % CFG)
    print("  用户：%s（key → openid）" % KEYS)
    ThreadingHTTPServer(("0.0.0.0", port), H).serve_forever()
