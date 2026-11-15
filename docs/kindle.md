# Kindle 安装

设备端脚本面向已越狱、已安装 KUAL 且已连接 Wi-Fi 的 Kindle。项目曾在 Kindle Paperwhite 3 上运行。当前脚本的完整安装和退出流程仍待在对应固件上复测。

1. 在电脑浏览器中打开自己的 `output.png`。如果还没有图片地址，先完成 [GitHub Pages 部署](pages.md)。
2. 将仓库里的 `kindle-device/dashboard/` 复制到 Kindle 的 `/mnt/us/dashboard/`，将 `kindle-device/extensions/kindle-dash/` 复制到 `/mnt/us/extensions/kindle-dash/`。
3. 从 [pascalw/kindle-dash 的 v1.0.0-beta.4 发布页](https://github.com/pascalw/kindle-dash/releases/tag/v1.0.0-beta.4) 下载 `kindle-dash-v1.0.0-beta.4.tgz`。从其中取出 `xh` 和 `next-wakeup`，放到 `/mnt/us/dashboard/`。上游包面向 Kindle 4 NT，二进制构建目标为 `arm-unknown-linux-musleabi`。先在自己的设备上确认可执行。`xh` 负责 HTTPS 下载，`next-wakeup` 计算下次刷新时间。省略后者时使用 30 分钟间隔。
4. 把 `/mnt/us/dashboard/local/env.example.sh` 复制为同目录下的 `env.sh`，把 `DASHBOARD_IMAGE_URL` 改为第一步验证过的地址。`REFRESH_SCHEDULE` 是五字段 cron 表达式，`TIMEZONE` 决定解释时区。
5. 先通过 Kindle shell 单独验证下载，再从 KUAL 打开 **Kindle Dashboard**。验证命令如下。

```sh
cd /mnt/us/dashboard
. ./local/env.sh
./xh --version
/bin/sh ./local/fetch-dashboard.sh /mnt/us/dashboard/test.png
```

脚本会将下载和刷新结果写到 `/mnt/us/dashboard/logs/dash.log`。如果网络故障，屏幕会尽量保留最近一次成功下载的图片。首次安装时保留 Kindle shell 连接，以便检查日志和退出。

当前脚本尝试在收到电源键或 USB 数据连接事件时退出，并恢复原生界面。实际行为取决于固件。也可以从 Kindle shell 执行 `/bin/sh /mnt/us/dashboard/stop.sh`。若原生界面仍未恢复，可重启 Kindle。
