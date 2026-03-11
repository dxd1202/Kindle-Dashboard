# 1. 要求 CMake 的最低版本
cmake_minimum_required(VERSION 3.10)

# 2. 定义项目名称（名字必须叫 Kindle-Dashboard）
project(Kindle-Dashboard VERSION 1.0)

# 3. 设置 C++ 标准为 17 (保证现代特性可用)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 4. 【关键】自动生成 clangd 需要的地图文件 (compile_commands.json)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# 5. 指定头文件存放目录
include_directories(include)

# 6. 定义你的可执行程序，以及它依赖的所有源代码文件
add_executable(Kindle-Dashboard 
    src/main.cpp 
    src/renderer.cpp
)