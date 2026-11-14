#ifndef RENDERER_HPP
#define RENDERER_HPP

#include "stb_truetype.h"
#include <cstdint>
#include <string>
#include <vector>


struct Font
{
    std::vector<unsigned char> data;
    stbtt_fontinfo info;
    Font(const std::string& path);
};

// 【关键修改点】：第一个参数改为 fonts 列表
void draw_text(const std::vector<Font*>& fonts, unsigned char* bitmap, int width, int height,
               const char* text, int x, int y, int size, bool center_tabs = false,
               int tab_width = 0, int ink = 0);

int measure_text(const std::vector<Font*>& fonts, const std::string& text, int size);
std::vector<std::string> wrap_todo(const std::vector<Font*>& fonts, const std::string& text,
                                  int size, int width);
int text_center_offset(const std::vector<Font*>& fonts, const std::string& text, int size);

#endif
