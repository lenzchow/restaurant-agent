from __future__ import annotations

import json

import pytest

from restaurant_agent.domain.contracts import RestaurantSearchInput
from restaurant_agent.infrastructure.dianping_provider import DianpingBrowserProvider


class FakeHarness:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.calls: list[tuple[str, str | None]] = []

    async def run(self, script: str, *, target_url: str | None = None) -> str:
        self.calls.append((script, target_url))
        return json.dumps(self.payload, ensure_ascii=False)


@pytest.mark.asyncio
async def test_provider_limits_recommended_dishes_to_ten_and_explains_shortfall() -> None:
    harness = FakeHarness(
        {
            "restaurant": {
                "name": "Sakura Table",
                "address": "示例路88号",
                "cuisine": "Japanese",
                "price_per_person": 180,
                "recommended_dishes": ["寿司", "烤鳗鱼"],
                "recommended_dish_images": [
                    "https://img.example/sushi.jpg",
                    "https://img.example/eel.jpg",
                ],
                "recommendation_total": 2,
                "recommendation_reason": "页面只展示2道推荐菜",
                "opening_hours": "11:30-21:30",
                "rating": 4.7,
                "review_summary": "食材新鲜",
                "review_highlights": ["服务好"],
            }
        }
    )
    provider = DianpingBrowserProvider(harness)

    restaurant = await provider.get_restaurant_details(
        "https://www.dianping.com/shop/example", city="北京"
    )

    assert restaurant.recommended_dishes == ["寿司", "烤鳗鱼"]
    assert restaurant.recommended_dish_images == [
        "https://img.example/sushi.jpg",
        "https://img.example/eel.jpg",
    ]
    assert restaurant.recommendation_note == "页面只展示2道推荐菜"
    assert restaurant.rating == 4.7
    assert restaurant.source_url == "https://www.dianping.com/shop/example"


@pytest.mark.asyncio
async def test_provider_searches_filtered_restaurants_with_pagination() -> None:
    harness = FakeHarness(
        {
            "restaurants": [
                {
                    "name": "Sakura Table",
                    "address": "示例路88号",
                    "cuisine": "Japanese",
                    "price_per_person": 180,
                    "rating": 4.8,
                }
            ],
        }
    )
    provider = DianpingBrowserProvider(harness)

    restaurants = await provider.search_restaurants(
        RestaurantSearchInput(
            city="北京",
            cuisine="北京菜",
            location="朝阳区",
            sort="rating",
            page=2,
            limit=10,
        )
    )

    assert len(restaurants) == 1
    assert restaurants[0].rating == 4.8
    script, target_url = harness.calls[0]
    assert target_url == "https://www.dianping.com/beijing/ch10"
    assert "slice(0, 10)" in script


def test_search_item_parser_maps_dianping_card_fields() -> None:
    item = {
        "name": "浩海火烧云傣家菜(京广店)",
        "source_url": "https://www.dianping.com/shop/example",
        "text": """浩海火烧云傣家菜(京广店)
42276 条评价
人均 ￥103
云南菜|滇菜 | 朝阳公园/团结湖
推荐菜： 油焖鸡 黑三剁 小锅米线
""",
        "rating": 4.5,
        "recommended_dishes": ["油焖鸡", "黑三剁", "小锅米线"],
    }

    restaurant = DianpingBrowserProvider._restaurant_from_search_item(item)

    assert restaurant.name == "浩海火烧云傣家菜(京广店)"
    assert restaurant.cuisine == "云南菜|滇菜"
    assert restaurant.price_per_person == 103
    assert restaurant.rating == 4.5
    assert restaurant.recommended_dishes == ["油焖鸡", "黑三剁", "小锅米线"]


@pytest.mark.asyncio
async def test_provider_reports_missing_recommended_dish_images() -> None:
    harness = FakeHarness(
        {
            "restaurant": {
                "name": "没有图片的餐厅",
                "recommended_dishes": ["招牌菜"],
                "recommended_dish_images": [],
            }
        }
    )

    restaurant = await DianpingBrowserProvider(harness).get_restaurant_details(
        "没有图片的餐厅", city="北京"
    )

    assert restaurant.recommended_dish_images == []
    assert restaurant.recommendation_image_note == "页面未抓取到推荐菜图片。"


@pytest.mark.asyncio
async def test_provider_maps_full_review_metadata() -> None:
    harness = FakeHarness(
        {
            "restaurant": {
                "name": "评价餐厅",
                "reviews": [
                    {
                        "content": "菜品新鲜，服务很好",
                        "rating": 4.5,
                        "tags": ["服务好", "菜品新鲜"],
                        "created_at": "2026-10-14",
                    }
                ],
                "review_count": 18,
                "review_tags": ["服务好", "菜品新鲜"],
            }
        }
    )

    restaurant = await DianpingBrowserProvider(harness).get_restaurant_details(
        "评价餐厅", city="北京"
    )

    assert restaurant.review_count == 18
    assert restaurant.review_tags == ["服务好", "菜品新鲜"]
    assert restaurant.reviews[0].content == "菜品新鲜，服务很好"


@pytest.mark.asyncio
async def test_provider_marks_shell_page_as_partial_instead_of_live_complete() -> None:
    harness = FakeHarness(
        {"url": "https://www.dianping.com/shop/example", "text": "©美团网 meituan.com"}
    )

    restaurant = await DianpingBrowserProvider(harness).get_restaurant_details(
        "https://www.dianping.com/shop/example", city="北京"
    )

    assert restaurant.data_source_status == "partial"
    assert restaurant.recommendation_note is not None


def test_recommended_dishes_skip_dianping_helper_rows() -> None:
    text = """推荐菜
查看更多
网友推荐(756)
178人推荐
39人推荐
全聚德烤鸭
鸭汤泡饭
贝勒爷烤羊肉
去大众点评App查看全部756道推荐菜
"""

    assert DianpingBrowserProvider._recommended_dishes(text) == [
        "全聚德烤鸭",
        "鸭汤泡饭",
        "贝勒爷烤羊肉",
    ]


def test_search_script_selects_shop_title_links_only() -> None:
    script = DianpingBrowserProvider._search_script(
        "https://www.dianping.com/beijing/ch10", 10
    )

    assert 'a[data-click-name="shop_title_click"]' in script
    assert 'a[href*="/shop/"]' not in script


def test_detail_script_extracts_recommended_dish_image_urls() -> None:
    script = DianpingBrowserProvider._detail_script(
        "https://www.dianping.com/shop/example"
    )

    assert "recommended_dish_images" in script
    assert "currentSrc" in script


def test_search_script_resolves_city_filters_and_sort_from_page_links() -> None:
    script = DianpingBrowserProvider._search_script(
        "https://www.dianping.com/beijing/ch10", 10,
        city="杭州", cuisine="日料", location="西湖区", sort="environment", page=2,
    )

    assert "city_payload" in script
    assert '"city": "杭州"' in script
    assert '"cuisine": "日本菜"' in script
    assert '"location": "西湖区"' in script
    assert '"sort": "环境最佳"' in script
    assert '"page": 2' in script


@pytest.mark.parametrize(
    ("sort", "label"),
    [
        ("review_count", "评价最多"),
        ("environment", "环境最佳"),
        ("service", "服务最佳"),
        ("booking", "预订优先"),
    ],
)
def test_sort_aliases_are_supported(sort: str, label: str) -> None:
    assert DianpingBrowserProvider._sort_labels[sort] == label


def test_detail_text_parsers_extract_live_page_fields() -> None:
    text = """打开App
全聚德(淮海中路店)
3.9
17343条¥125/人
淮海路烤鸭
营业中11:00-14:00, 17:00-21:00
淮海中路780号栗时代大厦4F（近瑞金一路）
"""

    assert DianpingBrowserProvider._name(text) == "全聚德(淮海中路店)"
    assert DianpingBrowserProvider._cuisine(text) == "烤鸭"
    assert DianpingBrowserProvider._address(text) == "淮海中路780号栗时代大厦4F（近瑞金一路）"
    assert DianpingBrowserProvider._price_per_person(text) == 125
    assert DianpingBrowserProvider._opening_hours(text) == "11:00-14:00, 17:00-21:00"
    assert DianpingBrowserProvider._rating(text) == 3.9


def test_address_parser_ignores_meituan_footer() -> None:
    text = "©美团网 meituan.com 京ICP证070791号 京公网安备 11000002002052号"

    assert DianpingBrowserProvider._address(text) is None
