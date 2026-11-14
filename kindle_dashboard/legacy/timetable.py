"""Weekly timetable text for the original JSON layout."""

from datetime import datetime, timedelta

from icalendar import Calendar

from ..config import BEIJING, WEEKDAYS
from ..sources.timetable import courses_between, read_calendar

DIVIDER = "┠──────────────────────────────────"


def weekly_courses(calendar, now):
    monday = now.date() - timedelta(days=now.weekday())
    return {
        day.weekday(): entries
        for day, entries in courses_between(calendar, monday, 5).items()
    }


def render_schedule(schedule, today_weekday):
    final_output = []
    final_output.append("┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

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


def get_weekly_schedule():
    try:
        source = read_calendar()
        if not source:
            return "课表未配置"
        calendar = Calendar.from_ical(source)
        now = datetime.now(BEIJING)
        schedule = weekly_courses(calendar, now)
        if not any(schedule.values()):
            return "本周课表无记录"
        return render_schedule(schedule, now.weekday())
    except (OSError, ValueError, TypeError, KeyError, OverflowError) as error:
        print(f"[课表] 读取失败: {type(error).__name__}")
        return "课表读取失败"


def update(config):
    for widget in config["widgets"]:
        if widget.get("id") == "timetable":
            widget["content"] = get_weekly_schedule()
            break
    return config
