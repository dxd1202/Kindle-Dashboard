cmake_minimum_required(VERSION 3.10)
project(KindleDash)

# 设置 C++ 标准为 C++17
set(CMAKE_CXX_STANDARD 17)

# 导出编译命令，让 VS Code IntelliSense 能正确识别头文件路径
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# 告诉编译器：去哪里找头文件？
# PUBLIC "include" 意味着编译器会自动去 include 文件夹里找我们刚才放进去的 .h 文件
include_directories(include)

# 告诉编译器：我们要编译哪个文件？
# 这里我们把 src/main.cpp 加入编译目标
add_executable(KindleDash src/main.cpp src/renderer.cpp)