# 发布到 GitHub Pages

## 第一次用示例发布

1. 登录 GitHub，在项目页点击 **Fork**，创建自己的公开 fork。进入 fork 的 **Actions**，按页面提示启用工作流。
2. 在 **Settings → Pages → Build and deployment → Source** 选择 **GitHub Actions**。
3. 在 **Settings → Secrets and variables → Actions → Variables** 点击 **New repository variable**，添加 `PAGES_USE_ACTIONS`，值填 `true`。本次示例发布只需要这一个变量。
4. 打开 **Actions → Kindle Dashboard Auto Update → Run workflow**，选择默认分支，勾选 **Publish the offline sample dashboard**，再运行工作流。
5. 等 `deploy` 作业成功。从部署链接复制站点地址，在其末尾加上 `/output.png`，例如 `https://你的用户名.github.io/Kindle-Dashboard/output.png`。用未登录窗口确认显示完整图片，再把这个地址写入 Kindle 的 `DASHBOARD_IMAGE_URL`。
6. 在同一个站点地址下打开 `/mobile/`。用手机检查待办添加和勾完成、今天／明天切换和七天预报。鸿蒙用户可在华为浏览器里将页面添加到桌面。

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

## 手机上新增和勾完成

示例版可以直接尝试新增和标完成。示例操作只在当前页面生效。

同步真实任务时，使用同一个 GitHub 任务文件，电脑无需保持在线。

1. 确认工作流的 `TASKS_FILE` 指向仓库中现有的任务 JSON。仓库默认文件是 `tasks.local.json`。
2. 在仓库变量中设置 `MOBILE_TASK_EDIT=true`。如果希望公开网页只展示天气，设置 `MOBILE_DATA=weather`。如果也希望公开日程和待办，设置 `MOBILE_DATA=personal`。运行一次工作流，发布新版手机页面。
3. 在 [GitHub 令牌设置](https://github.com/settings/personal-access-tokens/new) 创建一个限于此仓库的细粒度令牌，给 **Contents** 读写权限并设置到期日。这个权限覆盖指定仓库的内容。把令牌直接填入自己发布的手机页面，然后点「连接任务清单」。页面将令牌保留在当前页面内存中，只发送给 GitHub 的 API。刷新整个网页或关闭页面后需重新连接。
4. 在待办页输入待办并点「添加」，或点现有任务旁的勾。看到「已保存到 GitHub」就说明网页已经提交了修改，无需手动 push。等待下一次 Kindle 自动更新，或在 Actions 手动运行一次出图。公网仓库中写入的任务及提交历史对外可访问。

碰到「任务清单已被修改」时，页面会读取最新清单。确认最新内容后再重试。电脑如果也使用本地编辑器，编辑前先拉取 GitHub 上的新提交。

## 手机上新增和编辑日程

1. 在 Actions 仓库变量中设置 `MOBILE_DATA=personal` 和 `MOBILE_CALENDAR_EDIT=true`。确认 `ICS_FILE` 指向分支中已提交的日历文件，然后运行一次 **Kindle Dashboard Auto Update**。
2. 给仅限此仓库的细粒度 GitHub 令牌增加 **Actions** 读写权限。如果同一个令牌用于编辑待办，也要保留 **Contents** 读写权限。
3. 在手机版打开「日程」，点「新增日程」或在条目旁点「编辑」。保存时使用 GitHub 令牌。重复日程的改动只应用于选中的那一次。地点字段跟随 `MOBILE_SHOW_LOCATIONS` 设置。
4. 等待页面显示「已保存并发布」。工作流会提交 ICS，并更新手机网页和 Kindle 图片。手机上的每一次保存都由工作流完成，无需手动 push。遇到失败时可从页面打开 GitHub Actions 的运行记录。

## 定时更新

先成功运行一次手动发布。使用 cron-job.org 时，可以配置一个定时发送的 `POST` 请求，调用 GitHub 的工作流分派接口。

- 地址 `https://api.github.com/repos/OWNER/REPO/actions/workflows/main.yml/dispatches`
- 请求头 `Authorization: Bearer YOUR_TOKEN` 和 `Accept: application/vnd.github+json`
- 请求体 `{"ref":"main"}`，并把 `Content-Type` 设为 `application/json`

将 `OWNER`、`REPO` 和分支名换成自己的值。给访问令牌限定目标仓库，并授予触发工作流所需的 **Actions: write** 权限。把真实令牌填在定时任务的请求头中。先发送一次测试请求，再到 Actions 页面确认出现新的运行。

接口说明见 [GitHub REST API](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event)。
