#define STB_TRUETYPE_IMPLEMENTATION

#include "stb_truetype.h"
#include <fstream>
#include <vector>

// 这是一个简化的画字函数
void draw_text(unsigned char *bitmap, int width, int height, const char *text,
               int x, int y, int size) {
  // 读取字体文件
  std::ifstream fontFile("NOTO SANS SC.ttf", std::ios::binary);
  std::vector<unsigned char> fontData(
      (std::istreambuf_iterator<char>(fontFile)),
      std::istreambuf_iterator<char>());

  stbtt_fontinfo font;
  stbtt_InitFont(&font, fontData.data(), 0);

  // 渲染文字
  float scale = stbtt_ScaleForPixelHeight(&font, size);
  int ascent, descent, lineGap;
  stbtt_GetFontVMetrics(&font, &ascent, &descent, &lineGap);

  int pen_x = x;
  for (int i = 0; text[i]; ++i) {
    int advance, lsb;
    stbtt_GetCodepointHMetrics(&font, text[i], &advance, &lsb);

    int x0, y0, x1, y1;
    stbtt_GetCodepointBitmapBox(&font, text[i], scale, scale, &x0, &y0, &x1,
                                &y1);

    int byteOffset =
        (y + ascent * scale + y0) * width + (pen_x + lsb * scale + x0);
    stbtt_MakeCodepointBitmap(&font, bitmap + byteOffset, x1 - x0, y1 - y0,
                              width, scale, scale, text[i]);

    pen_x += advance * scale;
  }
}