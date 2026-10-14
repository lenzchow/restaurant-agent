# Agent 层设计

## 目标

在数据源和平台适配器之上增加一个独立的 Agent 规划层，负责参数提取、工具路由和多意图编排；对话历史交给 Agents SDK Session 管理。业务 Provider 只提供工具能力，不负责理解用户语言。

## 架构

```text
ChatRequest
  -> IntentRecognizer
  -> AgentParameterExtractor
  -> Agents SDK Session
  -> ToolRouter
  -> Agents SDK + Responses runtime
  -> ChatResponse
```

规划层输出结构化 `RestaurantSearchInput`、路线端点和有序 `AgentAction` 列表。Agents SDK 接收这些内容作为执行上下文，继续调用具体搜索、详情和路线工具。

## 组件

- `AgentParameterExtractor`：从当前消息提取城市、地点、菜系、预算、距离、人数、页码、返回数量、排序和路线端点。
- `SQLiteSession`：按 `conversation_id` 保存当前 Agent 的对话历史；当前默认使用进程内存，部署时可配置持久化路径。
- `ToolRouter`：根据一个或多个 `IntentType` 生成有序工具动作。
- `RestaurantAgentService`：在调用 Runner 前构造 `agent_plan`，并保留 Agents SDK 的工具调用和结构化输出能力。

## 约束

- 规划层不读取大众点评或高德的供应商字段。
- 外部数据失败不能被转换成虚构结果。
- 缺失路线端点和冲突条件继续由意图层负责追问。
- 当前只保存 Agent 对话历史，不建立复杂业务状态图；需要持久化时通过 Agents SDK Session 配置存储路径。

## 验证

- 参数提取单元测试。
- 多意图到有序工具动作的路由测试。
- Agents SDK Session 复用测试。
- Agent Runner 输入包含结构化规划上下文的测试。
- 全量离线测试和真实 Agent 请求单独联调。
