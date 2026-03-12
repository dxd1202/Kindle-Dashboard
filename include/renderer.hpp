#ifndef RENDERER_HPP
#define RENDERER_HPP

#include "stb_truetype.h"
#include <cstdint>   // 必须有这个，否则 uint32_t 报错
#include <string>
#include <vector>


struct Font
{
    std::vector<unsigned char> data;
    stbtt_fontinfo info;
    Font(const std::string& path);
};

void draw_text(Font& font, unsigned char* bitmap, int width, int height, const char* text, int x,
               int y, int size);

#endif