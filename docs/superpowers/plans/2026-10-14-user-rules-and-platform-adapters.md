# User Rules and Platform Adapters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将用户确认的状态化条件确认、飞书适配器、网页入口、命令行入口和多餐厅业务规则落到平台无关的 Agent 架构中。

**Architecture:** Agent 核心继续接收统一的 `ChatRequest` 并返回统一的 `ChatResponse`。新增的条件状态层只负责维护搜索条件、候选条件和确认状态；飞书、网页、命令行只负责把各自的输入转换成 `ChatRequest`，再把 `ChatResponse` 转换成平台消息。真实数据 Provider 和高德 MCP 仍由 Agent 工具调用。

**Tech Stack:** Python 3.12, FastAPI, Pydantic, OpenAI Agents SDK, pytest, pytest-asyncio。

**Spec:** `requirements_develop.md` 第十七节。

## Global Constraints

- 每次真实搜索前展示当前搜索条件并等待确认。
- 模糊条件只能生成候选值，不能静默选择唯一值。
- 新条件覆盖旧条件；“不限”清除对应条件；无法判断时追问。
- 单次默认最多处理 10 家餐厅。
- 多餐厅路线查询必须先确认查询范围。
- 不支持的路线方式直接说明不支持，不使用近似结果。
- 默认使用内存 Session。
- 不把飞书字段写进 Agent 核心。

### Task 1: 条件状态模型和搜索确认

**Files:**
- Create: `src/restaurant_agent/application/search_state.py`
- Modify: `src/restaurant_agent/application/service.py`
- Modify: `src/restaurant_agent/domain/contracts.py`
- Test: `tests/test_search_state.py`
- Test: `tests/test_agent.py`

**Interfaces:**
- `SearchConditionState.update(request: str) -> SearchConditionUpdate`
- `SearchConditionState.confirm(conversation_id: str) -> RestaurantSearchInput`
- `SearchConditionUpdate` 包含 `status`、`current_conditions`、`candidates`、`clarifying_question`。

- [ ] 为模糊预算、距离和排序条件写失败测试。
- [ ] 实现候选值生成和用户确认状态。
- [ ] 实现新条件覆盖旧条件和“不限”清除条件。
- [ ] 在真实搜索前返回条件预览。
- [ ] 验证搜索确认流程。

### Task 2: 多餐厅详情和路线范围确认

**Files:**
- Modify: `src/restaurant_agent/application/service.py`
- Modify: `src/restaurant_agent/application/agent_planning.py`
- Test: `tests/test_agent.py`
- Test: `tests/test_agent_planning.py`

**Interfaces:**
- 批量结果默认最多 10 家。
- 多餐厅路线请求必须先产生“全部餐厅 / 指定一家”的追问。
- 批量工具调用使用 `asyncio.gather`，单项失败保留错误信息。

- [ ] 为批量详情、批量路线和路线范围追问写失败测试。
- [ ] 实现批量详情查询。
- [ ] 实现路线范围确认和单项失败降级。
- [ ] 验证所有结果仍符合 `ChatResponse`。

### Task 3: 评价抓取和分层返回

**Files:**
- Modify: `src/restaurant_agent/domain/contracts.py`
- Modify: `src/restaurant_agent/infrastructure/dianping_provider.py`
- Modify: `src/restaurant_agent/application/service.py`
- Test: `tests/test_dianping_provider.py`
- Test: `tests/test_agent.py`

**Interfaces:**
- 默认返回评价总结。
- 完整评价请求返回评价正文、数量、标签和时间。
- 默认总结后固定追加：`是否需要查看抓取评价内容的完整信息？`

- [ ] 为完整评价字段写失败测试。
- [ ] 实现页面评价数据解析。
- [ ] 实现默认总结和用户追问后的完整评价返回。
- [ ] 验证没有评价时的降级说明。

### Task 4: 平台无关 API 和飞书适配器

**Files:**
- Create: `src/restaurant_agent/adapters/feishu.py`
- Modify: `src/restaurant_agent/api.py`
- Modify: `src/restaurant_agent/domain/contracts.py`
- Test: `tests/test_feishu_adapter.py`

**Interfaces:**
- `FeishuAdapter.to_chat_request(event: dict[str, object]) -> ChatRequest`
- `FeishuAdapter.to_message(response: ChatResponse) -> dict[str, object]`
- 飞书适配器不直接实现餐厅业务逻辑。

- [ ] 为飞书事件解析和响应转换写失败测试。
- [ ] 实现飞书文本消息适配。
- [ ] 实现确认、取消和条件追问消息适配。
- [ ] 增加飞书 webhook 入口配置。
- [ ] 验证飞书入口与通用 `/v1/chat` 复用同一 Agent 服务。

### Task 5: 网页和命令行入口

**Files:**
- Create: `src/restaurant_agent/web.py`
- Create: `src/restaurant_agent/cli.py`
- Create: `src/restaurant_agent/templates/chat.html`
- Test: `tests/test_web.py`
- Test: `tests/test_cli.py`

- [ ] 为网页入口和命令行入口写失败测试。
- [ ] 实现最小可用网页聊天页面。
- [ ] 实现命令行交互入口。
- [ ] 支持显示条件预览、确认和取消。
- [ ] 支持图片 URL 的页面展示。

### Task 6: 真实联调和回归验证

- [ ] 使用当前 Chrome 登录态联调大众点评定位、其他城市和商圈。
- [x] 使用 `.env` 中的高德 MCP 配置联调真实路线。✅（北京站到天安门）
- [ ] 使用 TeamRouter 执行 Responses API 端到端测试。
- [ ] 执行全量离线测试、编译检查和 `git diff --check`。
- [ ] 更新 `requirements_develop.md` 的完成状态。
