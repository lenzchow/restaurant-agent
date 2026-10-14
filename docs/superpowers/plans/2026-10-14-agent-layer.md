# Agent Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完善餐厅 Agent 的参数提取、工具路由、多意图工作流、Guardrails 和多轮状态，并用离线测试与可选的真实 Responses API 测试验证执行上下文。

**Architecture:** 在现有意图识别器和 Agents SDK Runner 之间增加轻量规划层。规划层输出搜索请求、路线端点和有序动作，Runner 继续负责实际工具调用与结构化回答。

**Tech Stack:** Python 3.12, Pydantic, FastAPI, OpenAI Agents SDK, pytest, pytest-asyncio。

**Spec:** `docs/superpowers/specs/2026-10-14-agent-layer-design.md`

## Global Constraints

- 不把大众点评、高德字段写进 Agent 规划层。
- 不保存 API Key、Cookie 或浏览器凭证。
- 生产代码必须先有失败测试，再实现。
- 当前使用 Agents SDK `SQLiteSession`，默认内存模式，不引入额外数据库依赖。

### Task 1: Agent 参数提取

**Files:**
- Create: `src/restaurant_agent/application/agent_planning.py`
- Test: `tests/test_agent_planning.py`

- [x] 写入自然语言到 `RestaurantSearchInput` 的失败测试。
- [x] 验证失败原因是规划模块不存在。
- [x] 实现城市、地点、菜系、预算、人数、距离、页码、数量、排序和路线端点提取。
- [x] 运行规划测试确认通过。

### Task 2: 工具路由和多意图编排

**Files:**
- Modify: `src/restaurant_agent/application/agent_planning.py`
- Modify: `src/restaurant_agent/application/service.py`
- Test: `tests/test_agent_planning.py`
- Test: `tests/test_agent.py`

- [x] 测试餐厅、推荐菜和路线组合生成有序动作。
- [x] 实现 `ToolRouter`。
- [x] 在 Service 调用 Runner 前生成 `agent_plan`。
- [x] 验证 Runner 收到搜索参数和动作列表。

### Task 3: Agents SDK Session

**Files:**
- Modify: `src/restaurant_agent/application/service.py`
- Test: `tests/test_agent.py`

- [x] 测试同一 `conversation_id` 复用 Agents SDK Session。
- [x] 使用 `SQLiteSession` 管理 Agent 对话历史。
- [x] 保持业务状态最小化，不新增自定义状态图。

### Task 4: Guardrails 与端到端 Agent 层验证

**Files:**
- Modify: `README.md`
- Modify: `AGENT_IMPLEMENTATION_FLOW.md`
- Test: `tests/test_agent.py`

- [x] 增加真实 Responses API 联调测试，默认跳过，不在离线测试中消耗 API。
- [x] 验证离线 Runner 收到结构化规划上下文。
- [x] 增加 Agents SDK 输入/输出 Guardrails，并测试路线端点和空响应拦截。
- [x] 运行全量离线测试、编译检查和 `git diff --check`。
- [ ] 当前环境真实联调仍受 `api.teamrouter.com` 连接失败影响，需要网络/代理或供应商端点恢复后重跑。
