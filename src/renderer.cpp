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
    if (!file.is_open()) throw std::runtime_error("Font file not found!");
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

// 测量宽度函数：必须支持动态字号跟踪
int get_text_width(const std::vector<Font*>& fonts, const std::string& text, int base_size) {
    int current_size = base_size;
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
        if (cp == 9655 || cp == 9472 || cp == 9504) continue;

        // 遍历所有字体找宽度
        for (auto* f : fonts) {
            if (stbtt_FindGlyphIndex(&f->info, cp) != 0) {
                float s = stbtt_ScaleForPixelHeight(&f->info, (float)current_size);
                int adv, lsb;
                stbtt_GetCodepointHMetrics(&f->info, cp, &adv, &lsb);
                total_w += (int)(adv * s);
                break;
            }
        }
    }
    return total_w;
}

// 3. 核心绘图引擎
void draw_text(const std::vector<Font*>& fonts, unsigned char* bitmap, int width, int height,
               const char* text, int x, int y, int size, bool center_tabs, int tab_width) {
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
        int segment_w = get_text_width(fonts, segment, base_size);
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
            int current_col = (pen_x - x) / effective_tab;
            pen_x = x + (current_col + 1) * effective_tab;
            apply_centering();
            continue;
        }

        // --- 以下是渲染逻辑，保持 std::min 混合不变 ---
        Font* activeFont = nullptr;
        for (auto* f : fonts) {
            if (stbtt_FindGlyphIndex(&f->info, cp) != 0) {
                activeFont = f;
                break;
            }
        }
        if (!activeFont) activeFont = fonts[0];

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
                    int ty = current_y + pixel_ascent + y0 + row;

                    if (cp >= 0xF100 && cp < 0xFF00) ty += 10;

                    if (tx >= 0 && tx < width && ty >= 0 && ty < height) {
                        int p = char_bmp[row * char_w + col];
                        if (p > 0) {
                            int color = 255 - p;
                            bitmap[ty * width + tx] = std::min((int)bitmap[ty * width + tx], color);
                            if (is_bold_line) {
                                int bold_c = 255 - (int)(p * 0.6);
                                for (int i = -1; i <= 1; i++) {
                                    for (int j = -1; j <= 1; j++) {
                                        if (i == 0 && j == 0) continue;
                                        int btx = tx + i, bty = ty + j;
                                        if (btx < width && bty < height)
                                            bitmap[bty * width + btx] =
                                                std::min((int)bitmap[bty * width + btx], bold_c);
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        pen_x += (int)(advance * local_scale);
    }
}