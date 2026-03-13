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

set(ASSET_FILES
    "${CMAKE_CURRENT_SOURCE_DIR}/config.json"
    "${CMAKE_CURRENT_SOURCE_DIR}/main-font.ttf"
    "${CMAKE_CURRENT_SOURCE_DIR}/qweather-icons.ttf"
)

# 遍历列表，为每个文件创建拷贝规则
foreach(ASSET_FILE ${ASSET_FILES})
    # 获取文件名（不带路径）
    get_filename_component(ASSET_NAME ${ASSET_FILE} NAME)
    
    # 每次 Build 之后，如果源文件有变动，就自动拷贝到生成可执行文件的目录下
    add_custom_command(
        TARGET ${PROJECT_NAME} POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
        "${ASSET_FILE}"
        "$<TARGET_FILE_DIR:${PROJECT_NAME}>/${ASSET_NAME}"
        COMMENT "正在同步资源文件: ${ASSET_NAME}"
    )
endforeach()