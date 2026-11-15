# Kindle Dashboard

把日期、学期进度、天气、日程、截止和待办生成一张 Kindle 可用的 **1077 × 1448 灰度 PNG**。可以在电脑上独立出图，也可以用 GitHub Actions 发布给 Kindle 定时下载。

![Kindle Dashboard 离线示例，左侧是七天预报，右侧是日程、截止和待办](docs/dashboard-demo.png)

## 快速开始

安装 Python 3.12、CMake 和支持 C++17 的编译器。Linux 可使用 GCC，macOS 可使用 Xcode Command Line Tools 的 Clang。出图所需字体随仓库提供。

```sh
git clone https://github.com/dxd1202/Kindle-Dashboard.git
cd Kindle-Dashboard
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 main.py --demo --output build/demo.png
```

打开 `build/demo.png` 就能看到固定示例。首次出图会编译 C++ 渲染器。如果提示找不到 `cmake` 或 C++ 编译器，请检查安装后是否已重新打开终端，以及命令是否在 `PATH` 上。

## 试用自己的配置

```sh
cp dashboard.example.json dashboard.local.json
python3 main.py --offline --output build/local-preview.png
python3 main.py --edit-tasks
```

`--offline` 跳过天气联网请求，仍读取本地日程和任务。示例日历带重复日程。用编辑器把示例截止日期改到未来七天，就可以查看截止栏的效果。
要用自己的数据，把 `dashboard.local.json` 中的 `calendar` 和 `tasks_file` 指向自己的 ICS 和 JSON 文件。省略 `--output` 时，图片写到 `build/output.png`。加上 `--hide-timetable` 可生成只含日期、学期进度和天气的版本。

## 项目结构

| 目录或文件 | 职责 |
| --- | --- |
| `main.py` | 运行入口 |
| `kindle_dashboard/config.py`、`application.py` | 读取设置、定义天气地点、组织当前数据 |
| `kindle_dashboard/sources/` | 天气 API 和 ICS 日历 |
| `kindle_dashboard/layout/` | 顶栏、天气、日程和任务的排版 |
| `kindle_dashboard/tasks.py` | 待办分类和截止时间 |
| `kindle_dashboard/render.py`、`src/`、`include/` | 调用 C++ 渲染器、生成与替换 PNG |
| `assets/` | 正文字体、和风天气图标字体和码表 |
| `tests/` | 示例日历和离线回归测试 |

运行回归测试：`python3 -m unittest discover -s tests -v`。向 `main` 推送或提交 Pull Request 时，独立的 Dashboard Checks 工作流会运行回归测试，并用离线示例验证 Python 到 C++ 的出图流程与 PNG 格式。

本地和 GitHub Actions 都直接读取 `assets/fonts/` 里的字体，无需安装系统字体。
正文使用 Inter Regular 和更纱黑体 SC Regular，强调文字使用 Inter SemiBold 和更纱黑体 SC Bold。
所附字体的 SIL OFL 1.1 许可也在该目录。上游版本见 [Inter 3.19](https://github.com/rsms/inter/releases/tag/v3.19) 和 [更纱黑体 SC 1.0.43](https://github.com/be5invis/Sarasa-Gothic/releases/tag/v1.0.43)。

## 获取实时数据

```sh
python3 main.py
```

可以把 `.env.example` 复制成 `.env`，然后填写需要的环境变量。

| 变量 | 用法 |
| --- | --- |
| `WEATHER_HOST`、`WEATHER_KEY` | 可选的和风天气专属 API Host 和密钥。Host 填 `https://你的专属域名.qweatherapi.com`。预报未配置或请求失败时，看板使用 Open-Meteo，并标明数据来源。 |
| `ICS_FILE` | iCalendar 日程文件路径。默认读取 Git 忽略的 `timetable.local.ics`。 |
| `ICS_DATA` | 完整的 iCalendar 文本，优先于本地日程文件。 |
| `TASKS_FILE` | 任务 JSON 文件路径，优先于本地配置中的 `tasks_file`。 |
| `SEMESTER_START`、`SEMESTER_WEEKS` | 可选的开学日期（YYYY-MM-DD）和总教学周数（默认 18）。 |

如需更换天气地点，修改 `kindle_dashboard/config.py` 中的 `WEATHER_LOCATION`。和风天气、Open-Meteo 和天气栏的地点标签使用这同一处设置。

在仓库根目录用 [配置示例](dashboard.example.json) 建立 `dashboard.local.json`。这个文件由 Git 忽略，里面的学期设置优先于学期环境变量。日程文件路径可由 `ICS_FILE` 覆盖，`ICS_DATA` 则可以直接提供日程内容。

日程来自 `calendar` 指向的 ICS 文件，换课表时可更新文件路径或重新导出并替换该文件。

运行 `.venv/bin/python main.py --edit-tasks` 后，打开网页的「日程」页。页面默认展示今天和明天，可以用「查看日期」切换到其他日期。已有日程可逐条编辑或删除，重复课程只修改选中的那一次。可填写名称、日期、北京时间、结束时间和地点，也支持全天日程。配置了 `ICS_FILE` 时，编辑器使用该文件。使用 `ICS_DATA` 时，日程页只提供查看。

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

任务文件缺失时，编辑器显示空清单，首次保存时创建 JSON 文件。空 JSON 数组 `[]` 表示清空任务。

## 部署到 Kindle

要让 Kindle 自动下载并显示看板，设备需要先越狱并安装 KUAL。请先按 [设备准备](docs/kindle.md#设备准备) 确认 Kindle 的型号和固件版本。只在电脑上生成 PNG 可以直接使用上面的快速开始。

先按 [GitHub Pages 部署](docs/pages.md) 发布一张可以访问的图片，再按 [Kindle 安装](docs/kindle.md) 配置设备。部署说明也包含使用自己的日程和定时出图的步骤。

项目代码采用 [MIT 许可证](LICENSE)。字体、图标、用到的头文件和天气数据来源见 [第三方资源](THIRD_PARTY_NOTICES.md)。
