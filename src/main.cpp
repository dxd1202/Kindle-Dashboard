#include <iostream>
#include <vector>

// 【重要】这是STB库的“开启开关”
// 只有在其中一个源文件里定义这个宏，库的代码才会被“展开”并编译
#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"

int main() {
  // 1448 x 1077 是 Kindle Paperwhite 的分辨率
  const int width = 1448;
  const int height = 1077;

  // 创建一个 buffer (内存数组)
  // 每一个像素由 R, G, B 三个分量组成，每个分量 1 字节 (0-255)
  // 255 代表白色
  std::vector<unsigned char> pixels(width * height * 3, 255);

  // 调用 stb_image_write 库的方法，把内存数组存成 PNG 文件
  stbi_write_png("output.png", width, height, 3, pixels.data(), width * 3);

  std::cout << "Success! [output.png] generated" << std::endl;
  return 0;
}