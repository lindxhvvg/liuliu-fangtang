# -*- coding: utf-8 -*-
# 桌宠/小游戏/任何 Python 程序的事件推送（六六系作品通用）
import urllib.request, urllib.parse
FANGTANG = "http://你的服务器:8787/send?key=你的key"

def push(title, desp=""):
    urllib.request.urlopen(FANGTANG + "&title=" + urllib.parse.quote(title)
                           + "&desp=" + urllib.parse.quote(desp), timeout=10)

# 例：桌宠提醒喝水
# push("🐱 桌宠提醒", "你已经连续写码 2 小时了，喝水休息")
# 例：大肥鱼抓到新单
# push("🐟 大肥鱼", "新订单进来了，金额 ¥299")
