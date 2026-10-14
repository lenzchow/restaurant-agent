# 大众点评筛选搜索 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将大众点评真实数据入口改为支持菜系、地点、排序、页码和返回数量的餐厅筛选搜索。

**Architecture:** 复用现有平台无关 Agent 和确认流程，使用 `RestaurantSearchInput` 传递筛选条件。Dianping Provider 先读取城市页上的实际筛选链接，再访问生成 URL 并解析餐厅卡片；Sample Provider 保留给离线测试。

**Tech Stack:** Python 3.12, FastAPI, Pydantic, OpenAI Agents SDK, browser-harness, pytest。

**Spec:** `docs/superpowers/specs/2026-10-14-dianping-filter-search-design.md`

## Global Constraints

- 不实现真实大众点评榜单抓取。
- 浏览器访问仅允许大众点评域名。
- 不保存 Cookie、Token 或用户浏览器凭证。
- 默认真实餐厅 Provider 为 `dianping`。
- 新行为必须先有失败测试，再写生产代码。

### Task 1: 搜索请求契约

**Files:**
- Modify: `src/restaurant_agent/domain/contracts.py`
- Test: `tests/test_contracts.py`

- [x] 增加 `city`、`sort`、`page` 字段，并验证页码和数量范围。
- [x] 运行契约测试确认新字段当前失败。
- [x] 实现字段并运行契约测试。

### Task 2: Dianping 搜索 Provider

**Files:**
- Modify: `src/restaurant_agent/infrastructure/dianping_provider.py`
- Test: `tests/test_dianping_provider.py`

- [x] 增加 `search_restaurants` 测试，确认请求带筛选、页码和 limit。
- [x] 增加搜索卡片解析测试。
- [x] 实现筛选 URL 生成、页面链接解析和餐厅卡片转换。
- [x] 删除榜单 Provider 方法及其测试。

### Task 3: Agent 和默认配置

**Files:**
- Modify: `src/restaurant_agent/application/service.py`
- Modify: `src/restaurant_agent/api.py`
- Modify: `src/restaurant_agent/config/settings.py`
- Modify: `.env.example`
- Test: `tests/test_agent.py`

- [x] 让 `search_restaurants` 在 Dianping Provider 存在时调用真实搜索。
- [x] 移除 `get_ranking` Agent 工具。
- [x] 默认 `RESTAURANT_PROVIDER=dianping`。
- [x] 运行 Agent 测试。

### Task 4: 文档与完整验证

**Files:**
- Modify: `README.md`
- Modify: `AGENT_IMPLEMENTATION_FLOW.md`

- [x] 删除榜单抓取说明，补充筛选搜索参数。
- [x] 运行全量测试、编译检查和 `git diff --check`。
- [x] 用真实大众点评页面验证菜系、地点、排序、页码和 limit。

### Task 5: 动态城市筛选与路线组合联调

- [x] 从大众点评城市页动态解析城市、菜系、商圈/行政区和排序链接，不依赖北京固定编码。
- [x] 支持评价最多、环境最佳、服务最佳、预订优先等“其他排序”。
- [x] 用杭州/西湖区验证非北京城市和商圈路径。
- [x] 用真实大众点评结果批量调用高德 MCP，写入驾车、打车、公交和地铁字段。
