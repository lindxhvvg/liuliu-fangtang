#!/bin/bash
# cron 定时提醒：每天 8:30 推天气/日程/任何文字
# crontab: 30 8 * * * /path/to/定时提醒.sh
FANGTANG="http://你的服务器:8787/send?key=你的key"
curl -s "$FANGTANG" --data-urlencode "title=早上好" --data-urlencode "desp=今天也要记得看盘前 30 分钟的公告"
