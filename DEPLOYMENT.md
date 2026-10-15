# 部署与联调说明

## 启动

```bash
uv sync
uv run uvicorn restaurant_agent.api:app --host 0.0.0.0 --port 8000
```

生产环境应在反向代理后提供 HTTPS，并把飞书回调指向：

```text
https://<public-host>/webhooks/feishu
```

健康检查：`GET /health`。

## 必要配置

复制 `.env.example` 为 `.env`，再填写模型、高德 MCP、Browser Harness 和飞书应用配置。`.env`、浏览器 Cookie、API Key 不得提交到 Git，也不应写入日志。

`AGENT_SESSION_DB_PATH=:memory:` 适合单进程开发；多进程部署时改为同一台机器可访问的 SQLite 文件路径。当前未实现 Redis 等跨机器 Session。

## 联调顺序

1. 先访问 `/health`。
2. 用 `/chat` 验证平台无关 Agent 入口。
3. 使用已登录 Chrome 验证大众点评搜索页。
4. 使用 `.env` 中的高德配置验证地点和路线。
5. 配置飞书事件订阅并验证 `/webhooks/feishu` Challenge。

如果外部服务不可用，Agent 会返回用户可读的降级提示；不会用样例数据伪装成实时结果。
