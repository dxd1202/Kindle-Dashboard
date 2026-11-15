"""Classify unfinished tasks for the dashboard."""

from datetime import datetime, timedelta
import json

from .config import BEIJING, ROOT, WEEKDAYS


def task_file(settings):
    path = ROOT / (settings.get("tasks_file") or "tasks.local.json")
    if path.suffix.lower() != ".json":
        raise ValueError("tasks_file 应指向 .json 任务清单")
    return path


def parse_due(value):
    due = datetime.fromisoformat(value)
    return due.replace(tzinfo=BEIJING) if due.tzinfo is None else due.astimezone(BEIJING)


def decode_tasks(data):
    tasks = json.loads(data.decode("utf-8-sig"))
    if not isinstance(tasks, list):
        raise ValueError("任务清单应为 JSON 数组")
    return tasks


def deadline_label(due, now):
    days = (due.date() - now.date()).days
    if days < 0:
        return f"逾期 {due:%m/%d}"
    if due < now:
        return "逾期 " + due.strftime("%H:%M")
    if days == 0:
        return ("今晚 " if due.hour >= 18 else "今天 ") + due.strftime("%H:%M")
    if days == 1:
        return "明天 " + due.strftime("%H:%M")
    return WEEKDAYS[due.weekday()] + due.strftime(" %H:%M")


def dashboard_tasks(settings, today, *, path=None):
    deadlines, todos = [], []
    deadline_limit = today + timedelta(days=7)
    try:
        if path is None:
            tasks = settings.get("tasks", [])
        else:
            try:
                tasks = decode_tasks(path.read_bytes())
            except FileNotFoundError:
                tasks = []
    except (OSError, ValueError) as error:
        print(f"[任务] 读取任务清单失败：{error}")
        return deadlines, todos
    if not isinstance(tasks, list):
        print("[任务] tasks 应为数组，已跳过")
        return deadlines, todos
    for index, task in enumerate(tasks, start=1):
        label = f"第 {index} 项"
        if not isinstance(task, dict):
            print(f"[任务] {label}应为对象，已跳过")
            continue
        done = task.get("done", False)
        if not isinstance(done, bool):
            print(f"[任务] {label}的 done 应为 true 或 false，已跳过")
            continue
        if done:
            continue
        title = task.get("title")
        if not isinstance(title, str) or not title.strip():
            print(f"[任务] {label}的 title 应为非空文本，已跳过")
            continue
        due = task.get("due")
        if due is None or due == "":
            todos.append(title)
            continue
        try:
            due = parse_due(due)
        except (TypeError, ValueError, OverflowError):
            print(f"[任务] {label}的 due 日期格式无效，已跳过")
            continue
        if due.date() < deadline_limit:
            deadlines.append((due, title))
    deadlines.sort()
    return deadlines, todos
