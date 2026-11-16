# 发布到 GitHub Pages

## 第一次用示例发布

1. 登录 GitHub，在项目页点击 **Fork**，创建自己的公开 fork。进入 fork 的 **Actions**，按页面提示启用工作流。
2. 在 **Settings → Pages → Build and deployment → Source** 选择 **GitHub Actions**。
3. 在 **Settings → Secrets and variables → Actions → Variables** 点击 **New repository variable**，添加 `PAGES_USE_ACTIONS`，值填 `true`。本次示例发布只需要这一个变量。
4. 打开 **Actions → Kindle Dashboard Auto Update → Run workflow**，选择默认分支，勾选 **Publish the offline sample dashboard**，再运行工作流。
5. 等 `deploy` 作业成功。从部署链接复制站点地址，在其末尾加上 `/output.png`，例如 `https://你的用户名.github.io/Kindle-Dashboard/output.png`。用未登录窗口确认显示完整图片，再把这个地址写入 Kindle 的 `DASHBOARD_IMAGE_URL`。
6. 在同一个站点地址下打开 `/mobile/`。用手机检查总览、今天／明天切换、任务筛选和七天预报。鸿蒙用户可在华为浏览器里将页面添加到桌面。

原仓库的分支发布方式仍可通过省略 `PAGES_USE_ACTIONS` 使用，该方式将图片写到 `gh-pages`。

## 用自己的数据发布

取消勾选示例选项，并在 Actions Variables 中设置以下变量。需将日历和任务文件提交到工作流使用的分支。

| 变量 | 值 |
| --- | --- |
| `SEMESTER_START` | 学期开始日期，格式为 `YYYY-MM-DD` |
| `SEMESTER_WEEKS` | 总教学周数，填正整数 |
| `ICS_FILE` | 仓库内的 ICS 路径，例如 `examples/calendar.ics` |
| `TASKS_FILE` | 仓库内的任务 JSON 路径，例如 `examples/tasks.json` |

省略 `ICS_FILE` 和 `TASKS_FILE` 时，分别使用 `2026Autumn.ics` 和 `tasks.local.json`。如果 Git 忽略了你的新 ICS 路径，先在 `.gitignore` 中放行该文件。配置天气地点见 [README](../README.md#获取实时数据)。

如需和风天气，在 Actions Secrets 中设置 `WEATHER_HOST` 和 `WEATHER_KEY`。使用 Open-Meteo 备用预报时可以省略两项。

公开仓库里的日历、任务与 Pages 图片都可被访问。准备向外公开的文件应按你的发布计划选择。

## 手机版数据范围

在 Actions 的 **Repository variables** 中配置 `MOBILE_DATA`。更改后重新运行工作流，配置才会反映在发布产物中。

| 值 | 手机版展示 |
| --- | --- |
| `demo`（默认） | 固定的虚构示例 |
| `weather` | 本轮实际天气、日期和学期周次 |
| `personal` | 本轮实际天气、今天和明天的日程，以及看板使用的未完成任务 |

个人版默认省略地点。确实需要公开地点时，额外设置 `MOBILE_SHOW_LOCATIONS=true`。**公开 Pages 上的 `mobile/dashboard.json` 可以直接下载。** 个人版会包含可能因版面限制而未出现在 PNG 上的条目。勾选工作流的离线示例选项时，两个输出都使用虚构数据。

## 定时更新

先成功运行一次手动发布。使用 cron-job.org 时，可以配置一个定时发送的 `POST` 请求，调用 GitHub 的工作流分派接口。

- 地址 `https://api.github.com/repos/OWNER/REPO/actions/workflows/main.yml/dispatches`
- 请求头 `Authorization: Bearer YOUR_TOKEN` 和 `Accept: application/vnd.github+json`
- 请求体 `{"ref":"main"}`，并把 `Content-Type` 设为 `application/json`

将 `OWNER`、`REPO` 和分支名换成自己的值。给访问令牌限定目标仓库，并授予触发工作流所需的 **Actions: write** 权限。把真实令牌填在定时任务的请求头中。先发送一次测试请求，再到 Actions 页面确认出现新的运行。

接口说明见 [GitHub REST API](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event)。
