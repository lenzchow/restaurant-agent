# 大众点评筛选搜索设计

## 目标

将真实餐厅查询从“榜单抓取”改为大众点评餐厅搜索，支持菜系、地点、排序、页码和返回数量控制。

## 范围

- 删除真实大众点评榜单语义和 `get_ranking` 业务入口。
- `DianpingBrowserProvider` 提供 `search_restaurants`。
- 搜索参数由 `RestaurantSearchInput` 传递：城市、菜系、地点、排序、页码、返回数量。
- 优先在大众点评城市美食页中解析筛选链接，再打开生成后的筛选 URL。
- 结果只读取餐厅主卡片，不读取榜单页面。

## 请求语义

`page` 对应大众点评分页，默认第 1 页；`limit` 是 Agent 本次最多返回的餐厅数量，默认 10，最大 20。

支持的排序值：

- `smart`：智能
- `rating`：好评
- `popularity`：人气
- `taste`：口味
- `price_high`：人均最高
- `price_low`：人均最低

## 数据流

```text
ChatRequest
  -> IntentRecognizer
  -> RestaurantSearchInput
  -> DianpingBrowserProvider.search_restaurants
  -> browser-harness 打开城市美食页
  -> 根据页面筛选链接构造 URL
  -> 提取餐厅主卡片
  -> Restaurant[]
```

## 非目标

- 不抓取或维护“真实大众点评榜单”。
- 不把榜单标签作为真实搜索结果来源。
- 不持久化浏览器 Cookie、Token 或搜索结果。
