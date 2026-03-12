from datetime import datetime

def get_current_time_info():
    """获取格式化的当前日期、星期和时间"""
    # 1. 获取当前时间对象
    now = datetime.now()
    
    # 2. 定义星期映射
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    weekday_str = weekdays[now.weekday()]
    
    # 3. 格式化日期部分
    date_str = now.strftime("%Y年%m月%d日")
    
    # 4. 格式化时间部分
    time_str = now.strftime("%H:%M:%S")
    
    # --- 极客进阶：利用你的 C++ 字号缩放功能 ---
    # 我们让日期小一点(↓)，让时间大一点(↑)
    # 效果示例：↓2026年03月12日 周四○ ↑15:30○
    return f"最新抓取于：▷{date_str} {weekday_str}  {time_str}"

def update(config):
    """更新 config.json 中的 clock 组件"""
    time_content = get_current_time_info()
    
    for item in config.get("widgets", []):
        if item.get("id") == "clock":
            item["content"] = time_content
            break
            
    return config