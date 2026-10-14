# 飞书接入说明

当前 Agent 核心不依赖飞书。飞书只通过 `/webhooks/feishu` 适配器接入，明天可以按下面步骤联调。

## 1. 本地配置

复制 `.env.example` 为 `.env`，填写：

```dotenv
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_API_BASE_URL=https://open.feishu.cn/open-apis
```

同时保留 Agent 所需的 `OPENAI_*`、高德 MCP 和 `BROWSER_HARNESS_EXECUTABLE` 配置。不要把 `.env` 提交到 Git。

## 2. 启动服务

```bash
uv sync
uv run uvicorn restaurant_agent.api:app --host 0.0.0.0 --port 8000
```

飞书事件订阅地址必须是飞书能够访问的 HTTPS 地址：

```text
https://你的公网域名/webhooks/feishu
```

本机 `127.0.0.1` 不能直接作为飞书回调地址。开发阶段可以使用已有的 HTTPS 隧道或部署到一台有公网 HTTPS 的服务器。

## 3. 飞书后台

在应用后台完成以下配置：

1. 开启机器人能力。
2. 配置事件订阅，订阅 `im.message.receive_v1`。
3. 给应用开通接收消息和回复消息所需的权限。
4. 将事件订阅 URL 设置为上面的 `/webhooks/feishu`。
5. 完成飞书的 URL 验证；服务会返回 `challenge`。
6. 将机器人加入测试群，发送普通文本消息。

服务收到文本后会转换为统一的 `ChatRequest`，调用 Agent，再通过飞书 Open API 回复文本。需要打开大众点评时，第一次会先回复确认消息；用户回复“确认”后才会继续浏览器操作。

## 4. 快速检查

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/chat
```

`/chat` 是本地网页入口；`/v1/chat` 是平台无关 API；`/webhooks/feishu` 是飞书回调入口。
