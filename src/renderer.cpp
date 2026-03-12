#define STB_TRUETYPE_IMPLEMENTATION
#include "renderer.hpp"
#include <cstdint>   // 必须包含这个，否则 uint32_t 报错
#include <fstream>
#include <iostream>


// 1. 字体加载逻辑
Font::Font(const std::string& path) {
    std::ifstream file(path, std::ios::binary | std::ios::ate);
    if (!file.is_open()) throw std::runtime_error("Font file not found!");
    std::streamsize size = file.tellg();
    file.seekg(0, std::ios::beg);
    data.resize(size);
    file.read((char*)data.data(), size);
    if (!stbtt_InitFont(&info, data.data(), 0)) throw std::runtime_error("Failed to init font!");
}

// 2. UTF-8 解码器 (修正了之前的多重修改问题)
static uint32_t next_utf8(const char*& str) {
    unsigned char c = (unsigned char)*str++;
    if (c < 0x80) return c;
    if ((c & 0xE0) == 0xC0) {
        uint32_t b1 = (unsigned char)*str++;
        return ((c & 0x1F) << 6) | (b1 & 0x3F);
    }
    if ((c & 0xF0) == 0xE0) {
        uint32_t b1 = (unsigned char)*str++;
        uint32_t b2 = (unsigned char)*str++;
        return ((c & 0x0F) << 12) | ((b1 & 0x3F) << 6) | (b2 & 0x3F);
    }
    if ((c & 0xF8) == 0xF0) {
        uint32_t b1 = (unsigned char)*str++;
        uint32_t b2 = (unsigned char)*str++;
        uint32_t b3 = (unsigned char)*str++;
        return ((c & 0x07) << 18) | ((b1 & 0x3F) << 12) | ((b2 & 0x3F) << 6) | (b3 & 0x3F);
    }
    return 0;
}

// 3. 核心绘图引擎
void draw_text(Font& font, unsigned char* bitmap, int width, int height, const char* text, int x,
               int y, int size) {
    // 获取缩放比例：将字体单位转换为像素
    float scale = stbtt_ScaleForPixelHeight(&font.info, (float)size);

    // 获取垂直度量
    int ascent, descent, lineGap;
    stbtt_GetFontVMetrics(&font.info, &ascent, &descent, &lineGap);

    // 【关键修复】：ascent 必须乘以上面的 scale 转换为像素
    int pixel_ascent = (int)(ascent * scale);

    int pen_x = x;
    const char* ptr = text;

    while (*ptr) {
        uint32_t cp = next_utf8(ptr);
        int advance, lsb;
        stbtt_GetCodepointHMetrics(&font.info, cp, &advance, &lsb);

        int x0, y0, x1, y1;
        stbtt_GetCodepointBitmapBox(&font.info, cp, scale, scale, &x0, &y0, &x1, &y1);

        int char_w = x1 - x0;
        int char_h = y1 - y0;

        if (char_w > 0 && char_h > 0) {
            std::vector<unsigned char> char_bmp(char_w * char_h);
            stbtt_MakeCodepointBitmap(
                &font.info, char_bmp.data(), char_w, char_h, char_w, scale, scale, cp);

            for (int row = 0; row < char_h; ++row) {
                for (int col = 0; col < char_w; ++col) {
                    int target_x = pen_x + x0 + col;
                    // 【关键修复】：使用缩放后的 pixel_ascent
                    int target_y = y + pixel_ascent + y0 + row;

                    if (target_x >= 0 && target_x < width && target_y >= 0 && target_y < height) {
                        // 背景是 255 (白)，我们要画黑字，所以减去采样值
                        int source_pixel = char_bmp[row * char_w + col];
                        if (source_pixel > 0) {
                            bitmap[target_y * width + target_x] = 255 - source_pixel;
                        }
                    }
                }
            }
        }
        pen_x += (int)(advance * scale);

        // Kerning 优化
        if (*ptr) {
            const char* peek_ptr = ptr;
            uint32_t next_cp = next_utf8(peek_ptr);
            pen_x += (int)(stbtt_GetCodepointKernAdvance(&font.info, cp, next_cp) * scale);
        }
    }
}