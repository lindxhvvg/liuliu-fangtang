# -*- coding: utf-8 -*-
# 下载/长任务完成推送：在任务末尾加一行
import urllib.request, urllib.parse
def fangtang(title, desp=""):
    cfg = {"url": "http://你的服务器:8787/send", "key": "你的key"}
    sep = "&" if "?" in cfg["url"] else "?"
    urllib.request.urlopen("%s%s%stitle=%s&desp=%s" % (
        cfg["url"], sep, "key=" + cfg["key"],
        urllib.parse.quote(title), urllib.parse.quote(desp)), timeout=10)

# 用法：任务跑完调用
fangtang("✅ 下载完成", "模型权重 12GB 已就位，耗时 43 分钟")
