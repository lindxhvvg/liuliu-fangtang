# 六六方糖 · 开源自建推送服务

> **一行 HTTP，推到你微信。任何程序都能挂上来。**
> 自建版 Server酱（方糖）替代品：从零实现，纯 Python 标准库，单文件，零第三方依赖。MIT 协议。

量化引擎的成交告警只是它的第一个客户。定时提醒、网站监控、下载完成、
桌宠事件、Git push 通知、NAS 状态……**你电脑和服务器上发生的一切，
都值得用一行 URL 送到你微信里。**（examples/ 目录有现成脚本）

MLA 引用（原理依据）：腾讯微信团队. *微信公众平台测试号接口文档：模板消息*[EB/OL]. https://mp.weixin.qq.com/wiki, 2026.

---

## 它是什么

一个自托管的推送服务：任何程序（服务器脚本、cron、树莓派、甚至浏览器地址栏）
访问一行 URL，你的微信立刻收到消息。

```
GET http://你的服务器:8787/send?key=你的key&title=服务器告警&desp=CPU 95%
```

## 为什么自己造这个轮子

| 方案 | 问题 |
|------|------|
| Server酱（方糖） | 免费额度每天 5 条，超出收费；数据过第三方 |
| 企业微信应用 | 需要企业资质 |
| Bark | iOS 专属 |
| **六六方糖（本仓库）** | **免费无限条 · 数据只过自己的服务器 · 单文件 200 行** |

## 原理（可验证）

微信公众号「测试号」向所有人免费开放模板消息接口（腾讯微信团队，微信公众平台接口文档）。
本服务封装：access_token 缓存与自动续期 → 模板消息下发 → 多用户 key 映射。

```
你的程序 ──GET /send──▶ 六六方糖(自建) ──模板消息──▶ 微信服务器 ──▶ 你的微信
```

## 部署（三步，10 分钟）

### ① 申请微信测试号（1 分钟）

打开 https://mp.weixin.qq.com/debug/cgi-bin/sandboxinfo?action=sandboxinfo
→ 微信扫码登录 → 得到 **appID** 和 **appsecret**（页面上直接显示）。

### ② 关注测试号拿 openid（30 秒）

同一页面下方「测试号二维码」→ 用你的微信扫码关注 → 页面显示你的 **openid**（一串 o 开头的字符）。
再在页面上方「模板消息接口」→「新增测试模板」：
- 模板标题：`方糖推送`
- 模板内容：`{{title.DATA}}\n{{content.DATA}}`
- 得到 **模板 ID**。

### ③ 配置并启动

```bash
# config.json
{"app_id": "wxXXXX", "app_secret": "XXXX", "template_id": "XXXX"}

# keys.json
{"我的key": {"openid": "oXXXX", "name": "示例用户"}}

python3 方糖服务.py
```

测试：

```bash
curl "http://127.0.0.1:8787/send?key=我的key&title=你好&desp=第一条推送"
```

微信立刻收到。🎉

## API

| 端点 | 方法 | 参数 | 说明 |
|------|------|------|------|
| `/send` | GET/POST | `key`(必填) `title` `desp` | 推送消息，JSON 返回 errcode |
| `/health` | GET | — | `{"ok":true,"keys":N}` 监控用 |

- POST 支持 JSON body：`{"key":"xx","title":"xx","desp":"xx"}`
- key 无效 → 403；token 过期自动刷新重试一次；全部请求进 `log/requests.log`

## 接入示例（任何语言）

```bash
# bash / cron
curl "http://服务器:8787/send?key=我的key&title=备份完成&desp=耗时 3 分钟"

# Python（本项目作者用法：量化系统成交/告警推送）
urllib.request.urlopen("http://127.0.0.1:8787/send?key=k&title=成交 BUY&desp=@254.22 ×1941")

# 浏览器地址栏
http://服务器:8787/send?key=我的key&title=上班打卡
```

## 安全建议

- 只放行给你信任的来源（防火墙/内网/反代加鉴权）
- key 视为密码：泄露就换（keys.json 里删旧加新）
- 服务器建议 HTTPS 反代（nginx + Let's Encrypt）——公网明文传输标题会被中间人看到

## 已知边界（诚实清单）

- 测试号模板消息有频率限制（腾讯未公开具体数值，社区经验约每分钟几十条）——告警场景足够，营销场景别用
- 测试号是微信"未认证"通道，腾讯保留调整权利——生产环境可无缝替换为认证服务号（同一接口）
- 模板内容上限：title 40 字 / desp 500 字（超出截断）

## 来源与致谢

- 诞生于「六六量化」项目的告警需求：量化引擎成交/异常 → 推开发者微信
- 原理同源：Server酱（方糖）——向它致敬，它证明了这条路可行
- 作者：六六（Liuliu）· 2026-11 · 从零系列
- License: MIT


## 做成系统服务（systemd，开机自启+崩溃自拉）

```bash
sudo cp fangtang.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now fangtang     # 启动+设为开机自启
systemctl status fangtang                # 查看状态
journalctl -u fangtang -f                # 跟日志
```

单元内置轻量化限制（适配小内存服务器）：`MemoryMax=50M`、`CPUQuota=10%`——
崩溃 5 秒后自动重启，不占量化引擎的资源。

## 云端脑接入（作为量化系统的告警通道）

量化引擎（AI盘服务.py）的 `push_event()` 支持三个通道，按 config 优先级自动选择：
1. `fangtang_url`（自建方糖，**优先**）→ 2. `serverchan_key`（Server酱）→ 3. 排队文件

config.json 加一行即切换：
```json
{"fangtang_url": "http://127.0.0.1:8787/send?key=我的key"}
```
