#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <string>
#include <vector>


// 1. 引入 JSON 库
#include <json.hpp>
using json = nlohmann::json;

// 2. 引入渲染引擎
#include "renderer.hpp"

// 3. 引入图片保存库
#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"

Font mainFont("NOTO SANS SC.ttf");
Font iconFont("qweather-icons.ttf");

std::vector<Font*> fontList = {&mainFont, &iconFont};

int main() {
    try {
        // --- 1. 初始化画布参数 ---
        const int width = 1448;
        const int height = 1077;
        std::vector<unsigned char> bitmap(width * height, 255);   // 白色背景

        // --- 2. 解析配置文件 ---
        std::ifstream configFile("config.json");
        if (!configFile.is_open()) {
            throw std::runtime_error("无法找到 config.json 文件！");
        }
        json config;
        configFile >> config;

        // --- 3. 字体管理器 (缓存) ---
        // 这里的逻辑是：文件名 -> 字体对象的映射
        // 使用 unique_ptr 是为了方便管理内存
        std::map<std::string, std::unique_ptr<Font>> fontCache;

        // 1. 先确保常用的核心字体都已经加载进 fontCache
        // 建议在循环外手动加载一下，保证它们一定在内存里
        std::string defaultFontName = "NOTO SANS SC.ttf";
        std::string iconFontName = "qweather-icons.ttf";

        if (fontCache.find(defaultFontName) == fontCache.end())
            fontCache[defaultFontName] = std::make_unique<Font>(defaultFontName);
        if (fontCache.find(iconFontName) == fontCache.end())
            fontCache[iconFontName] = std::make_unique<Font>(iconFontName);

        // 2. 开始渲染循环
        for (const auto& item : config["widgets"]) {
            std::string content = item.value("content", "");
            if (content.empty()) continue;

            // 获取当前组件的首选字体
            std::string preferredFont = item.value("font", defaultFontName);

            // 如果首选字体没加载，加载它
            if (fontCache.find(preferredFont) == fontCache.end()) {
                try {
                    fontCache[preferredFont] = std::make_unique<Font>(preferredFont);
                }
                catch (...) {
                    preferredFont = defaultFontName;
                }
            }

            // --- 【核心修改】：构建当前组件的“备选字体链” ---
            std::vector<Font*> activeFonts;
            activeFonts.push_back(fontCache[preferredFont].get());   // 第一优先级：组件指定的字体

            // 如果首选不是图标字体，把图标字体加到后面作为备选
            if (preferredFont != iconFontName) {
                activeFonts.push_back(fontCache[iconFontName].get());
            }
            // 如果首选不是默认字体，把默认中文字体也加上
            if (preferredFont != defaultFontName) {
                activeFonts.push_back(fontCache[defaultFontName].get());
            }

            // 提取其他参数
            int x = item.value("x", 0);
            int y = item.value("y", 0);
            int size = item.value("size", 40);
            bool center_tabs = item.value("center_tabs", false);
            int tab_width = item.value("tab_width", 0);

            // --- 【核心调用】：现在参数匹配了 ---
            draw_text(activeFonts,
                      bitmap.data(),
                      width,
                      height,
                      content.c_str(),
                      x,
                      y,
                      size,
                      center_tabs,
                      tab_width);
        }

        // --- 5. 保存结果 ---
        if (stbi_write_png("output.png", width, height, 1, bitmap.data(), width)) {
            std::cout << "\n🎉 看板生成成功：output.png" << std::endl;
        }
        else {
            throw std::runtime_error("写入图片失败！");
        }
    }
    catch (const std::exception& e) {
        std::cerr << "\n[致命错误] " << e.what() << std::endl;
        return 1;
    }

    return 0;
}