# Market Trading Hours

为 SPXW 0DTE 常规交易策略生成 Google Calendar 可订阅日历。正常交易日 09:30–16:00 ET，提前收盘 09:30–13:00 ET，周末及休市日无事件。America/New_York 自动处理夏令时；ICS 用 UTC 时间，Google 根据显示时区转换。事件为透明（不占用忙碌状态）。不代表非到期 SPX、GTH 或 ES 全时段，也不用于驱动真实订单。

## 安装
1. 创建 Public 仓库 `market-trading-hours`，上传本目录的五个普通文件（脚本、测试、快照、ICS、README）。
2. 单独创建 `.github/workflows/update-calendar.yml`，粘贴工作流。Actions → Update Market Trading Hours → Run workflow。
3. 初始 ICS 已预生成，公开上传后订阅 `https://raw.githubusercontent.com/rickeylau/market-trading-hours/main/market-trading-hours.ics#1`。
4. 确认新时间块后，隐藏或删除旧的固定 US Trading Time 重复事件。保留 Market Holidays 用于显示节假日名称。

## 更新与验证
- 每天 UTC 07:13，读取 `rickeylau/market-holidays/main/holidays.json`。源任务计划 UTC 06:23；GitHub 调度可能延迟。源仓库必须保持可公开访问并正常更新。若抓取失败、年份覆盖减少或数据异常，保留上次文件并报告失败。
- 仅生成有已发布假日表的完整年份；当前初始范围 2026–2027。没有下一年官方数据就不推算下一年交易日。
- 无第三方 Python 依赖或 API Key。测试 `python -m unittest -v`，离线生成 `python trading_hours.py --offline`。
- 官方来源： https://www.cboe.com/about/hours/us-options/ 和 https://www.cboe.com/tradable-products/sp-500/spx-options/spx-specifications 。特殊临时休市须以交易所通知为准；订阅存在延迟，不能代替交易风控。
