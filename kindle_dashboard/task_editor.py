"""Serve a local form for editing the configured JSON task list."""

from hashlib import sha256
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import webbrowser

from .config import load_settings
from .tasks import decode_tasks, legacy_tasks, parse_due, task_file

PAGE = Path(__file__).with_name("task_editor.html")
SCHEDULE_PAGE = PAGE.with_name("calendar_editor.html")
EDITOR_STYLE = PAGE.with_name("editor.css")


def normalize_task(task):
    if not isinstance(task, dict):
        raise ValueError("任务应为 JSON 对象")
    title, due, done = task.get("title"), task.get("due"), task.get("done", False)
    if not isinstance(title, str) or not title.strip() or len(title.splitlines()) != 1:
        raise ValueError("请输入单行任务标题")
    if type(done) is not bool:
        raise ValueError("完成状态无效")
    if due not in (None, ""):
        try:
            due = parse_due(due).replace(tzinfo=None).isoformat()
        except (ValueError, TypeError, OverflowError):
            raise ValueError("截止时间无效，请选择有效的日期和时间") from None
    return {"title": title.strip(), "due": due or None, "done": done}


class TaskList:
    def __init__(self, path, settings):
        self.path = path.resolve()
        self.filename = path.name
        self.settings = settings

    def read(self):
        try:
            data = self.path.read_bytes()
        except FileNotFoundError:
            tasks = legacy_tasks(self.settings)
            if not isinstance(tasks, list):
                raise ValueError("旧清单的 tasks 应为数组")
            data = json.dumps(tasks, ensure_ascii=False).encode("utf-8")
            return "legacy:" + sha256(data).hexdigest(), tasks
        return sha256(data).hexdigest(), decode_tasks(data)

    def snapshot(self):
        revision, tasks = self.read()
        items = []
        for index, task in enumerate(tasks):
            try:
                items.append({"id": index, **normalize_task(task)})
            except ValueError as error:
                raise ValueError(f"第 {index + 1} 项：{error}") from error
        return {"revision": revision, "tasks": items, "filename": self.filename}

    def update(self, change):
        revision, tasks = self.read()
        if change.get("revision") != revision:
            return False
        action = change.get("action")
        if action == "add":
            tasks.append(normalize_task(change))
        else:
            index = change.get("id")
            if type(index) is not int or not 0 <= index < len(tasks):
                raise ValueError("任务已不存在")
            if action == "delete":
                del tasks[index]
            elif action == "edit":
                tasks[index] = {**tasks[index], **normalize_task(change)}
            elif action == "toggle" and type(change.get("done")) is bool:
                tasks[index] = {**tasks[index], "done": change["done"]}
            else:
                raise ValueError("未知操作")
        for index, task in enumerate(tasks, start=1):
            try:
                normalize_task(task)
            except ValueError as error:
                raise ValueError(f"第 {index} 项：{error}") from error
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=self.path.parent) as directory:
            staged = Path(directory) / self.path.name
            staged.write_text(json.dumps(tasks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            if self.read()[0] != revision:
                return False
            staged.replace(self.path)
        return True


class EditorHandler(BaseHTTPRequestHandler):
    def editor(self):
        return {"/api/tasks": self.server.tasks, "/api/calendar": self.server.calendar}.get(self.path)

    def log_message(self, _format, *args):
        pass

    def setup(self):
        self.request.settimeout(5)
        super().setup()

    def respond(self, status, data, content_type="application/json; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'unsafe-inline'; "
                         "style-src 'self'; connect-src 'self'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(data)

    def json_response(self, status, value):
        self.respond(status, json.dumps(value, ensure_ascii=False).encode("utf-8"))

    def do_GET(self):
        if self.headers.get("Host") != self.server.address:
            self.send_error(HTTPStatus.FORBIDDEN)
        elif self.path in ("/", "/calendar"):
            page = PAGE if self.path == "/" else SCHEDULE_PAGE
            self.respond(HTTPStatus.OK, page.read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/editor.css":
            self.respond(HTTPStatus.OK, EDITOR_STYLE.read_bytes(), "text/css; charset=utf-8")
        elif (editor := self.editor()) is not None:
            try:
                self.json_response(HTTPStatus.OK, editor.snapshot())
            except (OSError, ValueError, TypeError, KeyError, OverflowError) as error:
                self.json_response(HTTPStatus.BAD_REQUEST, {"error": f"读取失败：{error}"})
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self):
        if (self.headers.get("Host") != self.server.address
                or self.headers.get("Origin") != f"http://{self.server.address}"
                or self.headers.get_content_type() != "application/json"):
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        editor = self.editor()
        if editor is None:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 65536:
                raise ValueError("请求大小无效")
            change = json.loads(self.rfile.read(size))
            if not isinstance(change, dict):
                raise ValueError("请求格式无效")
            if not editor.update(change):
                self.json_response(HTTPStatus.CONFLICT, {"error": "文件已在别处修改，请重新读取后重试。"})
                return
            self.json_response(HTTPStatus.OK, editor.snapshot())
        except (OSError, ValueError, TypeError, KeyError, OverflowError) as error:
            self.json_response(HTTPStatus.BAD_REQUEST, {"error": f"保存失败：{error}"})


def run_editor():
    from .calendar_editor import CalendarEditor

    settings = load_settings()
    with HTTPServer(("127.0.0.1", 0), EditorHandler) as server:
        server.address = f"127.0.0.1:{server.server_port}"
        server.tasks = TaskList(task_file(settings), settings)
        server.calendar = CalendarEditor(settings)
        url = f"http://{server.address}"
        print(f"任务编辑器：{url}\n按 Ctrl+C 退出。", flush=True)
        webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
