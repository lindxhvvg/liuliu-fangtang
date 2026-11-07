# Windows 计划任务接入（不装任何东西）

1. Win+R → `taskschd.msc` → 创建基本任务
2. 触发器：按需（每天/登录时/事件）
3. 操作：启动程序 → `curl.exe`（Win10+ 自带）
   参数：
   ```
   -s "http://你的服务器:8787/send?key=你的key" --data-urlencode "title=开机自检完成"
   ```
4. 完成。以后每次触发，微信响一声。
