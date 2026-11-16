"use strict";

async function publishCalendarEdit(target, token, change, progress) {
  const repository = target.repository.split("/").map(encodeURIComponent).join("/");
  const actions = `https://api.github.com/repos/${repository}/actions`;
  const headers = {
    Accept: "application/vnd.github+json",
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
    "X-GitHub-Api-Version": "2026-03-10",
  };
  async function request(url, options) {
    const response = await fetch(url, {cache: "no-store", redirect: "error", headers, ...options});
    if ([401, 403, 404].includes(response.status)) {
      throw new Error("无法访问日程工作流，请检查令牌和此仓库的 Actions 读写权限。");
    }
    if (!response.ok) throw new Error(`GitHub 请求失败（${response.status}）。`);
    return response.status === 204 ? null : response.json();
  }
  const dispatch = await request(`${actions}/workflows/main.yml/dispatches`, {
    method: "POST",
    body: JSON.stringify({
      ref: target.branch,
      inputs: {calendar_change: JSON.stringify(change)},
    }),
  });
  const id = dispatch?.workflow_run_id;
  if (!Number.isSafeInteger(id)) {
    throw new Error("日程请求已提交。请先到 GitHub Actions 查看结果，再决定是否重试。");
  }
  const runUrl = `https://github.com/${repository}/actions/runs/${id}`;
  progress("已提交，正在等待 GitHub 保存和发布…", runUrl);
  for (let attempt = 0; attempt < 48; attempt++) {
    await new Promise(resolve => setTimeout(resolve, 5000));
    const run = await request(`${actions}/runs/${id}`);
    if (run.status === "completed") {
      if (run.conclusion === "success") return;
      throw new Error("工作流未成功完成。请先查看运行记录，确认改动是否已写入。");
    }
  }
  throw new Error("工作流仍在运行，请查看运行记录后再操作。");
}
