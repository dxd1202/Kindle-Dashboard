#define STB_TRUETYPE_IMPLEMENTATION
#include "renderer.hpp"
#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <vector>

const float LINE_HEIGHT = 0.95;
const float UPSCALE = 1.2;
const float DOWNSCALE = 0.85;

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

// 测量宽度函数：必须支持动态字号跟踪
static int get_text_width(const std::vector<Font*>& fonts, const std::string& text,
                          int base_size, int current_size) {
    int total_w = 0;
    const char* ptr = text.c_str();

    while (*ptr) {
        uint32_t cp = next_utf8(ptr);

        // 缩放控制不计入宽度
        if (cp == 8593) {
            current_size = (int)(base_size * UPSCALE);
            continue;
        }
        if (cp == 8595) {
            current_size = (int)(base_size * DOWNSCALE);
            continue;
        }
        if (cp == 9675) {
            current_size = base_size;
            continue;
        }

        // 信号符不计入宽度
        if (cp == 9655) continue;

        // 遍历所有字体找宽度
        auto* font = glyph_font(fonts, cp);
        float scale = stbtt_ScaleForPixelHeight(&font->info, (float)current_size);
        int advance, lsb;
        stbtt_GetCodepointHMetrics(&font->info, cp, &advance, &lsb);
        total_w += (int)(advance * scale);
    }
    return total_w;
}

int measure_text(const std::vector<Font*>& fonts, const std::string& text, int size) {
    return get_text_width(fonts, text, size, size);
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
        if (cp == 9655) continue;
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

// 3. 核心绘图引擎
void draw_text(const std::vector<Font*>& fonts, unsigned char* bitmap, int width, int height,
               const char* text, int x, int y, int size, bool center_tabs, int tab_width, int ink) {
    if (fonts.empty()) return;

    int base_size = size;
    int current_size = size;
    float current_scale;
    int ascent, descent, lineGap, pixel_ascent;

    auto update_size = [&](int new_size) {
        current_size = new_size;
        current_scale = stbtt_ScaleForPixelHeight(&fonts[0]->info, (float)current_size);
        stbtt_GetFontVMetrics(&fonts[0]->info, &ascent, &descent, &lineGap);
        pixel_ascent = (int)(ascent * current_scale);
    };

    update_size(base_size);

    int pen_x = x;
    int column = 0;
    int current_y = y;
    const char* ptr = text;

    // --- 核心状态位修改 ---
    bool is_bold_line = false;
    bool bold_is_persistent = false;   // 是否是持久加粗（跨行）

    auto apply_centering = [&]() {
        if (!center_tabs || tab_width <= 0 || *ptr == '\0' || *ptr == '\n' || *ptr == '\t') return;
        std::string segment = "";
        const char* temp_ptr = ptr;
        while (*temp_ptr && *temp_ptr != '\t' && *temp_ptr != '\n') {
            segment += *temp_ptr++;
        }
        // 注意：get_text_width 也需要更新以匹配这个多字体逻辑，见下文
        int segment_w = get_text_width(fonts, segment, base_size, current_size);
        int offset = (tab_width - segment_w) / 2;
        if (offset > 0) pen_x += offset;
    };

    apply_centering();

    while (*ptr) {
        uint32_t cp = next_utf8(ptr);

        // 1. 处理加粗开关信号 (在渲染前判断)
        if (cp == 9654) {   // ▶ 实心三角：开启【持久】加粗
            is_bold_line = true;
            bold_is_persistent = true;
            // continue;   // 不画出这个字符
        }
        if (cp == 9655) {   // ▷ 空心三角：开启【单行】加粗
            is_bold_line = true;
            bold_is_persistent = false;
            continue;   // 不画出这个字符
        }
        if (cp == 9472 || cp == 9504 || cp == 9675) {   // ─, ┠, ○：强制关闭所有加粗
            is_bold_line = false;
            bold_is_persistent = false;
            if (cp == 9675) {
                update_size(base_size);
                continue;
            }   // ○ 还要重置字号
        }

        // 2. 处理换行
        if (cp == '\n') {
            pen_x = x;
            column = 0;
            current_y += (int)(current_size * LINE_HEIGHT);
            // 如果不是持久加粗，则换行重置
            if (!bold_is_persistent) {
                is_bold_line = false;
            }
            apply_centering();
            continue;
        }

        // 3. 处理字号缩放
        if (cp == 8593) {
            update_size((int)(base_size * UPSCALE));
            continue;
        }
        if (cp == 8595) {
            update_size((int)(base_size * DOWNSCALE));
            continue;
        }

        // 4. 处理 Tab
        if (cp == 9) {
            int effective_tab = (tab_width > 0 ? tab_width : 100);
            // Keep centered cells tied to their column even if a label overflows.
            if (center_tabs) {
                pen_x = x + (++column) * effective_tab;
            } else {
                int current_col = (pen_x - x) / effective_tab;
                pen_x = x + (current_col + 1) * effective_tab;
            }
            apply_centering();
            continue;
        }

        // --- 以下是渲染逻辑，保持 std::min 混合不变 ---
        Font* activeFont = glyph_font(fonts, cp);

        float local_scale = stbtt_ScaleForPixelHeight(&activeFont->info, (float)current_size);
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
                    int ty = current_y + pixel_ascent + y0 + row + glyph_y_offset(cp);

                    if (tx >= 0 && tx < width && ty >= 0 && ty < height) {
                        int p = char_bmp[row * char_w + col];
                        if (p > 0) {
                            auto blend = [&](int x, int y, int alpha) {
                                auto& pixel = bitmap[y * width + x];
                                pixel = (pixel * (255 - alpha) + ink * alpha) / 255;
                            };
                            if (is_bold_line) {
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
