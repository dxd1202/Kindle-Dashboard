import requests
import json
import os

# ================= 配置区 =================
# 1. 填入你申请的 API KEY
API_KEY = "e3b714910ce74b1bbdc2d7bfd802cffd"
# 2. 填入城市 ID (101010100 是北京)
CITY_ID = "101010100" 

# 3. 你的配置文件名
CONFIG_FILE = "config.json"
# ==========================================

def get_weather_data():
    """从和风天气 API 获取实时数据"""
    print(f"[1/3] 正在从和风天气获取实时数据 (城市ID: {CITY_ID})...")
    
    url = "https://pt4wcutkrg.re.qweatherapi.com/v7/weather/now"
    params = {
        "location": CITY_ID,
        "key": API_KEY,
        "gzip": "n"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data['code'] == "200":
            now = data['now']
            # 我们提取：天气文字 + 温度 + 湿度
            weather_str = f"{now['text']} {now['temp']}°C 湿度:{now['humidity']}%"
            print(f"[2/3] 数据获取成功: {weather_str}")
            return weather_str
        else:
            print(f"[错误] API返回状态码异常: {data['code']}")
            return None
    except Exception as e:
        print(f"[错误] 网络请求失败: {e}")
        return None

def update_config_file(new_weather):
    """精确更新 config.json 中 ID 为 weather 的组件"""
    if not os.path.exists(CONFIG_FILE):
        print(f"[错误] 找不到配置文件: {CONFIG_FILE}")
        return

    # 读取现有的 JSON 内容
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        try:
            config_data = json.load(f)
        except json.JSONDecodeError:
            print("[错误] config.json 格式损坏，无法解析")
            return

    # 在 widgets 列表中搜索 ID
    found = False
    if "widgets" in config_data:
        for item in config_data["widgets"]:
            if item.get("id") == "weather":
                item["content"] = new_weather
                found = True
                break
    
    if found:
        # 写回文件，保持格式缩进
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=4)
        print(f"[3/3] 已成功更新 {CONFIG_FILE}")
    else:
        print("[警告] 在 JSON 中没有找到 id 为 'weather' 的组件，更新取消")

if __name__ == "__main__":
    # 执行流程
    weather_info = get_weather_data()
    if weather_info:
        update_config_file(weather_info)
    else:
        print("[中止] 由于抓取失败，未修改配置文件")