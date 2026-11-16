"use strict";

const main = document.querySelector("#main");
const status = document.querySelector("#status");
const refresh = document.querySelector("#refresh");
const nav = [...document.querySelectorAll("[data-view]")];
const beijingTime = new Intl.DateTimeFormat("zh-CN", {
  timeZone: "Asia/Shanghai", hour: "2-digit", minute: "2-digit", hourCycle: "h23",
});
const beijingDate = new Intl.DateTimeFormat("zh-CN", {
  timeZone: "Asia/Shanghai", month: "numeric", day: "numeric",
});
let data = null;
let issue = "";
let selectedDay = 0;
let taskFilter = "open";
let taskQuery = "";
let taskClient = null;
let taskSnapshot = null;
let taskTargetKey = "";
let taskBusy = false;
let taskMessage = "";
let draftTitle = "";
let draftDue = "";
let draftId = "";
let editingTask = null;
let calendarDraft = null;
let calendarToken = "";
let calendarBusy = false;
let calendarMessage = "";
let calendarRun = "";
let savedCalendarRevision = "";
const editorFilters = [["open", "进行中"], ["due", "有截止"], ["done", "已完成"], ["all", "全部"]];

function clearTaskDraft() {
  draftTitle = draftDue = draftId = "";
  editingTask = null;
}

function updateTaskSnapshot(snapshot) {
  if (editingTask && !snapshot.tasks.includes(editingTask)) {
    const before = JSON.stringify(editingTask);
    const matches = snapshot.tasks.filter(task => JSON.stringify(task) === before);
    if (matches.length === 1) editingTask = matches[0];
  }
  taskSnapshot = snapshot;
}

function localDeadline(value) {
  if (typeof value !== "string") return "";
  if (!/(?:Z|[+-]\d{2}:?\d{2})$/i.test(value)) return value.slice(0, 19);
  const stamp = Date.parse(value);
  return Number.isFinite(stamp) ? new Date(stamp + 8 * 3600_000).toISOString().slice(0, 19) : "";
}

function element(tag, className, ...children) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  node.append(...children);
  return node;
}

function link(label, target, className = "link") {
  const node = element("a", className, label);
  node.href = target;
  return node;
}

function glyph(value) {
  const node = element("span", "glyph", value || "");
  node.setAttribute("aria-hidden", "true");
  return node;
}

function panel(title, action, className = "") {
  const head = element("div", "panel-head", element("h2", "", title));
  if (action) head.append(action);
  return element("section", `panel ${className}`.trim(), head);
}

function hero(title, subtitle) {
  main.append(element("div", "hero", element("h1", "", title), element("p", "", subtitle)));
}

function dateLabel(value) {
  return beijingDate.format(new Date(`${value}T00:00:00+08:00`));
}

function timeLabel(value) {
  return beijingTime.format(new Date(value));
}

function showStatus(view) {
  if (issue) {
    const previous = data ? ` · 保留 ${dateLabel(data.today)} ${timeLabel(data.updated)} 的数据` : "";
    status.textContent = `更新失败，点右上角重试${previous}`;
  } else if (data) {
    const stamp = `${dateLabel(data.today)} ${timeLabel(data.updated)}`;
    const stale = Date.now() - Date.parse(data.updated) > 150 * 60_000;
    status.textContent = data.mode === "demo" ? "示例数据"
      : view === "tasks" && data.task_editor ? ""
      : `${stale ? "数据可能已过期" : "看板更新"} · ${stamp}（北京时间）`;
  }
  status.hidden = status.textContent === "";
  status.classList.toggle("error", Boolean(issue));
}

function showAlerts() {
  for (const alert of data.weather.alerts || []) {
    main.append(element("aside", "panel alert", element("h2", "card-title", "天气预警"), element("p", "", alert)));
  }
}

function humidity(value) {
  return value == null ? "—" : `${Math.round(value * 100)}%`;
}

function currentWeather() {
  const { current, forecast, aqi, status: weatherStatus, fetched } = data.weather;
  const card = panel("当前天气", null, "weather");
  if (current) {
    card.append(element("div", "weather-reading", glyph(current.icon),
      element("strong", "temperature", `${current.temperature}°`), current.condition || ""));
    card.append(element("p", "", `实况观测 ${timeLabel(current.observed)}（北京时间）`));
    const stats = [
      `体感 ${current.feels_like == null ? "—" : `${current.feels_like}°`}`,
      `湿度 ${humidity(current.humidity)}`, `AQI ${aqi ?? "—"}`, `UV ${current.uv_index ?? "—"}`,
    ];
    card.append(element("div", "weather-stats", ...stats.map(text => element("span", "", text))));
  } else if (forecast[0]?.condition) {
    const today = forecast[0];
    card.append(element("div", "weather-reading", glyph(today.icon),
      element("strong", "temperature", `${today.low}° / ${today.high}°`), today.condition));
    card.append(element("p", "", fetched ? `今日预报 · 获取于 ${timeLabel(fetched)}（北京时间）` : "今日预报"));
  } else {
    card.append(element("p", "", weatherStatus));
  }
  return card;
}

function choice(label, selected, action) {
  const button = element("button", "", label);
  button.type = "button";
  button.setAttribute("aria-pressed", selected);
  button.addEventListener("click", action);
  return button;
}

function row(label, title, detail, overdue = false) {
  const content = element("div", "", element("strong", "", title));
  if (detail) content.append(element("small", "", detail));
  return element("li", "row", element("span", overdue ? "time overdue" : "time", label), content);
}

function taskControls() {
  const demo = data.mode === "demo";
  const card = element("section", "task-capture");
  const message = element("p", "task-message", taskMessage);
  message.setAttribute("role", "status");
  if (!demo && !taskClient) {
    const form = element("form", "capture-form");
    const token = element("input", "search");
    token.type = "password";
    token.required = true;
    token.placeholder = "GitHub 访问令牌";
    token.setAttribute("aria-label", "GitHub 访问令牌");
    token.autocomplete = "off";
    const connect = element("button", "primary", "连接任务清单");
    connect.disabled = taskBusy;
    const guide = link("如何配置 ›",
      "https://github.com/" + data.task_editor.repository + "/blob/" +
      encodeURIComponent(data.task_editor.branch) + "/docs/pages.md#手机上新增和勾完成");
    form.append(token, connect, guide);
    form.addEventListener("submit", async event => {
      event.preventDefault();
      if (taskBusy || refresh.disabled || !token.value.trim()) return;
      const client = new GitHubTaskFile(data.task_editor, token.value.trim());
      token.value = "";
      connect.disabled = true;
      taskBusy = true;
      try {
        taskSnapshot = await client.read();
        taskClient = client;
        taskMessage = "GitHub 已连接";
      } catch (error) {
        taskMessage = error.message;
      } finally {
        taskBusy = false;
        render();
      }
    });
    const connection = element("details", "panel connection",
      element("summary", "", "连接 GitHub 待办"), form, message);
    connection.open = Boolean(taskMessage);
    card.append(connection);
    return card;
  }

  const form = element("form", "capture-form");
  const title = element("input", "search");
  title.type = "text";
  title.disabled = taskBusy;
  title.required = true;
  title.maxLength = 160;
  title.value = draftTitle;
  title.placeholder = "例如：提交实验报告";
  title.addEventListener("input", () => { draftTitle = title.value; draftId = ""; });
  const due = element("input", "");
  due.type = "datetime-local";
  due.step = "1";
  due.disabled = taskBusy;
  due.value = draftDue;
  due.addEventListener("input", () => { draftDue = due.value; draftId = ""; });
  const editIndex = editingTask ? taskSnapshot.tasks.indexOf(editingTask) : -1;
  const add = element("button", "primary", editingTask ? "保存" : "添加");
  add.disabled = taskBusy || Boolean(editingTask && editIndex < 0);
  const controls = element("div", "editor-actions", add);
  if (editingTask) {
    const cancel = choice("取消", false, () => {
      clearTaskDraft();
      taskMessage = "";
      render();
    });
    cancel.disabled = taskBusy;
    controls.append(cancel);
  }
  form.append(element("h2", "", editingTask ? "编辑任务" : "新增任务"),
    element("label", "editor-field", "任务名称", title),
    element("label", "editor-field", "截止时间（可选，北京时间）", due), controls);
  if (editingTask && editIndex < 0) {
    form.append(element("p", "task-message overdue", "这项任务已在别处修改。请取消后从清单重新打开。"));
  }
  form.addEventListener("submit", event => {
    event.preventDefault();
    if (!title.value.trim() || taskBusy || refresh.disabled) return;
    const fields = { title: title.value.trim(), due: due.value || null };
    if (editingTask) {
      if (editIndex < 0) return;
      const revised = taskSnapshot.tasks.map((item, offset) => offset === editIndex ? {...item, ...fields} : item);
      changeTask(revised, {action: "edit"});
      return;
    }
    draftId ||= Array.from(crypto.getRandomValues(new Uint32Array(4)),
      number => number.toString(16).padStart(8, "0")).join("");
    const entry = { id: draftId, ...fields, done: false };
    changeTask(taskSnapshot.tasks.some(task => task?.id === draftId) ? taskSnapshot.tasks
      : [entry, ...taskSnapshot.tasks], {action: "add", addedId: draftId});
  });
  if (editingTask) form.classList.add("editing");
  form.classList.add("panel");
  card.append(form, message);
  const tasks = taskSnapshot.tasks.flatMap((task, index) => {
    if (!task || typeof task.title !== "string") return [];
    const checkbox = element("input", "complete");
    checkbox.type = "checkbox";
    checkbox.checked = Boolean(task.done);
    checkbox.disabled = taskBusy || task === editingTask;
    checkbox.setAttribute("aria-label", `${task.done ? "重新打开" : "完成"} ${task.title}`);
    checkbox.addEventListener("change", () => {
      const done = checkbox.checked;
      checkbox.checked = Boolean(task.done);
      const revised = taskSnapshot.tasks.map((item, offset) => offset === index ? {...item, done} : item);
      changeTask(revised, {action: done ? "complete" : "reopen"});
    });
    const edit = element("button", "text-button", "编辑");
    edit.type = "button";
    edit.disabled = taskBusy;
    edit.setAttribute("aria-label", `编辑 ${task.title}`);
    edit.addEventListener("click", () => {
      if (taskBusy || refresh.disabled) return;
      editingTask = task;
      draftTitle = task.title;
      draftDue = localDeadline(task.due);
      draftId = taskMessage = "";
      render();
      main.querySelector(".editing .editor-field input")?.focus();
    });
    const dueDate = localDeadline(task.due);
    const clock = demo ? Date.parse(data.updated) : Date.now();
    const overdue = Boolean(!task.done && dueDate && Date.parse(dueDate + "+08:00") <= clock);
    const node = element("li", task.done ? "row tick-row done" : "row tick-row", checkbox,
      element("div", "task-details", element("strong", "", task.title),
        dueDate ? element("small", overdue ? "overdue" : "", `${overdue ? "逾期" : "截止"} ${dueDate.replace("T", " ").slice(0, 16)}`) : ""), edit);
    return [{task, node}];
  });
  const list = element("div", "panel task-list");
  if (tasks.length) {
    const search = element("input", "search");
    search.type = "search";
    search.value = taskQuery;
    search.placeholder = "搜索任务标题";
    search.setAttribute("aria-label", "搜索任务标题");
    const filters = editorFilters;
    const buttons = filters.map(([key, label]) => choice(label, key === taskFilter, () => {
      taskFilter = key;
      update();
    }));
    function update() {
      buttons.forEach((button, index) => button.setAttribute("aria-pressed", filters[index][0] === taskFilter));
      const query = taskQuery.trim().toLocaleLowerCase();
      const matches = tasks.filter(({task}) => task.title.toLocaleLowerCase().includes(query) &&
        (taskFilter === "all" || (taskFilter === "done" ? task.done
          : !task.done && (taskFilter !== "due" || task.due))));
      matches.sort((a, b) => (localDeadline(a.task.due) || "~").localeCompare(localDeadline(b.task.due) || "~"));
      list.replaceChildren();
      for (const [label, include] of [
        ["截止", task => !task.done && task.due],
        ["待办", task => !task.done && !task.due],
        ["已完成", task => task.done],
      ]) {
        const rows = matches.filter(({task}) => include(task));
        if (rows.length) list.append(element("h2", "task-group", label),
          element("ul", "rows", ...rows.map(({node}) => node)));
      }
      if (!matches.length) list.append(element("p", "empty", "没有符合条件的任务"));
    }
    search.addEventListener("input", () => { taskQuery = search.value; update(); });
    card.append(element("div", "switch", ...buttons), search);
    update();
  } else {
    list.append(element("p", "empty", "没有未完成的任务"));
  }
  card.append(list);
  if (taskClient) {
    const disconnect = element("button", "text-button", "断开 GitHub");
    disconnect.type = "button";
    disconnect.addEventListener("click", () => {
      if (taskBusy || refresh.disabled) return;
      taskClient = null;
      taskSnapshot = null;
      clearTaskDraft();
      taskMessage = "";
      render();
    });
    card.append(disconnect);
  }
  return card;
}

async function changeTask(tasks, {action, addedId}) {
  if (taskBusy || refresh.disabled) return;
  const demo = data.mode === "demo";
  taskBusy = true;
  taskMessage = "正在保存…";
  render();
  let saved = false;
  try {
    taskSnapshot = demo ? {tasks} : await taskClient.write(taskSnapshot, tasks);
    saved = true;
  } catch (error) {
    taskMessage = error.message;
    try {
      updateTaskSnapshot(await taskClient.read());
      saved = Boolean(addedId && taskSnapshot.tasks.some(task => task?.id === addedId));
    } catch {
      taskMessage += " 请手动刷新后再操作。";
    }
  } finally {
    if (saved) {
      if (action === "add" || action === "edit") clearTaskDraft();
      if (action === "add") {
        taskFilter = "open";
        taskQuery = "";
      }
      const feedback = {add: "任务已添加", edit: "修改已保存", complete: "已标为完成", reopen: "已恢复为进行中"};
      taskMessage = demo ? feedback[action] : `${feedback[action]} · 已保存到 GitHub`;
    }
    taskBusy = false;
    render();
  }
}

function openCalendarDraft(day, event) {
  if (refresh.disabled || calendarBusy) return;
  calendarMessage = calendarRun = "";
  calendarDraft = {
    action: event ? "edit" : "add",
    first_day: data.today,
    revision: data.calendar_editor.revision,
    id: event?.id,
    title: event?.name || "",
    start: event?.start || `${day.date}T09:00`,
    end: event?.end || "",
    all_day: Boolean(event?.all_day),
  };
  if (data.calendar_editor.show_locations) calendarDraft.place = event?.place || "";
  render();
  main.querySelector(".calendar-form input")?.focus();
}

function calendarForm(target) {
  const draft = calendarDraft;
  const form = element("form", "panel calendar-form");
  form.append(element("h2", "", draft.action === "add" ? "新增日程" : "编辑日程"));
  function input(key, label, type, required = false) {
    const field = element("input", "");
    field.type = type;
    field.required = required;
    field.disabled = calendarBusy;
    if (type === "datetime-local") field.step = "1";
    if (type === "checkbox") field.checked = draft[key];
    else field.value = draft[key];
    field.addEventListener("input", () => {
      draft[key] = type === "checkbox" ? field.checked : field.value;
    });
    form.append(element("label", "editor-field", label, field));
    return field;
  }
  input("title", "日程名称", "text", true).maxLength = 160;
  const allDay = input("all_day", "全天", "checkbox");
  allDay.parentElement.classList.add("calendar-all-day");
  allDay.addEventListener("change", () => {
    for (const field of ["start", "end"]) {
      if (draft[field]) draft[field] = draft.all_day ? draft[field].slice(0, 10)
        : `${draft[field]}T${field === "start" ? "09:00" : "10:00"}`;
    }
    if (draft.all_day && draft.end <= draft.start) draft.end = "";
    render();
    main.querySelector(".calendar-all-day input")?.focus();
  });
  const dateType = draft.all_day ? "date" : "datetime-local";
  input("start", draft.all_day ? "开始日期" : "开始时间（北京时间）", dateType, true);
  input("end", draft.all_day ? "结束日期（可选，填写日程最后一天的次日）" : "结束时间（可选）", dateType);
  if (target.show_locations) input("place", "地点（可选）", "text").maxLength = 160;
  const token = element("input", "");
  token.type = "password";
  token.autocomplete = "off";
  token.disabled = calendarBusy;
  const sharedToken = data.task_editor?.repository === target.repository &&
    data.task_editor.branch === target.branch ? taskClient?.token : "";
  const existing = calendarToken || sharedToken;
  token.required = !existing;
  form.append(element("label", "editor-field", existing ? "GitHub 令牌（可更换）" : "GitHub 令牌（Actions 读写）", token));
  const save = element("button", "primary", "保存");
  save.disabled = calendarBusy || draft.revision !== target.revision;
  const cancel = choice("取消", false, () => {
    calendarDraft = null;
    calendarMessage = calendarRun = "";
    render();
  });
  cancel.disabled = calendarBusy;
  if (draft.revision !== target.revision) form.append(element("p", "task-message", "日历已更新，请取消后重新打开。"));
  form.append(element("div", "editor-actions", save, cancel));
  form.addEventListener("submit", async event => {
    event.preventDefault();
    if (save.disabled || refresh.disabled || !draft.title.trim()) return;
    const auth = token.value.trim() || existing;
    if (!auth) return;
    if (draft.end && draft.end <= draft.start) {
      calendarMessage = "结束时间必须晚于开始时间。";
      render();
      return;
    }
    calendarToken = auth;
    calendarBusy = true;
    calendarRun = "";
    calendarMessage = "正在提交…";
    render();
    try {
      await publishCalendarEdit(target, calendarToken, draft, (message, runUrl) => {
        calendarMessage = message;
        calendarRun = runUrl;
        render();
      });
      savedCalendarRevision = draft.revision;
      calendarDraft = null;
      calendarMessage = "已保存并发布。";
    } catch (error) {
      calendarMessage = error.message;
    } finally {
      calendarBusy = false;
      if (!calendarDraft) await load();
      render();
    }
  });
  return form;
}

function schedule() {
  hero("日程", "今天和明天 · 北京时间");
  const switcher = element("div", "switch");
  const body = element("section", "panel");
  const controls = element("div", "calendar-controls");
  const target = data.calendar_editor;
  const waitingForPages = target && target.revision === savedCalendarRevision;
  const buttons = data.days.map((day, index) => choice(
    `${index ? "明天" : "今天"} · ${dateLabel(day.date)}`, index === selectedDay, () => {
      selectedDay = index;
      update();
    },
  ));
  function update() {
    buttons.forEach((button, index) => button.setAttribute("aria-pressed", index === selectedDay));
    const day = data.days[selectedDay];
    if (target) {
      const add = choice("新增日程", false, () => openCalendarDraft(day));
      add.className = "primary";
      add.disabled = calendarBusy || waitingForPages;
      controls.replaceChildren(add);
      if (calendarDraft) controls.append(calendarForm(target));
      if (calendarMessage) {
        const message = element("p", "task-message", waitingForPages
          ? "已保存到 GitHub，网页数据正在更新。稍后点右上角刷新。" : calendarMessage);
        message.setAttribute("role", "status");
        if (calendarRun) message.append(" ", link("查看运行记录", calendarRun));
        controls.append(message);
      }
    }
    const rows = day.events.map(event => {
      const end = event.end?.includes("T") && event.end.slice(0, 10) === day.date
        ? event.end.slice(11, 16) : event.end?.replace("T", " ").replace(/(:\d\d):\d\d$/, "$1");
      const node = row(event.time, event.name, [
        end && !event.all_day && `至 ${end}`, event.place, event.repeating && "重复日程",
      ].filter(Boolean).join(" · "));
      if (target && event.id) {
        const edit = choice(event.repeating ? "编辑这一次" : "编辑", false, () => openCalendarDraft(day, event));
        edit.className = "text-button";
        edit.disabled = calendarBusy || waitingForPages;
        edit.setAttribute("aria-label", `${edit.textContent} ${event.name}`);
        node.classList.add("calendar-row");
        node.append(edit);
      }
      return node;
    });
    body.replaceChildren(rows.length
      ? element("ul", "rows", ...rows)
      : element("p", "empty", data.schedule_status || "暂无日程"));
  }
  switcher.append(...buttons);
  main.append(switcher, controls, body);
  update();
}

function tasks() {
  hero("待办", [dateLabel(data.today), data.weekday].join(" · "));
  if (data.mode === "demo" || data.task_editor) {
    main.append(taskControls());
    return;
  }
  const search = element("input", "search");
  search.type = "search";
  search.value = taskQuery;
  search.placeholder = "搜索任务标题";
  search.setAttribute("aria-label", "搜索任务标题");
  const results = element("section", "panel");
  const filters = [["open", "全部"], ["due", "有截止"], ["todo", "待办"]];
  const buttons = filters.map(([name, label]) => choice(label, name === taskFilter, () => {
    taskFilter = name;
    update();
  }));
  function update() {
    buttons.forEach((button, index) => button.setAttribute("aria-pressed", filters[index][0] === taskFilter));
    const query = taskQuery.trim().toLocaleLowerCase();
    const matches = title => title.toLocaleLowerCase().includes(query);
    const list = [];
    if (taskFilter !== "todo") list.push(...data.deadlines.filter(entry => matches(entry.title))
      .map(entry => row(entry.label, entry.title, null, entry.overdue)));
    if (taskFilter !== "due") list.push(...data.todos.filter(matches).map(title => row("待办", title)));
    results.replaceChildren(list.length ? element("ul", "rows", ...list)
      : element("p", "empty", query ? "没有匹配的任务" : "暂无任务"));
  }
  search.addEventListener("input", () => { taskQuery = search.value; update(); });
  const filter = element("details", "task-filters", element("summary", "", "搜索与筛选"),
    search, element("div", "switch", ...buttons));
  filter.open = Boolean(taskQuery || taskFilter !== "open");
  main.append(filter, results);
  update();
}

function weather() {
  hero("天气", data.weather.location);
  showAlerts();
  main.append(currentWeather());
  const card = panel("七天预报", null);
  for (const day of data.weather.forecast) {
    const heading = element("span", "forecast-info", `${day.label} `,
      element("span", "date", dateLabel(day.date)), glyph(day.icon), day.condition || "暂无预报");
    if (day.low != null && day.high != null) heading.append(element("span", "forecast-temp", `${day.low}° / ${day.high}°`));
    card.append(element("details", "", element("summary", "", heading),
      element("p", "", `最低 ${day.low ?? "—"}° · 最高 ${day.high ?? "—"}° · 湿度 ${humidity(day.humidity)} · AQI ${day.aqi ?? "—"}`)));
  }
  main.append(card);
  if (data.weather.fetched) main.append(element("p", "source", `预报获取于 ${timeLabel(data.weather.fetched)}（北京时间）`));
  if (data.weather.providers.length) main.append(element("p", "source", "天气来源：",
    ...data.weather.providers.flatMap((provider, index) => [index ? " · " : "", link(provider.name, provider.url, "")])));
  for (const credit of data.weather.alert_credits) main.append(element("p", "source", credit));
  main.append(element("p", "source", link("打开 Kindle 图片版", "../output.png")));
}

const views = { tasks, schedule, weather };
function render() {
  const requested = location.hash.slice(1);
  const sections = {
    tasks: Boolean(data && (data.personal || data.task_editor || data.mode === "demo")),
    schedule: Boolean(data?.personal),
    weather: true,
  };
  const current = Object.hasOwn(views, requested) && sections[requested]
    ? requested : sections.tasks ? "tasks" : "weather";
  showStatus(current);
  for (const item of nav) {
    item.hidden = !sections[item.dataset.view];
    if (item.dataset.view === current) item.setAttribute("aria-current", "page");
    else item.removeAttribute("aria-current");
  }
  main.replaceChildren();
  if (data) views[current]();
  else if (issue) main.append(link("打开 Kindle 图片版", "../output.png"));
}

async function load() {
  if (refresh.disabled || taskBusy || calendarBusy) return;
  refresh.disabled = true;
  try {
    const response = await fetch(`dashboard.json?t=${Date.now()}`, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const snapshot = await response.json();
    if (snapshot.version !== 1 || !Array.isArray(snapshot.weather?.forecast)) throw new Error("Unsupported dashboard data");
    const targetKey = JSON.stringify(snapshot.task_editor || snapshot.mode);
    if (targetKey !== taskTargetKey) {
      taskTargetKey = targetKey;
      taskClient = null;
      taskSnapshot = snapshot.mode === "demo" ? {tasks: [
        ...snapshot.deadlines.map(task => ({title: task.title, due: task.due})),
        ...snapshot.todos.map(title => ({title})),
      ]} : null;
      taskMessage = "";
      clearTaskDraft();
      taskFilter = "open";
      taskQuery = "";
    } else if (taskClient) {
      try { updateTaskSnapshot(await taskClient.read()); }
      catch (error) { taskMessage = error.message; }
    }
    if (data && (data.calendar_editor?.repository !== snapshot.calendar_editor?.repository ||
                 data.calendar_editor?.branch !== snapshot.calendar_editor?.branch)) {
      calendarToken = calendarMessage = calendarRun = savedCalendarRevision = "";
      calendarDraft = null;
    }
    data = snapshot;
    issue = "";
  } catch (error) {
    issue = String(error);
  } finally {
    refresh.disabled = false;
    render();
  }
}

refresh.addEventListener("click", load);
window.addEventListener("hashchange", () => {
  render();
  window.scrollTo(0, 0);
  main.focus();
});
load();
