import os
from dotenv import load_dotenv

# 1. 必须最先加载环境
load_dotenv()

import json
import platform
import subprocess
import shutil
from feeders import clock, weather, stock, timetable

# 配置文件路径
CONFIG_FILE = "config.json"


def main():
    print("=== Kindle Dashboard 自动化流程启动 ===")

    # 1. 加载现有的 config.json
    if not os.path.exists(CONFIG_FILE):
        print(f"错误：找不到 {CONFIG_FILE}")
        return

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)

    # 2. 调用各个模块更新数据 (以后在这里加一行就是加一个功能)
    
    config = clock.update(config)
    
    # 1. 检查是否有天气 Key，有才更新
    if os.getenv("WEATHER_KEY"):
        config = weather.update(config)
    else:
        print("[跳过] 未配置 WEATHER_KEY，不更新天气")

    # 2. 检查是否有股票列表
    if os.getenv("STOCK_LIST"):
        config = stock.update(config)
    else:
        print("[跳过] 未配置 STOCK_LIST，不更新股市")

    # 3. 检查是否有课表数据
    ics_data = os.getenv("ICS_DATA")
    if ics_data:
        # 只有在 GitHub 运行且有数据时才还原文件
        with open("dxdcourses2025Spring.ics", "w", encoding="utf-8") as f:
            f.write(ics_data)
        config = timetable.update(config)
    elif os.path.exists("dxdcourses2025Spring.ics"):
        # 本地运行，直接用本地文件
        config = timetable.update(config)
    else:
        print("[跳过] 未找到课表数据")

    # 3. 将更新后的数据保存回去
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
    print("✅ 配置文件已保存。")

    exe_name = "Kindle-Dashboard"
    if platform.system() == "Windows":
        build_dir = os.path.join(os.getcwd(), "build", "Debug") # 适配 Windows 可能的路径
        if not os.path.exists(build_dir):
            build_dir = os.path.join(os.getcwd(), "build")
        exe_path = os.path.join(build_dir, f"{exe_name}.exe")
    else:
        build_dir = os.path.join(os.getcwd(), "build")
        exe_path = os.path.join(build_dir, exe_name)

    assets = ["config.json", "main-font.TTF", "qweather-icons.ttf", "qweather-icons.json"]
    
    print("📂 正在同步资源文件到运行目录...")
    for asset in assets:
        if os.path.exists(asset):
            try:
                shutil.copy2(asset, build_dir) # 拷贝并保留元数据
                print(f"  - 已拷贝: {asset}")
            except Exception as e:
                print(f"  - 拷贝失败 {asset}: {e}")
    # ---------------------------------------------------------

    # 4. 自动调用 C++ 渲染引擎 (假设你已经编译好了)
    # 注意：我们的 CMake 会自动把 config.json 考到 build，
    # 但由于我们改的是根目录的，所以我们再次调用一次同步
    print("🚀 启动 C++ 渲染引擎...")
    try:
        # 先同步资源并编译
        subprocess.run(["cmake", "--build", "build"], check=True)
        
        # 核心修改：增加 encoding='utf-8'，并加上 errors='ignore' 防止一些奇怪符号导致崩溃
        result = subprocess.run(
            [exe_path], # 使用变量 
            capture_output=True, 
            text=True, 
            encoding='utf-8',   # 强制使用 UTF-8 解码
            errors='ignore',      # 万一还有解不出来的字节，直接忽略，不报错
            cwd=build_dir
        )
        print("--- C++ 标准输出 (stdout) ---")
        print(result.stdout)
        print("--- C++ 错误输出 (stderr) ---")
        print(result.stderr) # 【关键】：把错误打印出来！
        print("----------------------------")
    except Exception as e:
        print(f"❌ 运行失败: {e}")

if __name__ == "__main__":
    main()