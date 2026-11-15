# 第三方资源

项目代码采用根目录的 [MIT 许可证](LICENSE)。下列资源保留各自的许可证。

| 资源 | 仓库路径 | 许可证和上游 |
| --- | --- | --- |
| Inter 3.19 Regular、SemiBold | `assets/fonts/Inter-*.ttf` | [SIL OFL 1.1](assets/fonts/Inter-OFL.txt) · [Inter 3.19](https://github.com/rsms/inter/releases/tag/v3.19) |
| 更纱黑体 SC 1.0.43 Regular、Bold | `assets/fonts/SarasaGothicSC-*.ttf` | [SIL OFL 1.1](assets/fonts/Sarasa-Gothic-OFL.txt) · [Sarasa Gothic 1.0.43](https://github.com/be5invis/Sarasa-Gothic/releases/tag/v1.0.43) |
| 和风天气图标字体和图标码表 | `assets/qweather-icons.ttf`、`assets/qweather-icons.json` | [MIT](licenses/QWeather-Icons-MIT.txt) · [QWeather Icons](https://github.com/qwd/Icons) |
| JSON for Modern C++ 3.12.0 | `include/json.hpp` | [MIT](licenses/nlohmann-json-MIT.txt) · [nlohmann/json](https://github.com/nlohmann/json/tree/v3.12.0) |
| stb | `include/stb_truetype.h`、`include/stb_image_write.h` | MIT 或公共领域声明，完整文本在头文件末尾 · [stb](https://github.com/nothings/stb) |
| Kindle 设备端脚本 | `kindle-device/` | 设备布局与工具参考 [pascalw/kindle-dash](https://github.com/pascalw/kindle-dash) · [上游 MIT 声明](licenses/kindle-dash-MIT.txt) |

`xh` 与 `next-wakeup` 从设备端上游发布包获取。安装路径见 [Kindle 安装](docs/kindle.md)。

## 天气数据

- 和风天气提供实况、预报、空气质量和预警数据。看板页脚显示服务网址，并列出预警响应中的来源及发布机构。服务及署名要求见 [和风天气](https://www.qweather.com/) 和 [署名说明](https://dev.qweather.com/docs/terms/attribution/)。
- Open-Meteo 提供备用预报，使用时页脚显示服务网址及 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 标识。服务限制见 [Open-Meteo](https://open-meteo.com/) 和 [使用条款](https://open-meteo.com/en/terms)。
