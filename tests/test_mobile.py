from dataclasses import replace
from datetime import timedelta
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from kindle_dashboard.application import collect_dashboard
from kindle_dashboard.demo import DEMO_NOW
from kindle_dashboard.mobile import export_mobile, mobile_payload
from kindle_dashboard.sources.timetable import get_two_day_schedule


class MobileTests(unittest.TestCase):
    def setUp(self):
        self.demo = collect_dashboard(demo=True, offline=True, hide_personal=False)

    def test_demo_wire_format_and_assets(self):
        with TemporaryDirectory() as directory:
            output = Path(directory)
            export_mobile(self.demo, output, mode="demo", show_locations=False)
            data = json.loads((output / "dashboard.json").read_text())
            self.assertTrue({"index.html", "app.js", "app.css", "qweather-icons.ttf",
                             "qweather-icons-LICENSE.txt"} <= {file.name for file in output.iterdir()})
            self.assertEqual(data["next_event"], {
                "time": "14:30", "end": "16:05", "name": "数电实验", "place": "实验室", "day": "今天",
            })
            self.assertEqual(len(data["weather"]["forecast"]), 7)

    def test_live_data_export_requires_an_explicit_personal_mode(self):
        live = replace(self.demo, demo=False)
        entry = {"time": "15:00", "end": "16:00", "name": "个人日程", "place": "精确地点", "notes": "私密备注"}
        live.schedule = {live.now.date(): [entry]}
        with self.assertRaises(ValueError):
            mobile_payload(live, mode="demo")
        public = mobile_payload(live, mode="weather", show_locations=True)
        self.assertEqual((public["days"], public["deadlines"], public["todos"]), ([], [], []))
        self.assertIsNone(public["next_event"])
        personal = mobile_payload(live, mode="personal")
        self.assertEqual(personal["days"][0]["events"][0], {
            "time": "15:00", "end": "16:00", "name": "个人日程",
        })
        with_places = mobile_payload(live, mode="personal", show_locations=True)
        self.assertEqual(with_places["next_event"]["place"], "精确地点")
        self.assertNotIn("私密备注", json.dumps(with_places, ensure_ascii=False))
        hidden = mobile_payload(replace(live, hide_personal=True), mode="personal", show_locations=True)
        self.assertEqual(hidden["days"], [])
        self.assertEqual(hidden["todos"], [])

    @patch.dict("os.environ", {"ICS_DATA": "", "ICS_FILE": ""})
    def test_mobile_calendar_adds_end_times_without_changing_png_inputs(self):
        fixture = Path(__file__).resolve().parents[1] / "examples" / "calendar.ics"
        default, _ = get_two_day_schedule(DEMO_NOW, fixture)
        mobile, _ = get_two_day_schedule(DEMO_NOW, fixture, include_end=True)
        self.assertEqual(mobile[DEMO_NOW.date()][0]["end"], "10:30")
        self.assertEqual(default, {day: [{key: value for key, value in entry.items() if key != "end"}
                                       for entry in entries] for day, entries in mobile.items()})
        self.assertEqual(list(mobile), [DEMO_NOW.date(), DEMO_NOW.date() + timedelta(days=1)])
