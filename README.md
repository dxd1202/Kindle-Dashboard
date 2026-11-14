# Kindle Dashboard

首页显示日期、学期进度、海淀未来七天预报（竖排，每行以统一温标呈现最低到最高温）、今天和明天的日程、截止时间和待办。
C++ 以 1448 × 1077 横向排版，再顺时针旋转，生成 Kindle 使用的 1077 × 1448 灰度 PNG。

## 本地预览

安装 Python 3、uv、CMake 和支持 C++17 的编译器。在仓库根目录首次配置项目环境：

```sh
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.txt
```

之后每次打开新终端，先启用项目环境，再运行下文的 `python3` 命令：

```sh
source .venv/bin/activate
python3 main.py --demo --output build/demo.png
```

这会用示例数据生成 `build/demo.png`。省略 `--output` 时，默认写入 `build/output.png`。加上 `--hide-timetable` 可以预览公开版，
其中只显示日期、学期进度、天气和更新时间。

使用 `--config 路径` 显式运行旧版布局，例如 `python3 main.py --config examples/legacy-layout.json --offline`。
旧版布局的实时行情需要额外运行 `uv pip install --python .venv/bin/python -r requirements-legacy.txt`。
用 `--offline` 跳过联网采集，新版仍会读取本地日程；旧版布局会使用文件中的文字。
运行时不会覆盖布局输入文件。
首次运行会配置并编译 C++ 渲染器。以后沿用已有构建目录，由 CMake 判断何时需要重新配置或编译。

## 项目结构

| 目录或文件 | 职责 |
| --- | --- |
| `main.py` | 运行入口 |
| `kindle_dashboard/config.py`、`application.py` | 读取设置、定义天气地点、组织当前数据 |
| `kindle_dashboard/sources/` | 天气 API 和 ICS 日历 |
| `kindle_dashboard/layout/` | 顶栏、天气、日程和任务的排版 |
| `kindle_dashboard/tasks.py` | 待办分类和截止时间 |
| `kindle_dashboard/render.py`、`src/`、`include/` | 调用 C++ 渲染器、生成与替换 PNG |
| `assets/`、`examples/` | 内置字体和图标、旧布局示例 |
| `kindle_dashboard/legacy/` | 旧布局的行情、天气和周课表 |
| `tests/` | 示例日历和离线回归测试 |

运行回归测试：`python3 -m unittest discover -s tests -v`。向 `main` 推送或提交 Pull Request 时，独立的 Dashboard Checks 工作流会运行回归测试，并用离线示例验证 Python 到 C++ 的出图流程与 PNG 格式。

新版看板在有 Fontconfig 的系统上优先使用 Inter 和更纱黑体 SC，强调文字使用 Inter SemiBold 和更纱黑体 SC Bold。
缺少对应字重或 Fontconfig 时，该字重回退到仓库自带字体。

## 获取实时数据

```sh
python3 main.py
```

在本地的 `.env` 或环境变量中设置需要的数据源：

| 变量 | 用法 |
| --- | --- |
| `WEATHER_HOST`、`WEATHER_KEY` | 可选的和风天气专属 API Host 和密钥。Host 填 `https://你的专属域名.qweatherapi.com`，程序拼接 `/weather/v1` 路径。已有 Host 值中的路径会被忽略。未配置或请求失败时，看板使用 Open-Meteo，并标明数据来源。 |
| `ICS_FILE` | iCalendar 日程文件路径。默认读取 Git 忽略的 `timetable.local.ics`。 |
| `ICS_DATA` | 完整的 iCalendar 文本，优先于本地日程文件。 |
| `SEMESTER_START`、`SEMESTER_WEEKS` | 可选的开学日期（YYYY-MM-DD）和总教学周数（默认 18）。 |
| `STOCK_LIST` | 仅供旧版行情布局使用。示例 `[["000001.SS","上证指数","¥"]]`。 |

如需更换天气地点，修改 `kindle_dashboard/config.py` 中的 `WEATHER_LOCATION`。和风天气、Open-Meteo 和天气栏的地点标签使用这同一处设置。

在仓库根目录建立 `dashboard.local.json` 设置学期、日程文件和任务清单路径。该文件由 Git 忽略。
学期设置优先于学期环境变量；日程文件路径则可由 `ICS_DATA` 或 `ICS_FILE` 覆盖。

```json
{
  "semester": {"start": "2026-09-14", "weeks": 18},
  "calendar": "2026Autumn.ics",
  "tasks_file": "tasks.local.json"
}
```

日程来自 `calendar` 指向的 ICS 文件，换课表时可更新文件路径或重新导出并替换该文件。

运行 `.venv/bin/python main.py --edit-tasks` 后，打开网页的「日程」页，可查看今天和明天的日程，并向当前 ICS 新增单次事件。填写名称、日期和北京时间，可选填同一天的结束时间及地点。配置了 `ICS_FILE` 时，编辑器使用该文件。使用 `ICS_DATA` 时，日程页只提供查看。

保存后运行 `.venv/bin/python main.py` 更新看板。新增日程和课表在同一份 ICS 里，重新导出并替换文件前，请保留需要的手动日程。

## 待办和截止

运行 `python3 main.py --edit-tasks` 打开本地任务编辑页。可以新增、搜索、筛选、修改、完成或删除任务。操作立即保存，截止时间按北京时间输入。若浏览器没有自动打开，复制终端显示的网址即可。按 `Ctrl+C` 关闭编辑器。运行 `python3 main.py` 生成更新后的看板图片。

`tasks_file` 指向一个 JSON 数组文件，省略时默认使用 `tasks.local.json`。与 `calendar` 一样，相对路径以仓库根目录为准。默认清单参与公开发布。使用其他仅供本地读取的清单时，请将对应路径加入 Git 忽略规则。

```json
[
  {"title": "整理实验板和导线", "due": null, "done": false},
  {"title": "交物理实验报告", "due": "2026-11-19T18:00", "done": false}
]
```

旧配置仍指向 Markdown 时，编辑器会把第一次保存写到同名的 `.json` 文件，原 Markdown 留作备份。还没有 JSON 文件时，看板仍可读取旧清单。空 JSON 数组 `[]` 表示清空任务。

## 发布

GitHub Actions 可手动启动或由 cron-job.org 触发。Actions Secrets 提供
`WEATHER_HOST` 和 `WEATHER_KEY`。Actions Variables 提供
`SEMESTER_START` 和 `SEMESTER_WEEKS`。

工作流直接读取 `main` 上的 `2026Autumn.ics` 和 `tasks.local.json`，生成包含日程、待办和截止的完整版图片。两个源文件及其提交历史在仓库中公开。Pages 发布目录包含 `output.png` 和 `.nojekyll`。

网页编辑器保存后，将改动的源文件提交并推送到 `main`。例如同时更新两份文件：

```sh
git add 2026Autumn.ics tasks.local.json
git commit -m "Update dashboard schedule and tasks"
git push origin main
```

下一次手动运行或定时触发会用推送后的数据出图。要立即更新，在 Actions 页运行 **Kindle Dashboard Auto Update**，分支选 `main`。换学期改用新 ICS 文件时，同时更新本地 `dashboard.local.json` 的 `calendar`、工作流里的 `ICS_FILE` 以及 `.gitignore` 中放行的日历路径。
