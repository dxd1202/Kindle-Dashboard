from icalendar import Calendar
from datetime import datetime
import pytz
import os

# ================= 配置区 =================
ICS_FILE = "dxdcourses2025Spring.ics"
WEEKDAYS = ["周一", "周二", "周三", "周四", "周五"]
# 分割线长度，根据你的字体大小调整，确保能横跨屏幕
DIVIDER = "┠──────────────────────────────────" 
# ==========================================

def get_weekly_schedule():
    
    print("[课表模块] 正在生成全周分割线看板...")

    # 1. 检查物理文件是否存在 (本地运行通常走这里)
    if not os.path.exists(ICS_FILE):
        # 2. 如果文件不存在，检查环境变量 (GitHub Actions 运行走这里)
        ics_content = os.getenv("ICS_DATA")
        if ics_content:
            print("[课表模块] 检测到环境变量 ICS_DATA，正在生成临时文件...")
            with open(ICS_FILE, "w", encoding="utf-8") as f:
                f.write(ics_content)
        else:
            print("[课表模块] 错误：既找不到本地文件，也找不到环境变量数据！")
            return "未找到课表数据"
        
    try:
        with open(ICS_FILE, 'rb') as f:
            gcal = Calendar.from_ical(f.read())
        
        schedule = {i: [] for i in range(5)}
        tz = pytz.timezone('Asia/Shanghai')
        now = datetime.now(tz)
        today_weekday = now.weekday() 

        for component in gcal.walk():
            if component.name == "VEVENT":
                summary = str(component.get('summary'))
                location = str(component.get('location'))
                dtstart = component.get('dtstart').dt
                wday = dtstart.weekday()
                if wday < 5:
                    time_str = dtstart.strftime("%H:%M")
                    schedule[wday].append({
                        "time": time_str,
                        "name": summary,
                        "place": location
                    })

        final_output = []

        final_output.append("┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        for i in range(5):
            is_today = (i == today_weekday)
            
            # 1. 每一天的起始标记
            # 如果是今天，开头加 ▶ 开启 C++ 的加粗模式
            prefix = "▶" if is_today else "┃"
            
            day_courses = sorted(schedule[i], key=lambda x: x['time'])
            
            # 2. 构造当天的课程文字
            if not day_courses:
                final_output.append(f"{prefix}{WEEKDAYS[i]}：休息")
            else:
                for idx, course in enumerate(day_courses):
                    name = course['name']
                    place = course['place']
                    line_content = f"{course['time']} {name} [{place}]"
                    if idx == 0:
                        final_output.append(f"{prefix}{WEEKDAYS[i]}：{line_content}")
                    else:
                        # 使用全角空格缩进
                        final_output.append(f"┃　　　{line_content}")
            
            # 3. 【核心改动】添加一整行分割线来代替空行
            # 这一行开头的第一个字符就是 —，C++ 看到它会立刻把 is_bold 设为 false
            if (i != 4):
                final_output.append(DIVIDER)

        final_output.append("┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        return "\n".join(final_output)

    except Exception as e:
        print(f"[课表模块] 报错: {e}")
        return "课表解析失败"

# update 函数保持不变

def update(config):
    content = get_weekly_schedule()
    for item in config.get("widgets", []):
        if item.get("id") == "timetable":
            item["content"] = content
            break
    return config