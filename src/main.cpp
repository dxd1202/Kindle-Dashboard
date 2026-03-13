#include "renderer.hpp"
#include <fstream>
#include <iostream>
#include <json.hpp>
#include <map>
#include <memory>
#include <string>
#include <vector>


#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"

using json = nlohmann::json;

int main() {
    try {
        const int width = 1448, height = 1077;
        std::vector<unsigned char> bitmap(width * height, 255);

        std::ifstream configFile("config.json");
        if (!configFile.is_open()) throw std::runtime_error("config.json not found!");
        json config;
        configFile >> config;

        std::map<std::string, std::unique_ptr<Font>> fontCache;
        std::string defFont = "main-font.ttf";
        std::string iconFont = "qweather-icons.ttf";

        // 预加载核心字体
        fontCache[defFont] = std::make_unique<Font>(defFont);
        fontCache[iconFont] = std::make_unique<Font>(iconFont);

        std::cout << "--- 正在解析布局并渲染 ---" << std::endl;

        if (config.contains("widgets") && config["widgets"].is_array()) {
            for (const auto& item : config["widgets"]) {
                std::string content = item.value("content", "");
                if (content.empty()) continue;

                std::string fontName = item.value("font", defFont);
                if (fontCache.find(fontName) == fontCache.end()) {
                    try {
                        fontCache[fontName] = std::make_unique<Font>(fontName);
                    }
                    catch (...) {
                        fontName = defFont;
                    }
                }

                // 构造优先级字体链
                std::vector<Font*> activeFonts;
                activeFonts.push_back(fontCache[fontName].get());
                if (fontName != iconFont) activeFonts.push_back(fontCache[iconFont].get());
                if (fontName != defFont) activeFonts.push_back(fontCache[defFont].get());

                std::cout << "  > 渲染: " << item.value("id", "none")
                          << " | 居中: " << (item.value("center_tabs", false) ? "开" : "关")
                          << " | 宽: " << item.value("tab_width", 0) << std::endl;

                draw_text(activeFonts,
                          bitmap.data(),
                          width,
                          height,
                          content.c_str(),
                          item.value("x", 0),
                          item.value("y", 0),
                          item.value("size", 40),
                          item.value("center_tabs", false),
                          item.value("tab_width", 0));
            }
        }

        // 在这里，bitmap 已经是渲染好的 1448x1077 横向图了

        // 定义目标尺寸（旋转后）
        const int final_w = 1077;
        const int final_h = 1448;

        // 创建一个新的旋转后的 bitmap 容器
        std::vector<unsigned char> rotated_bitmap(final_w * final_h, 255);

        // 执行 90 度顺时针旋转
        for (int y = 0; y < height; ++y) {
            for (int x = 0; x < width; ++x) {
                // 旋转算法：
                // 新的坐标 (new_x, new_y) = (height - 1 - y, x)
                // 新的 index = new_y * final_w + new_x
                rotated_bitmap[x * final_w + (height - 1 - y)] = bitmap[y * width + x];
            }
        }

        // 修改保存逻辑：使用新的尺寸和新的 rotated_bitmap
        if (stbi_write_png("output.png", final_w, final_h, 1, rotated_bitmap.data(), final_w)) {
            std::cout << "🎉 看板生成成功 (已旋转): output.png" << std::endl;
        }
        else {
            throw std::runtime_error("Failed to write PNG");
        }
    }
    catch (const std::exception& e) {
        std::cerr << "[错误] " << e.what() << std::endl;
        return 1;
    }
    return 0;
}