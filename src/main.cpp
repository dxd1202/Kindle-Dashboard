#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"
#include <iostream>
#include <vector>

int main() {
    // 【最关键的一行】：在程序开头先输出！
    std::cout << "--- Kindle-Dashboard Engine Starting ---" << std::endl;

    const int width = 1448;
    const int height = 1077;
    std::vector<unsigned char> pixels(width * height * 3, 255);

    int result = stbi_write_png("output.png", width, height, 3, pixels.data(), width * 3);

    if (result != 0) {
        std::cout << "Successfully created output.png!" << std::endl;
    }
    else {
        std::cout << "Failed to create output.png!" << std::endl;
    }

    return 0;
}