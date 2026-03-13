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

        if (stbi_write_png("output.png", width, height, 1, bitmap.data(), width)) {
            std::cout << "🎉 看板生成成功：output.png" << std::endl;
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