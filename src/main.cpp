#include <fstream>
#include <iostream>
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

int main() {
    try {
        // --- 初始化参数 ---
        const int width = 1448;
        const int height = 1077;
        std::vector<unsigned char> bitmap(width * height, 255);   // 白色背景

        // --- 加载字体 (只加载一次) ---
        Font myFont("NOTO SANS SC.ttf");

        // --- 解析配置文件 ---
        std::ifstream configFile("config.json");
        if (!configFile.is_open()) {
            throw std::runtime_error("无法找到 config.json 文件！请确保它在运行目录下。");
        }

        json config;
        configFile >> config;   // 自动解析 JSON 数据

        std::cout << "正在解析布局并渲染..." << std::endl;

        // --- 核心逻辑：遍历 JSON 中的组件 ---
        // 我们预设 JSON 里有一个 "widgets" 数组
        if (config.contains("widgets") && config["widgets"].is_array()) {
            for (const auto& item : config["widgets"]) {
                // 提取参数，带上默认值防止 JSON 格式错误导致崩溃
                std::string content = item.value("content", "");
                int x = item.value("x", 0);
                int y = item.value("y", 0);
                int size = item.value("size", 40);

                if (!content.empty()) {
                    std::cout << "  - 渲染组件: " << content << " (at " << x << "," << y << ")"
                              << std::endl;
                    draw_text(myFont, bitmap.data(), width, height, content.c_str(), x, y, size);
                }
            }
        }

        // --- 保存结果 ---
        if (stbi_write_png("output.png", width, height, 1, bitmap.data(), width)) {
            std::cout << "看板生成成功：output.png" << std::endl;
        }
        else {
            throw std::runtime_error("写入图片失败！");
        }
    }
    catch (const std::exception& e) {
        // 捕获所有可能的错误（文件找不到、JSON 语法错误、内存溢出等）
        std::cerr << "[错误] " << e.what() << std::endl;
        return 1;
    }

    return 0;
}