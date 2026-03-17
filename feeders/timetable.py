from icalendar import Calendar
from datetime import datetime, timedelta
import pytz
import os
from dateutil import rrule # 需要确保环境安装了 python-dateutil

# ================= 配置区 =================
ICS_FILE = "dxdcourses2025Spring.ics"
WEEKDAYS = ["周一", "周二", "周三", "周四", "周五"]
# 分割线长度，根据你的字体大小调整，确保能横跨屏幕
DIVIDER = "┠──────────────────────────────────" 
# ==========================================

def get_weekly_schedule():
    print("[课表模块] 正在生成本周动态课表...")

    # 文件检查逻辑
    if not os.path.exists(ICS_FILE):
        ics_content = os.getenv("ICS_DATA")
        if ics_content:
            with open(ICS_FILE, "w", encoding="utf-8") as f:
                f.write(ics_content)
        else:
            return "未找到课表数据"
        
    try:
        with open(ICS_FILE, 'rb') as f:
            gcal = Calendar.from_ical(f.read())
        
        tz = pytz.timezone('Asia/Shanghai')
        now = datetime.now(tz)
        
        # 【核心修改 1】把本周范围转为“无时区”的本地时间
        monday_start = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
        friday_end = monday_start + timedelta(days=4, hours=23, minutes=59)

        schedule = {i: [] for i in range(5)}

        for component in gcal.walk():
            if component.name == "VEVENT":
                summary = str(component.get('summary'))
                location = str(component.get('location'))
                dtstart = component.get('dtstart').dt
                
                # 处理 dtstart 格式并【核心修改 2】强行去除时区信息
                if not isinstance(dtstart, datetime):
                    dtstart = datetime.combine(dtstart, datetime.min.time())
                
                # 无论原来有没有时区，统一转为 naive 格式（无时区）
                dtstart = dtstart.replace(tzinfo=None)

                rrule_prop = component.get('rrule')
                if rrule_prop:
                    rrule_str = rrule_prop.to_ical().decode('utf-8')
                    
                    # 【核心修改 3】增加 ignoretz=True，忽略标准中对 UNTIL 的时区要求
                    try:
                        rule = rrule.rrulestr(rrule_str, dtstart=dtstart, ignoretz=True)
                        occurrences = rule.between(monday_start, friday_end, inc=True)
                    except Exception as rrule_err:
                        print(f"解析规则出错 {summary}: {rrule_err}")
                        occurrences = []
                else:
                    occurrences = [dtstart] if monday_start <= dtstart <= friday_end else []

                for occ in occurrences:
                    wday = occ.weekday()
                    if wday < 5:
                        schedule[wday].append({
                            "time": occ.strftime("%H:%M"),
                            "name": summary,
                            "place": location
                        })

        # --- 以下生成文字部分的逻辑基本不变 ---
        final_output = []
        final_output.append("┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        today_weekday = now.weekday()

        for i in range(5):
            is_today = (i == today_weekday)
            prefix = "▶" if is_today else "┃"
            
            day_courses = sorted(schedule[i], key=lambda x: x['time'])
            
            if not day_courses:
                final_output.append(f"{prefix}{WEEKDAYS[i]}：休息")
            else:
                for idx, course in enumerate(day_courses):
                    line_content = f"{course['time']} {course['name']} [{course['place']}]"
                    if idx == 0:
                        final_output.append(f"{prefix}{WEEKDAYS[i]}：{line_content}")
                    else:
                        final_output.append(f"┃　　　{line_content}")
            
            if i != 4:
                final_output.append(DIVIDER)

        final_output.append("┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        return "\n".join(final_output)

    except Exception as e:
        print(f"[课表模块] 报错: {e}")
        import traceback
        traceback.print_exc()
        return "课表解析失败"

# update 函数保持不变

def update(config):
    content = get_weekly_schedule()
    for item in config.get("widgets", []):
        if item.get("id") == "timetable":
            item["content"] = content
            break
    return config