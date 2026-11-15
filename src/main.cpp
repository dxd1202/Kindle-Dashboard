#include "renderer.hpp"
#include <algorithm>
#include <cstdlib>
#include <filesystem>
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

namespace {
constexpr int width = 1448;
constexpr int height = 1077;
const std::string defFont = "main-font.ttf";
const std::string iconFont = "qweather-icons.ttf";

using FontCache = std::map<std::string, std::unique_ptr<Font>>;
using FontStacks = std::map<std::string, std::vector<Font*>>;

std::string font_path(const std::string& name) {
    namespace fs = std::filesystem;
    const fs::path path(name);
    if (!path.has_parent_path() && !fs::is_regular_file(path)) {
        const auto bundled = fs::path("assets") / path;
        if (fs::is_regular_file(bundled)) return bundled.string();
    }
    return name;
}

json read_config(const char* config_path) {
    std::ifstream configFile(config_path);
    if (!configFile.is_open()) throw std::runtime_error(std::string("Cannot open ") + config_path);
    json config;
    configFile >> config;
    return config;
}

FontStacks load_fonts(const json& config, FontCache& fontCache) {
    FontStacks dashboardFonts;
    // 预加载核心字体
    fontCache[defFont] = std::make_unique<Font>(font_path(defFont));
    fontCache[iconFont] = std::make_unique<Font>(font_path(iconFont));
    const auto fontConfig = config.value("dashboard_fonts", json::object());
    for (const auto& weight : {"Regular", "Bold", "SemiBold"}) {
        if (!fontConfig.contains(weight)) continue;
        for (const auto& entry : fontConfig.at(weight)) {
            const auto path = entry.get<std::string>();
            if (!fontCache.count(path)) fontCache[path] = std::make_unique<Font>(path);
            dashboardFonts[weight].push_back(fontCache.at(path).get());
        }
    }
    return dashboardFonts;
}

std::vector<Font*> widget_fonts(const std::string& name, const std::string& weight,
                               const FontCache& cache, const FontStacks& stacks) {
    if (name == defFont && stacks.count(weight)) {
        auto fonts = stacks.at(weight);
        fonts.push_back(cache.at(iconFont).get());
        fonts.push_back(cache.at(defFont).get());
        return fonts;
    }
    std::vector<Font*> fonts{cache.at(name).get()};
    if (name != iconFont) fonts.push_back(cache.at(iconFont).get());
    if (name != defFont) fonts.push_back(cache.at(defFont).get());
    return fonts;
}

int font_baseline(const Font& font, int size) {
    int ascent;
    stbtt_GetFontVMetrics(&font.info, &ascent, nullptr, nullptr);
    return ascent * stbtt_ScaleForPixelHeight(&font.info, size);
}

void draw_emphasized_text(const json& item, const std::string& content,
                          std::vector<unsigned char>& bitmap, const std::vector<Font*>& regular,
                          const std::vector<Font*>& bold, bool synthetic_bold) {
    const auto& range = item.at("emphasis");
    const auto start = std::min(content.size(), range.at(0).get<std::size_t>());
    const auto end = std::clamp(range.at(1).get<std::size_t>(), start, content.size());
    const auto prefix = content.substr(0, start);
    const auto accent = content.substr(start, end - start);
    const auto suffix = content.substr(end);
    int size = item.value("size", 40);
    const int max_width = item.value("max_width", 0);
    while (max_width > 0 && size > 1 && measure_text(regular, prefix, size)
           + measure_text(bold, accent, size) + measure_text(regular, suffix, size) > max_width)
        --size;
    const int x = item.value("x", 0);
    const int y = item.value("y", 0) - text_center_offset(regular, content, size);
    const int gray = std::clamp(item.value("gray", 0), 0, 255);
    const int accent_x = x + measure_text(regular, prefix, size);
    const int accent_y = y + font_baseline(*regular.front(), size) - font_baseline(*bold.front(), size);
    draw_text(regular, bitmap.data(), width, height, prefix.c_str(), x, y, size, gray);
    draw_text(bold, bitmap.data(), width, height, accent.c_str(), accent_x, accent_y, size, 0, synthetic_bold);
    draw_text(regular, bitmap.data(), width, height, suffix.c_str(),
              accent_x + measure_text(bold, accent, size), y, size, gray);
}

void draw_widgets(const json& config, std::vector<unsigned char>& bitmap,
                  FontCache& fontCache, const FontStacks& dashboardFonts) {
    if (!config.contains("widgets") || !config["widgets"].is_array()) {
        throw std::runtime_error("Config must contain a widgets array");
    }
    int next_todo_y = 0;
    for (const auto& item : config["widgets"]) {
        const auto type = item.value("type", "");
        if (type == "rect") {
            int left = std::clamp(item.at("left").get<int>(), 0, width);
            int right = std::clamp(item.at("right").get<int>(), left, width);
            int top = std::clamp(item.at("top").get<int>(), 0, height);
            int bottom = std::clamp(item.at("bottom").get<int>(), top, height);
            const auto color = std::clamp(item.at("gray").get<int>(), 0, 255);
            for (int y = top; y < bottom; ++y) {
                std::fill(bitmap.begin() + y * width + left,
                          bitmap.begin() + y * width + right, color);
            }
            continue;
        }
        std::string content = item.value("content", "");
        if (content.empty()) continue;

        std::string fontName = item.value("font", defFont);
        if (fontCache.find(fontName) == fontCache.end()) {
            try {
                fontCache[fontName] = std::make_unique<Font>(font_path(fontName));
            }
            catch (...) {
                fontName = defFont;
            }
        }

        const bool bold = item.value("bold", false);
        const auto bold_weight = dashboardFonts.count("Bold") ? "Bold" : "SemiBold";
        const auto weight = bold ? bold_weight : "Regular";
        const auto activeFonts = widget_fonts(fontName, weight, fontCache, dashboardFonts);
        if (item.contains("emphasis")) {
            draw_emphasized_text(item, content, bitmap, activeFonts,
                                 widget_fonts(fontName, bold_weight, fontCache, dashboardFonts),
                                 fontName != defFont || !dashboardFonts.count(bold_weight));
            continue;
        }
        const bool synthetic_bold = bold && (fontName != defFont || !dashboardFonts.count(weight));

        int x = item.value("x", 0);
        int size = item.value("size", 40);
        int max_width = item.value("max_width", 0);
        if (type == "todo") {
            const int indent = std::max(37, size + 7);
            const int line_height = std::max(37, size + 4);
            constexpr int item_gap = 12;
            const int text_width = max_width - indent;
            const int y = std::max(next_todo_y, item.at("y").get<int>());
            const int gray = std::clamp(item.value("gray", 0), 0, 255);
            const auto lines = wrap_todo(activeFonts, content, size, text_width);
            draw_text(activeFonts, bitmap.data(), width, height, "□", x, y, size, gray);
            for (std::size_t i = 0; i < lines.size(); ++i) {
                draw_text(activeFonts, bitmap.data(), width, height, lines[i].c_str(),
                          x + indent, y + static_cast<int>(i) * line_height, size, gray);
            }
            next_todo_y = y + static_cast<int>(lines.size()) * line_height + item_gap;
            continue;
        }
        if (max_width > 0 && item.value("fit_width", false)) {
            while (size > 1 && measure_text(activeFonts, content, size) > max_width) --size;
        } else if (max_width > 0 && measure_text(activeFonts, content, size) > max_width) {
            do {
                auto end = content.size() - 1;
                while (end > 0 && (static_cast<unsigned char>(content[end]) & 0xc0) == 0x80)
                    --end;
                content.erase(end);
            } while (!content.empty() && measure_text(activeFonts, content + "…", size) > max_width);
            content += "…";
        }
        const auto align = item.value("align", "left");
        if (align == "right" || align == "center") {
            const int text_width = measure_text(activeFonts, content, size);
            x -= align == "right" ? text_width : text_width / 2;
        }

        int y = item.value("y", 0);
        if (item.value("center_y", false)) {
            y -= text_center_offset(activeFonts, content, size);
        }

        draw_text(activeFonts,
                  bitmap.data(),
                  width,
                  height,
                  content.c_str(),
                  x,
                  y,
                  size,
                  std::clamp(item.value("gray", 0), 0, 255),
                  synthetic_bold);
    }
}

void write_rotated_png(const std::vector<unsigned char>& bitmap, const char* output_path) {
    // 定义目标尺寸（旋转后）
    const int final_w = height;
    const int final_h = width;

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
    int png_size = 0;
    std::unique_ptr<unsigned char, decltype(&std::free)> png(
        stbi_write_png_to_mem(rotated_bitmap.data(), final_w, final_w, final_h, 1, &png_size),
        &std::free);
    if (!png) {
        throw std::runtime_error("Failed to encode PNG");
    }
    std::ofstream output(output_path, std::ios::binary);
    output.write(reinterpret_cast<const char*>(png.get()), png_size);
    output.close();
    if (!output) {
        throw std::runtime_error(std::string("Cannot write ") + output_path);
    }
    std::cout << "看板生成成功: " << output_path << std::endl;
}
}  // namespace

int main(int argc, char* argv[]) {
    try {
        if (argc != 3) {
            throw std::runtime_error("Usage: Kindle-Dashboard <layout.json> <output.png>");
        }
        const char* config_path = argv[1];
        const char* output_path = argv[2];
        const auto config = read_config(config_path);
        FontCache fontCache;
        const auto dashboardFonts = load_fonts(config, fontCache);
        std::vector<unsigned char> bitmap(width * height, 255);
        std::cout << "--- 正在解析布局并渲染 ---" << std::endl;
        draw_widgets(config, bitmap, fontCache, dashboardFonts);
        write_rotated_png(bitmap, output_path);
    }
    catch (const std::exception& e) {
        std::cerr << "[错误] " << e.what() << std::endl;
        return 1;
    }
    return 0;
}
