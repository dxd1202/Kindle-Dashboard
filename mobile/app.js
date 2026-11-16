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
  hero(dateLabel(data.today), [data.weekday, data.semester].filter(Boolean).join(" · "));
  showAlerts();
  main.append(currentWeather());
  if (data.personal) {
    const event = data.next_event;
    const eventCard = panel("下一条日程", link("全部日程 ›", "#schedule"));
    eventCard.append(element("p", "prominent", event ? event.name : "暂无接下来的日程"));
    if (event) eventCard.append(element("p", "", [event.day, event.time, event.place].filter(Boolean).join(" · ")));
    const dueCard = panel("最近截止", link("全部任务 ›", "#tasks"));
    const deadline = data.deadlines.find(entry => !entry.overdue) || data.deadlines[0];
    dueCard.append(element("p", "prominent", deadline ? deadline.title : "近期暂无截止"));
    if (deadline) dueCard.append(element("p", deadline.overdue ? "overdue" : "", deadline.label));
    main.append(element("div", "overview-grid", eventCard, dueCard));
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
    (data?.personal || !["schedule", "tasks"].includes(requested)) ? requested : "overview";
  for (const item of nav) {
    item.hidden = Boolean(data && !data.personal && item.dataset.view !== "overview");
    if (item.dataset.view === current) item.setAttribute("aria-current", "page");
    else item.removeAttribute("aria-current");
  }
  main.replaceChildren();
  if (data) views[current]();
  else if (issue) main.append(link("打开 Kindle 图片版", "../output.png"));
}

async function load() {
  if (refresh.disabled) return;
  refresh.disabled = true;
  try {
    const response = await fetch("dashboard.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const snapshot = await response.json();
    if (snapshot.version !== 1 || !Array.isArray(snapshot.weather?.forecast)) throw new Error("Unsupported dashboard data");
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
