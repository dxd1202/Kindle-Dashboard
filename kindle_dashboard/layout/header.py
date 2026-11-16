from datetime import date

from lunardate import LunarDate

from ..config import WEEKDAYS
from .widgets import DARK, HEADER_RULE_HEIGHT, HEADER_RULE_Y, LEFT, MUTED, RIGHT


def lunar_label(day):
    months = ("正", "二", "三", "四", "五", "六", "七", "八", "九", "十", "冬", "腊")
    digits = "一二三四五六七八九十"
    try:
        lunar = LunarDate.from_solar_date(day.year, day.month, day.day)
    except ValueError:
        return "农历暂不可用"
    day_names = {
        10: "初十", 20: "二十", 30: "三十",
    }
    prefix = ("初", "十", "廿", "三十")[(lunar.day - 1) // 10]
    day_name = day_names.get(lunar.day, prefix + digits[(lunar.day - 1) % 10])
    leap = "闰" if lunar.is_leap_month else ""
    return f"农历{leap}{months[lunar.month - 1]}月{day_name}"


def semester_progress(today, semester):
    start = date.fromisoformat(semester["start"])
    weeks = int(semester["weeks"])
    if weeks < 1:
        raise ValueError("学期总周数至少为 1")
    elapsed = (today - start).days
    week = min(weeks, max(1, elapsed // 7 + 1))
    status = "尚未开学" if elapsed < 0 else "学期已结束" if elapsed >= weeks * 7 else f"第 {week} / {weeks} 周"
    return status, week / weeks if elapsed >= 0 else 0


def add_header(widgets, today, semester):
    text, rect, line = widgets.text, widgets.rect, widgets.line
    text(LEFT, 12, f"{today.month}月{today.day}日", 102, bold=True)
    text(440, 15, WEEKDAYS[today.weekday()].replace("周", "星期"), 45)
    text(440, 64, lunar_label(today), 38, gray=MUTED)
    text(745, 64, f"{today.year} 年第 {today.timetuple().tm_yday} 天", 38, gray=MUTED,
         max_width=286, fit_width=True)
    if semester:
        status, progress = semester_progress(today, semester)
        text(RIGHT - 320, 35, "学期进度", 36, gray=MUTED)
        text(RIGHT, 28, status, 43, align="right", bold=True)
        rect(RIGHT - 320, 86, RIGHT, 95, 218)
        rect(RIGHT - 320, 86, RIGHT - 320 + round(320 * progress), 95, DARK)
    else:
        text(RIGHT, 45, "学期进度未配置", 33, gray=MUTED, align="right")
    line(LEFT, HEADER_RULE_Y, RIGHT, DARK, HEADER_RULE_HEIGHT)
