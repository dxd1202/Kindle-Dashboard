from datetime import datetime, time, timedelta, timezone
import os
from pathlib import Path
import re

from dateutil import rrule
from icalendar import Calendar

from ..config import BEIJING, ROOT

LOCAL_ICS = ROOT / "timetable.local.ics"


def calendar_file(local_path=None):
    path = os.getenv("ICS_FILE")
    if path:
        return Path(path).expanduser()
    return local_path if local_path is not None else LOCAL_ICS


def read_calendar(local_path=None):
    data = os.getenv("ICS_DATA")
    if data and data.strip():
        return data
    path = calendar_file(local_path)
    try:
        return path.read_bytes()
    except FileNotFoundError:
        if local_path is not None or os.getenv("ICS_FILE"):
            raise
        return None


def event_datetime(value, tz):
    if not isinstance(value, datetime):
        value = datetime.combine(value, time.min)
    if value.tzinfo is None:
        value = value.replace(tzinfo=tz)
    return value


def recurrence_dates(event, name, tz):
    properties = event.get(name, [])
    if not isinstance(properties, list):
        properties = [properties]
    for prop in properties:
        for occurrence in prop.dts:
            value = occurrence.dt
            if isinstance(value, tuple):
                value = value[0]
            yield event_datetime(value, tz)


def recurrence_rule(event, start):
    rule = event.get("RRULE").to_ical().decode("ascii")

    # The original course export uses local UNTIL values with a TZID.
    def local_until_to_utc(match):
        value = match[1]
        if len(value) == 8:
            end = datetime.strptime(value, "%Y%m%d").replace(
                hour=23, minute=59, second=59, tzinfo=start.tzinfo
            )
        else:
            end = datetime.strptime(value, "%Y%m%dT%H%M%S").replace(tzinfo=start.tzinfo)
        return "UNTIL=" + end.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    rule = re.sub(
        r"\bUNTIL=(\d{8}(?:T\d{6})?)(?=;|$)", local_until_to_utc, rule
    )
    return rrule.rrulestr(rule, dtstart=start)


def recurrence_key(value, tz):
    if isinstance(value, datetime):
        return event_datetime(value, tz).astimezone(timezone.utc)
    return value


def courses_between(calendar, first_day, days):
    start = datetime.combine(first_day, time.min, tzinfo=BEIJING)
    end = start + timedelta(days=days)
    schedule = {first_day + timedelta(days=offset): [] for offset in range(days)}

    events = calendar.walk("VEVENT")
    masters = {str(event["UID"]): event for event in events
               if "UID" in event and "RECURRENCE-ID" not in event}
    overrides = {}
    for event in events:
        if "RECURRENCE-ID" not in event:
            continue
        uid = str(event.get("UID", ""))
        master = masters.get(uid)
        original = event.decoded("RECURRENCE-ID")
        tz = BEIJING
        if master and "DTSTART" in master:
            tz = event_datetime(master.decoded("DTSTART"), BEIJING).tzinfo
        key = (uid, recurrence_key(original, tz))
        previous = overrides.get(key)
        if previous is None or int(event.get("SEQUENCE", 0)) >= int(previous.get("SEQUENCE", 0)):
            overrides[key] = event

    def add_occurrence(occurrence, original_start, event, master):
        local = occurrence.astimezone(BEIJING)
        if start <= local < end:
            schedule[local.date()].append({
                "time": local.strftime("%H:%M") if isinstance(original_start, datetime) else "全天",
                "name": str(event.get("SUMMARY", master.get("SUMMARY", "未命名课程"))),
                "place": str(event.get("LOCATION", master.get("LOCATION", ""))),
            })

    for event in events:
        if "RECURRENCE-ID" in event:
            continue
        if str(event.get("STATUS", "")).upper() == "CANCELLED":
            continue
        uid = str(event.get("UID", ""))
        original_start = event.decoded("DTSTART")
        event_start = event_datetime(original_start, BEIJING)
        occurrences = rrule.rruleset()
        occurrences.rdate(event_start)
        if "RRULE" in event:
            occurrences.rrule(recurrence_rule(event, event_start))
        for value in recurrence_dates(event, "RDATE", event_start.tzinfo):
            occurrences.rdate(value)
        for value in recurrence_dates(event, "EXDATE", event_start.tzinfo):
            occurrences.exdate(value)

        for occurrence in occurrences.between(start, end, inc=True):
            original = occurrence if isinstance(original_start, datetime) else occurrence.date()
            if (uid, recurrence_key(original, event_start.tzinfo)) in overrides:
                continue
            add_occurrence(occurrence, original_start, event, event)

    for (uid, _), event in overrides.items():
        if str(event.get("STATUS", "")).upper() == "CANCELLED":
            continue
        master = masters.get(uid, {})
        if str(master.get("STATUS", "")).upper() == "CANCELLED":
            continue
        original_start = event.decoded("DTSTART") if "DTSTART" in event else event.decoded("RECURRENCE-ID")
        tz = event_datetime(master.decoded("DTSTART"), BEIJING).tzinfo if master else BEIJING
        add_occurrence(event_datetime(original_start, tz), original_start, event, master)
    return schedule


def get_two_day_schedule(now, local_path=None):
    try:
        source = read_calendar(local_path)
        if not source:
            return {}, "日程未配置"
        return courses_between(Calendar.from_ical(source), now.date(), 2), "暂无日程"
    except (OSError, ValueError, TypeError, KeyError, OverflowError) as error:
        print(f"[日程] 读取失败: {type(error).__name__}")
        return {}, "日程读取失败"
