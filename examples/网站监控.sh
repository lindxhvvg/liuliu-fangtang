#!/bin/bash
# 网站监控：每 5 分钟探测，挂了才推（避免轰炸）
# crontab: */5 * * * * /path/to/网站监控.sh
FANGTANG="http://你的服务器:8787/send?key=你的key"
URL="https://你要监控的网站.com"
CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$URL")
if [ "$CODE" != "200" ]; then
  FLAG="/tmp/site_down_$(echo $URL | md5sum | cut -c1-8)"
  [ -f "$FLAG" ] && exit 0          # 已经推过，不重复轰炸
  curl -s "$FANGTANG" --data-urlencode "title=🔴 网站挂了" --data-urlencode "desp=$URL 返回 HTTP $CODE"
  touch "$FLAG"
else
  rm -f /tmp/site_down_* 2>/dev/null # 恢复了，清标志
fi
