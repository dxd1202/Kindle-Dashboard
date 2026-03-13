import requests
import json
import os

# ================= 配置区 =================
API_KEY = os.getenv("WEATHER_KEY")
BASE_URL = os.getenv("WEATHER_HOST")
CITY_ID = "101010200"  # 海淀
ICON_DATA_FILE = "qweather-icons.json"
# ==========================================

def load_icon_map():
    if not os.path.exists(ICON_DATA_FILE):
        print(f"[警告] 找不到 {ICON_DATA_FILE}，将无法显示图标！")
        return {}
    with open(ICON_DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

# 全局变量存储码表
ICON_MAP = load_icon_map()

def get_icon_char(icon_id):
    """通过读取到的 ICON_MAP 进行转换"""
    try:
        # 1. 尝试获取 ID 对应的十进制码点
        # 注意：API 返回的 ID 是字符串，JSON 里的 key 也是字符串
        code_point = ICON_MAP.get(str(icon_id))
        
        if code_point:
            return chr(int(code_point))
        else:
            print(f"[天气] 警告: 未知图标 ID {icon_id}")
            return chr(ICON_MAP.get("999", 61766)) # 返回“未知”图标
    except Exception as e:
        print(f"[天气] 转换出错: {e}")
        return "?"

def get_weather_now():
    """获取实时天气及其图标"""
    print(f"[天气模块] 正在获取实时数据 (ID: {CITY_ID})...")
    url = f"{BASE_URL}/now"
    params = {"location": CITY_ID, "key": API_KEY, "gzip": "n"}
    
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data['code'] == "200":
            n = data['now']
            icon = get_icon_char(n['icon'])
            text = f"当前({n['obsTime'][11:16]})     ▷{n['text']}    {n['temp']}°C\n湿度{n['humidity']}%      {n['windDir']}{n['windScale']}级\n体感{n['feelsLike']}°C"
            return icon, text
    except Exception as e:
        print(f"[天气] 实时获取失败: {e}")
    return "", "实时获取失败"

def get_weather_hourly():
    """获取 24 小时预报并格式化为 3行/组 的网格样式"""
    url = f"{BASE_URL}/24h"
    params = {"location": CITY_ID, "key": API_KEY, "gzip": "n"}
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()

        if data['code'] == "200":
            h_list = data['hourly'][:24]
            # --- 【新增】：提取更新时间 ---
            # 原始格式如: "2026-03-12T14:35+08:00"
            raw_update_time = data.get('updateTime', '')
            update_time_display = raw_update_time[11:16] if raw_update_time else "未知"

            final_lines = []
            
            # 每 6 个小时一组
            for i in range(0, 24, 6):
                chunk = h_list[i:i+6]
        
                # 第一行：小时 (▷开启加粗)
                row_time = "▷" + "\t".join([f"{h['fxTime'][11:13]}时" for h in chunk])
                
                # 第二行：图标 (这里是关键！每一列放一个图标字符)
                row_icon = "↓" + "\t".join([get_icon_char(h['icon']) for h in chunk]) + "○"
        
                # 第三行：天气+温度
                row_data = "↓" + "\t".join([f"{h['text'][:2]}{h['temp']}°" for h in chunk]) + "○"
        
                final_lines.append(row_time)
                final_lines.append(row_icon)
                final_lines.append(row_data)
                # final_lines.append("") # 组间留空行

            # --- 2. 【核心新增】：在列表最后添加一行小字更新时间 ---
            # 使用 ↓ 缩小字号，让它看起来像个页脚（Footer）
            footer = f"↓───── (数据更新于 {update_time_display}) ─────○"
            final_lines.append(footer)
            
            return "\n".join(final_lines)
        
    except Exception as e:
        print(f"[天气] 24h预报获取失败: {e}")
    return "24小时预报获取失败"

def update(config):
    """更新 config.json 中的实时天气、天气图标、小时预报"""
    now_icon, now_text = get_weather_now()
    hourly_content = get_weather_hourly()
    
    found_flags = {"now": False, "icon": False, "hourly": False}
    
    for item in config.get("widgets", []):
        # 1. 实时天气文字
        if item.get("id") == "weather_now":
            item["content"] = now_text
            found_flags["now"] = True
        
        # 2. 实时天气图标 (注意：这个 ID 需要你在 config.json 里手动添加)
        if item.get("id") == "weather_icon":
            item["content"] = now_icon
            # 这里的 font 必须在 config.json 里写为 "qweather-icons.ttf"
            found_flags["icon"] = True
            
        # 3. 小时预报
        if item.get("id") == "weather_hourly":
            item["content"] = hourly_content
            # 注意：小时预报现在也包含了图标字符
            # 如果你希望图标正常显示，你可能需要让这个组件也使用 qweather-icons.ttf
            # 或者（更高级的做法）将其拆分为两个组件，目前建议将此组件 font 设为普通字体，
            # 图标会变成小方块。若要图标也显示，建议此组件 font 设为图标字体。
            found_flags["hourly"] = True
            
    # 打印状态
    for k, v in found_flags.items():
        if not v: print(f"[天气] 警告：JSON 中未找到 ID: weather_{k}")
        
    return config