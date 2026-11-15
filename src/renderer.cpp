#define STB_TRUETYPE_IMPLEMENTATION
#include "renderer.hpp"
#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <vector>

// 1. 字体加载逻辑
Font::Font(const std::string& path) {
    std::ifstream file(path, std::ios::binary | std::ios::ate);
    if (!file.is_open()) throw std::runtime_error("C++ 找不到这个文件: [" + path + "]");
    std::streamsize size = file.tellg();
    file.seekg(0, std::ios::beg);
    data.resize(size);
    file.read((char*)data.data(), size);
    if (!stbtt_InitFont(&info, data.data(), 0)) throw std::runtime_error("Failed to init font!");
}

// 2. UTF-8 解码器
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

static Font* glyph_font(const std::vector<Font*>& fonts, uint32_t codepoint) {
    for (auto* font : fonts) {
        if (stbtt_FindGlyphIndex(&font->info, codepoint) != 0) return font;
    }
    return fonts.front();
}

static int glyph_y_offset(uint32_t codepoint) {
    return codepoint >= 0xF100 && codepoint < 0xFF00 ? 10 : 0;
}

int measure_text(const std::vector<Font*>& fonts, const std::string& text, int size) {
    int total_w = 0;
    const char* ptr = text.c_str();
    while (*ptr) {
        const uint32_t cp = next_utf8(ptr);
        // 遍历所有字体找宽度
        auto* font = glyph_font(fonts, cp);
        float scale = stbtt_ScaleForPixelHeight(&font->info, (float)size);
        int advance, lsb;
        stbtt_GetCodepointHMetrics(&font->info, cp, &advance, &lsb);
        total_w += (int)(advance * scale);
    }
    return total_w;
}

std::vector<std::string> wrap_todo(const std::vector<Font*>& fonts, const std::string& text,
                                  int size, int width) {
    if (measure_text(fonts, text, size) <= width) return {text};

    const char* start = text.c_str();
    const auto fitting_end = [&](const char* begin, int limit) {
        const char* cursor = begin;
        const char* end = begin;
        const char* word_end = begin;
        while (*cursor) {
            if (*cursor == ' ' && end == cursor) word_end = cursor;
            next_utf8(cursor);
            if (measure_text(fonts, std::string(begin, cursor), size) > limit) break;
            end = cursor;
        }
        return *cursor && word_end > begin ? word_end : end;
    };

    const char* end = fitting_end(start, width);
    std::string first(start, end);
    while (*end == ' ') ++end;
    std::string second(end);
    if (measure_text(fonts, second, size) > width) {
        const auto prefix = fitting_end(end, width - measure_text(fonts, "…", size));
        second = std::string(end, prefix) + "…";
    }
    return {first, second};
}

// Measure the ink bounds of a single line, including the weather icon offset.
int text_center_offset(const std::vector<Font*>& fonts, const std::string& text, int size) {
    int ascent;
    stbtt_GetFontVMetrics(&fonts.front()->info, &ascent, nullptr, nullptr);
    const int baseline = ascent * stbtt_ScaleForPixelHeight(&fonts.front()->info, size);
    int top = 0, bottom = 0;
    bool has_ink = false;
    const char* ptr = text.c_str();
    while (*ptr) {
        const uint32_t cp = next_utf8(ptr);
        auto* font = glyph_font(fonts, cp);
        const float scale = stbtt_ScaleForPixelHeight(&font->info, size);
        int x0, y0, x1, y1;
        stbtt_GetCodepointBitmapBox(&font->info, cp, scale, scale, &x0, &y0, &x1, &y1);
        if (x0 == x1 || y0 == y1) continue;
        const int offset = glyph_y_offset(cp);
        top = has_ink ? std::min(top, y0 + offset) : y0 + offset;
        bottom = has_ink ? std::max(bottom, y1 + offset) : y1 + offset;
        has_ink = true;
    }
    return has_ink ? baseline + (top + bottom) / 2 : 0;
}

void draw_text(const std::vector<Font*>& fonts, unsigned char* bitmap, int width, int height,
               const char* text, int x, int y, int size, int ink, bool synthetic_bold) {
    if (fonts.empty()) return;

    int ascent;
    stbtt_GetFontVMetrics(&fonts.front()->info, &ascent, nullptr, nullptr);
    const int pixel_ascent = ascent * stbtt_ScaleForPixelHeight(&fonts.front()->info, size);
    int pen_x = x;
    const char* ptr = text;
    while (*ptr) {
        const uint32_t cp = next_utf8(ptr);
        Font* activeFont = glyph_font(fonts, cp);

        float local_scale = stbtt_ScaleForPixelHeight(&activeFont->info, (float)size);
        int advance, lsb, x0, y0, x1, y1;
        stbtt_GetCodepointHMetrics(&activeFont->info, cp, &advance, &lsb);
        stbtt_GetCodepointBitmapBox(
            &activeFont->info, cp, local_scale, local_scale, &x0, &y0, &x1, &y1);

        int char_w = x1 - x0, char_h = y1 - y0;
        if (char_w > 0 && char_h > 0) {
            std::vector<unsigned char> char_bmp(char_w * char_h);
            stbtt_MakeCodepointBitmap(&activeFont->info,
                                      char_bmp.data(),
                                      char_w,
                                      char_h,
                                      char_w,
                                      local_scale,
                                      local_scale,
                                      cp);

            for (int row = 0; row < char_h; ++row) {
                for (int col = 0; col < char_w; ++col) {
                    int tx = pen_x + x0 + col;
                    int ty = y + pixel_ascent + y0 + row + glyph_y_offset(cp);

                    if (tx >= 0 && tx < width && ty >= 0 && ty < height) {
                        int p = char_bmp[row * char_w + col];
                        if (p > 0) {
                            auto blend = [&](int x, int y, int alpha) {
                                auto& pixel = bitmap[y * width + x];
                                pixel = (pixel * (255 - alpha) + ink * alpha) / 255;
                            };
                            if (synthetic_bold) {
                                for (int i = -1; i <= 1; i++) {
                                    for (int j = -1; j <= 1; j++) {
                                        if (i == 0 && j == 0) continue;
                                        int btx = tx + i, bty = ty + j;
                                        if (btx >= 0 && btx < width && bty >= 0 && bty < height)
                                            blend(btx, bty, (int)(p * 0.6));
                                    }
                                }
                            }
                            blend(tx, ty, p);
                        }
                    }
                }
            }
        }
        pen_x += (int)(advance * local_scale);
    }
}
