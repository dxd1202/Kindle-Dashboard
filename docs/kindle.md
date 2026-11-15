# Kindle 安装

## 设备准备

1. 在 Kindle 上打开 **设置 → 设备选项 → 设备信息**，记下设备型号和完整固件版本。型号也可以参考 [Amazon 的 Kindle 型号识别指南](https://digprjsurvey.amazon.com/csad/help/node/GK33S847NN4V6Y83)。
2. 根据型号和固件版本确认越狱兼容性，再完成设备越狱。同一机型的不同固件可能需要不同的准备流程。仓库中的脚本从已越狱的设备开始安装。
3. 越狱后安装适用于该设备的 [KUAL（Kindle Unified Application Launcher）](https://wiki.mobileread.com/wiki/KUAL)，打开一次确认菜单能正常显示，并让 Kindle 连上 Wi-Fi。

项目曾在 Kindle Paperwhite 3 上运行。当前脚本的完整安装和退出流程仍待在对应固件上复测。

## 安装看板

1. 在电脑浏览器中打开自己的 `output.png`。如果还没有图片地址，先完成 [GitHub Pages 部署](pages.md)。
2. 将仓库里的 `kindle-device/dashboard/` 复制到 Kindle 的 `/mnt/us/dashboard/`，将 `kindle-device/extensions/kindle-dash/` 复制到 `/mnt/us/extensions/kindle-dash/`。
3. 从 [pascalw/kindle-dash 的 v1.0.0-beta.4 发布页](https://github.com/pascalw/kindle-dash/releases/tag/v1.0.0-beta.4) 下载 `kindle-dash-v1.0.0-beta.4.tgz`。从其中取出 `xh` 和 `next-wakeup`，放到 `/mnt/us/dashboard/`。上游包面向 Kindle 4 NT，二进制构建目标为 `arm-unknown-linux-musleabi`。先在自己的设备上确认可执行。`xh` 负责 HTTPS 下载，`next-wakeup` 计算下次刷新时间。省略后者时使用 30 分钟间隔。
4. 把 `/mnt/us/dashboard/local/env.example.sh` 复制为同目录下的 `env.sh`，把 `DASHBOARD_IMAGE_URL` 改为第一步验证过的地址。`REFRESH_SCHEDULE` 是五字段 cron 表达式，`TIMEZONE` 决定解释时区。
5. 从 KUAL 打开 **Kindle Dashboard**。首次启动后，屏幕应显示第 1 步验证过的图片。

复制后，Kindle 上的主要文件路径如下。

```text
/mnt/us/dashboard/start.sh
/mnt/us/dashboard/local/env.sh
/mnt/us/dashboard/local/fetch-dashboard.sh
/mnt/us/dashboard/xh
/mnt/us/extensions/kindle-dash/config.xml
/mnt/us/extensions/kindle-dash/menu.json
```

有 Kindle shell 时，可以在启动前单独验证 HTTPS 下载。以下命令在 Kindle 上执行。

```sh
cd /mnt/us/dashboard
. ./local/env.sh
./xh --version
/bin/sh ./local/fetch-dashboard.sh /mnt/us/dashboard/test.png
```

脚本会将下载和刷新结果写到 `/mnt/us/dashboard/logs/dash.log`。如果网络故障，屏幕会尽量保留最近一次成功下载的图片。有 Kindle shell 时，首次安装可以保留连接，以便检查日志和退出。

遇到网络错误时，脚本会立即尝试重新连接已保存的 Wi-Fi。若仍无法下载，且无线功能原本开启，脚本会在 Wi-Fi 已断开或状态未知时当轮重启无线功能。若设备仍报告已关联，则从连续第二轮失败起才会重启。相邻两次重启之间至少隔两轮重试。只要还有网络错误且 Wi-Fi 未关闭，本轮处理完成后就会在 30 秒后发起下一轮。实际下载成功后恢复正常刷新间隔。如果仍无法恢复，可查看日志里的 Wi-Fi 状态、重连结果和下载退出码。

当前脚本尝试在收到电源键或 USB 数据连接事件时退出，并恢复原生界面。实际行为取决于固件。也可以从 Kindle shell 执行 `/bin/sh /mnt/us/dashboard/stop.sh`。若原生界面仍未恢复，可重启 Kindle。
