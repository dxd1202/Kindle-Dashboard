"""Export the browser dashboard using only fields shown in its interface."""

from datetime import timedelta
import json
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory

from .config import ASSETS, ROOT, WEATHER_LOCATION, WEEKDAYS
from .layout.header import semester_progress
from .tasks import deadline_label

WEB = Path(__file__).with_name("mobile_web")


def mobile_payload(snapshot, *, mode, show_locations=False):
    if mode == "demo" and not snapshot.demo:
        raise ValueError("Demo mobile output requires a demo snapshot")
    now, weather = snapshot.now, snapshot.weather
    today = now.date()
    day_keys = [today + timedelta(days=offset) for offset in range(7)]
    personal = mode != "weather" and not snapshot.hide_personal
    days = []
    today_time = now.strftime("%H:%M")
    next_event = None
    if personal:
        for offset, day in enumerate(day_keys[:2]):
            events = []
            entries = sorted(snapshot.schedule.get(day, ()), key=lambda item: (item["time"] != "全天", item["time"]))
            for entry in entries:
                event = {key: entry[key] for key in ("time", "name", "end") if key in entry}
                if show_locations:
                    event["place"] = entry.get("place", "")
                if next_event is None and event["time"] != "全天" and (offset or event["time"] >= today_time):
                    next_event = {**event, "day": "今天" if offset == 0 else "明天"}
                events.append(event)
            days.append({"date": day.isoformat(), "events": events})

    forecast = []
    for index, day in enumerate(day_keys):
        key = day.isoformat()
        entry = weather.forecast.get(key, {})
        forecast.append({
            "date": key,
            "label": ("今天", "明天")[index] if index < 2 else WEEKDAYS[day.weekday()],
            **{field: entry[field] for field in ("icon", "condition", "low", "high", "humidity") if field in entry},
            "aqi": weather.air_quality.get(key),
        })

    current = None
    if weather.current:
        current = {key: weather.current.get(key) for key in ("icon", "condition", "temperature", "feels_like", "humidity", "uv_index")}
        current["observed"] = weather.current["observed_at"].isoformat()
    alerts = weather.alerts
    providers = []
    if not snapshot.demo:
        if weather.source == "Open-Meteo":
            providers.append({"name": "Open-Meteo（CC BY 4.0）", "url": "https://open-meteo.com/"})
        if weather.source == "和风天气" or weather.current or weather.air_quality or weather.current_aqi or alerts is not None:
            providers.append({"name": "和风天气", "url": "https://www.qweather.com/"})

    deadlines = []
    if personal:
        deadlines = [{"title": title, "due": due.isoformat(), "label": deadline_label(due, now), "overdue": due < now}
                     for due, title in snapshot.deadlines]
    return {
        "version": 1,
        "mode": "demo" if snapshot.demo else mode,
        "updated": now.isoformat(),
        "today": today.isoformat(),
        "weekday": WEEKDAYS[today.weekday()],
        "semester": semester_progress(today, snapshot.semester)[0] if snapshot.semester else None,
        "personal": personal,
        "days": days,
        "schedule_status": snapshot.schedule_status if personal else None,
        "next_event": next_event,
        "deadlines": deadlines,
        "todos": snapshot.todos if personal else [],
        "weather": {
            "location": f"{WEATHER_LOCATION.city} · {WEATHER_LOCATION.district}",
            "current": current,
            "aqi": weather.current_aqi,
            "alerts": alerts,
            "alert_credits": weather.alert_credits,
            "forecast": forecast,
            "status": weather.status,
            "fetched": weather.fetched_at.isoformat() if weather.fetched_at else None,
            "providers": providers,
        },
    }


def export_mobile(snapshot, output, *, mode, show_locations):
    output.mkdir(parents=True, exist_ok=True)
    payload = mobile_payload(snapshot, mode=mode, show_locations=show_locations or snapshot.demo)
    with TemporaryDirectory(dir=output) as stage_dir:
        stage = Path(stage_dir)
        for name in ("index.html", "app.css", "app.js"):
            copyfile(WEB / name, stage / name)
        copyfile(ASSETS / "qweather-icons.ttf", stage / "qweather-icons.ttf")
        copyfile(ROOT / "licenses/QWeather-Icons-MIT.txt", stage / "qweather-icons-LICENSE.txt")
        (stage / "dashboard.json").write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
        for file in stage.iterdir():
            file.replace(output / file.name)
