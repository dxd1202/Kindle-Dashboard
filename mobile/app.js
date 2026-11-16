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
let taskFilter = "all";
let taskQuery = "";
let taskClient = null;
let taskSnapshot = null;
let taskTargetKey = "";
let taskBusy = false;
let taskMessage = "";
let draftTitle = "";
let draftDue = "";
let draftId = "";

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

function showStatus() {
  if (issue) {
    const previous = data ? ` · 保留 ${dateLabel(data.today)} ${timeLabel(data.updated)} 的数据` : "";
    status.textContent = `更新失败，点右上角重试${previous}`;
  } else if (data) {
    const stamp = `${dateLabel(data.today)} ${timeLabel(data.updated)}`;
    const stale = Date.now() - Date.parse(data.updated) > 150 * 60_000;
    status.textContent = data.mode === "demo" ? "示例数据" : `${stale ? "数据可能已过期" : "看板更新"} · ${stamp}（北京时间）`;
  }
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
  const card = panel(`天气 · ${data.weather.location}`, link("七天预报 ›", "#weather"), "weather");
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

function overview() {
  if (data.mode === "demo" || data.task_editor) {
    hero("随手记", [dateLabel(data.today), data.weekday, data.semester].filter(Boolean).join(" · "));
    main.append(taskControls());
  } else {
    hero(dateLabel(data.today), [data.weekday, data.semester].filter(Boolean).join(" · "));
  }
  showAlerts();
  main.append(currentWeather());
  if (data.personal) {
    const event = data.next_event;
    const eventCard = panel("下一条日程", link("全部日程 ›", "#schedule"));
    eventCard.append(element("p", "prominent", event ? event.name : "暂无接下来的日程"));
    if (event) eventCard.append(element("p", "", [event.day, event.time, event.place].filter(Boolean).join(" · ")));
    const dueCard = panel("最近截止", link("截止与待办 ›", "#tasks"));
    const deadline = data.deadlines.find(entry => !entry.overdue) || data.deadlines[0];
    dueCard.append(element("p", "prominent", deadline ? deadline.title : "近期暂无截止"));
    if (deadline) dueCard.append(element("p", deadline.overdue ? "overdue" : "", deadline.label));
    main.append(data.mode === "demo" || data.task_editor ? eventCard
      : element("div", "overview-grid", eventCard, dueCard));
  }
  main.append(element("p", "source", link("打开 Kindle 图片版", "../output.png")));
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

function taskControls(full = false) {
  const demo = data.mode === "demo";
  const card = panel("待办清单", taskClient
    ? choice("断开", false, () => {
      if (taskBusy || refresh.disabled) return;
      taskClient = null;
      taskSnapshot = null;
      taskMessage = "";
      render();
    }) : null, "task-capture");
  const message = element("p", "task-message", taskMessage || (demo
    ? "示例操作仅在当前页面生效" : "保存后会在下一次 Kindle 更新时同步"));
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
        taskMessage = "已连接，修改将写入 GitHub 任务清单";
      } catch (error) {
        taskMessage = error.message;
      } finally {
        taskBusy = false;
        render();
      }
    });
    card.append(form, message);
    return card;
  }

  const form = element("form", "capture-form");
  const title = element("input", "search");
  title.type = "text";
  title.disabled = taskBusy;
  title.required = true;
  title.maxLength = 160;
  title.value = draftTitle;
  title.placeholder = "记一件要做的事…";
  title.setAttribute("aria-label", "新待办标题");
  title.addEventListener("input", () => { draftTitle = title.value; draftId = ""; });
  const due = element("input", "");
  due.type = "datetime-local";
  due.disabled = taskBusy;
  due.value = draftDue;
  due.setAttribute("aria-label", "截止时间（北京时间）");
  due.addEventListener("input", () => { draftDue = due.value; draftId = ""; });
  const add = element("button", "primary", "添加");
  add.disabled = taskBusy;
  const options = element("details", "capture-options",
    element("summary", "", "加个截止时间"), element("label", "", "北京时间 ", due));
  options.open = Boolean(draftDue);
  form.append(element("div", "capture-line", title, add), options);
  form.addEventListener("submit", event => {
    event.preventDefault();
    if (!title.value.trim() || taskBusy || refresh.disabled) return;
    draftId ||= Array.from(crypto.getRandomValues(new Uint32Array(4)),
      number => number.toString(16).padStart(8, "0")).join("");
    const entry = { id: draftId, title: title.value.trim(), due: due.value || null, done: false };
    changeTask(taskSnapshot.tasks.some(task => task?.id === draftId) ? taskSnapshot.tasks
      : [entry, ...taskSnapshot.tasks], draftId);
  });
  card.append(form, message);
  const active = taskSnapshot.tasks.flatMap((task, index) => {
    if (!task || task.done || typeof task.title !== "string") return [];
    const button = element("button", "complete", "✓");
    button.type = "button";
    button.disabled = taskBusy;
    button.setAttribute("aria-label", `完成 ${task.title}`);
    button.addEventListener("click", () => {
      const revised = taskSnapshot.tasks.map((item, offset) => offset === index ? {...item, done: true} : item);
      changeTask(revised);
    });
    const node = element("li", "row tick-row", button,
      element("div", "", element("strong", "", task.title),
        typeof task.due === "string" && task.due ? element("small", "", task.due.replace("T", " ").slice(0, 16)) : ""));
    return [{task, node}];
  });
  const list = element("div", "");
  if (full) {
    const search = element("input", "search");
    search.type = "search";
    search.value = taskQuery;
    search.placeholder = "搜索任务标题";
    search.setAttribute("aria-label", "搜索任务标题");
    const filters = [["all", "全部"], ["due", "有截止"], ["todo", "待办"]];
    const buttons = filters.map(([key, label]) => choice(label, key === taskFilter, () => {
      taskFilter = key;
      update();
    }));
    function update() {
      buttons.forEach((button, index) => button.setAttribute("aria-pressed", filters[index][0] === taskFilter));
      const query = taskQuery.trim().toLocaleLowerCase();
      const matches = active.filter(({task}) => task.title.toLocaleLowerCase().includes(query) &&
        (taskFilter === "all" || Boolean(task.due) === (taskFilter === "due")));
      list.replaceChildren(matches.length ? element("ul", "rows", ...matches.map(({node}) => node))
        : element("p", "empty", "没有匹配的未完成任务"));
    }
    search.addEventListener("input", () => { taskQuery = search.value; update(); });
    card.append(search, element("div", "switch", ...buttons));
    update();
  } else {
    list.append(active.length ? element("ul", "rows", ...active.slice(0, 5).map(({node}) => node))
      : element("p", "empty", "没有未完成的任务"));
    if (active.length > 5) list.append(link(`查看全部 ${active.length} 项 ›`, "#tasks"));
  }
  card.append(list);
  return card;
}

async function changeTask(tasks, addedId) {
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
      taskSnapshot = await taskClient.read();
      saved = Boolean(addedId && taskSnapshot.tasks.some(task => task?.id === addedId));
    } catch {
      taskMessage += " 请手动刷新后再操作。";
    }
  } finally {
    if (saved) {
      if (addedId) draftTitle = draftDue = draftId = "";
      taskMessage = demo ? "已更新示例清单" : "已保存到 GitHub，下次出图时同步到 Kindle";
    }
    taskBusy = false;
    render();
  }
}

function schedule() {
  hero("日程", "今天和明天 · 北京时间");
  const switcher = element("div", "switch");
  const body = element("section", "panel");
  const buttons = data.days.map((day, index) => choice(
    `${index ? "明天" : "今天"} · ${dateLabel(day.date)}`, index === selectedDay, () => {
      selectedDay = index;
      update();
    },
  ));
  function update() {
    buttons.forEach((button, index) => button.setAttribute("aria-pressed", index === selectedDay));
    const day = data.days[selectedDay];
    body.replaceChildren(day.events.length
      ? element("ul", "rows", ...day.events.map(event => row(event.time, event.name,
        [event.end && `至 ${event.end}`, event.place].filter(Boolean).join(" · "))))
      : element("p", "empty", data.schedule_status || "暂无日程"));
  }
  switcher.append(...buttons);
  main.append(switcher, body);
  update();
}

function tasks() {
  if (data.mode === "demo" || data.task_editor) {
    hero("任务", "新增和标完成");
    main.append(taskControls(true));
    return;
  }
  hero("任务", "逾期、七天内的截止与无截止待办");
  const search = element("input", "search");
  search.type = "search";
  search.value = taskQuery;
  search.placeholder = "搜索任务标题";
  search.setAttribute("aria-label", "搜索任务标题");
  const results = element("section", "panel");
  const filters = [["all", "全部"], ["due", "有截止"], ["todo", "待办"]];
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
  main.append(search, element("div", "switch", ...buttons), results);
  update();
}

function weather() {
  hero("七天天气", data.weather.location);
  showAlerts();
  const card = element("section", "panel");
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
  main.append(link("‹ 返回总览", "#overview"));
}

const views = { overview, schedule, tasks, weather };
function render() {
  const requested = location.hash.slice(1);
  const current = Object.hasOwn(views, requested) &&
    ((requested === "tasks" && data?.task_editor) || data?.personal ||
      !["schedule", "tasks"].includes(requested)) ? requested : "overview";
  for (const item of nav) {
    item.hidden = Boolean(data && !data.personal && item.dataset.view !== "overview" &&
      !(item.dataset.view === "tasks" && data.task_editor));
    if (item.dataset.view === current) item.setAttribute("aria-current", "page");
    else item.removeAttribute("aria-current");
  }
  main.replaceChildren();
  if (data) views[current]();
  else if (issue) main.append(link("打开 Kindle 图片版", "../output.png"));
}

async function load() {
  if (refresh.disabled || taskBusy) return;
  refresh.disabled = true;
  try {
    const response = await fetch("dashboard.json", { cache: "no-store" });
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
      draftTitle = draftDue = draftId = "";
    } else if (taskClient) {
      try { taskSnapshot = await taskClient.read(); }
      catch (error) { taskMessage = error.message; }
    }
    data = snapshot;
    issue = "";
  } catch (error) {
    issue = String(error);
  } finally {
    refresh.disabled = false;
    showStatus();
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
