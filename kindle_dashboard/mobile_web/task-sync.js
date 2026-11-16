"use strict";

class GitHubTaskFile {
  constructor(target, token) {
    const repository = target.repository.split("/").map(encodeURIComponent).join("/");
    const path = target.path.split("/").map(encodeURIComponent).join("/");
    this.url = `https://api.github.com/repos/${repository}/contents/${path}`;
    this.branch = target.branch;
    this.token = token;
  }

  async request(url, options = {}) {
    const response = await fetch(url, {
      ...options,
      cache: "no-store",
      redirect: "error",
      headers: {
        Accept: "application/vnd.github+json",
        Authorization: `Bearer ${this.token}`,
        "Content-Type": "application/json",
      },
    });
    if (response.ok) return response.json();
    const messages = {
      401: "授权已失效，请重新连接 GitHub。",
      403: "GitHub 拒绝了操作，请检查权限或稍后重试。",
      404: "找不到任务文件，请检查令牌的仓库权限。",
      409: "任务清单已被修改，请更新后重试。",
      422: "GitHub 拒绝了写入，请更新后检查任务清单。",
    };
    throw Object.assign(new Error(messages[response.status] || `GitHub 请求失败（${response.status}）`),
      { status: response.status });
  }

  async read() {
    const file = await this.request(`${this.url}?ref=${encodeURIComponent(this.branch)}`);
    if (file.encoding !== "base64" || !file.sha) throw new Error("无法读取 GitHub 的 JSON 任务文件。");
    const bytes = Uint8Array.from(atob(file.content.replace(/\s/g, "")), char => char.charCodeAt(0));
    const tasks = JSON.parse(new TextDecoder("utf-8", {fatal:true}).decode(bytes));
    if (!Array.isArray(tasks)) throw new Error("GitHub 的任务文件必须是 JSON 数组。");
    return { tasks, sha: file.sha };
  }

  async write(snapshot, tasks) {
    const bytes = new TextEncoder().encode(JSON.stringify(tasks, null, 2) + "\n");
    let binary = "";
    for (let i = 0; i < bytes.length; i += 8192) binary += String.fromCharCode(...bytes.subarray(i, i + 8192));
    const result = await this.request(this.url, {
      method: "PUT",
      body: JSON.stringify({
        message: "Update dashboard tasks from mobile", branch: this.branch,
        sha: snapshot.sha, content: btoa(binary),
      }),
    });
    return { tasks, sha: result.content.sha };
  }
}
