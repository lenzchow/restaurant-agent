from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote, urlsplit

from restaurant_agent.domain.contracts import Restaurant, RestaurantSearchInput
from restaurant_agent.infrastructure.browser_harness import (
    SubprocessBrowserHarness,
    validate_dianping_url,
)


class DianpingBrowserProvider:
    """Extracts typed restaurant data from a user-authorized Dianping browser session."""

    _city_slugs = {"北京": "beijing", "上海": "shanghai", "广州": "guangzhou", "深圳": "shenzhen"}
    _sort_labels = {
        "smart": "智能",
        "rating": "好评",
        "popularity": "人气",
        "taste": "口味",
        "review_count": "评价最多",
        "reviews": "评价最多",
        "environment": "环境最佳",
        "service": "服务最佳",
        "booking": "预订优先",
        "reservation": "预订优先",
        "price_high": "人均最高",
        "price_low": "人均最低",
    }

    def __init__(self, harness: Any | None = None) -> None:
        self.harness = harness or SubprocessBrowserHarness()

    async def get_restaurant_details(
        self, url_or_name: str, *, city: str | None = None
    ) -> Restaurant:
        target_url = self._target_url(url_or_name, city)
        output = await self.harness.run(
            self._detail_script(target_url), target_url=target_url
        )
        payload = self._decode(output)
        raw = payload.get("text", "")
        data = dict(payload.get("restaurant") or {})
        structured = self._structured_restaurant(payload.get("jsonld"))
        for key, value in structured.items():
            data.setdefault(key, value)
        dishes = list(data.get("recommended_dishes") or self._recommended_dishes(raw))[:10]
        note = data.get("recommendation_note") or data.get("recommendation_reason")
        if len(dishes) < 10 and not note:
            note = f"大众点评页面当前只抓到{len(dishes)}道推荐菜，少于10道。"
        return Restaurant(
            name=str(data.get("name") or self._name(raw) or url_or_name),
            cuisine=str(data.get("cuisine") or self._cuisine(raw) or "未知"),
            address=str(data.get("address") or self._address(raw) or "未识别到地址"),
            price_per_person=float(data.get("price_per_person") or self._price_per_person(raw) or 0),
            distance_km=float(data.get("distance_km") or 0),
            recommended_dishes=dishes,
            recommendation_note=note,
            opening_hours=data.get("opening_hours") or self._opening_hours(raw),
            rating=self._float_or_none(data.get("rating")) or self._rating(raw),
            review_summary=data.get("review_summary") or self._review_summary(raw),
            review_highlights=list(data.get("review_highlights") or []),
            source_url=str(payload.get("url") or target_url),
            source_fetched_at=self._now(),
        )

    async def search_restaurants(self, request: RestaurantSearchInput) -> list[Restaurant]:
        target_url = self._search_start_url(request)
        output = await self.harness.run(
            self._search_script(
                target_url,
                request.limit,
                city=request.city,
                cuisine=request.cuisine,
                location=request.location,
                sort=request.sort,
                page=request.page,
            ),
            target_url=target_url,
        )
        payload = self._decode(output)
        return [
            self._restaurant_from_search_item(item)
            for item in list(payload.get("restaurants") or [])[: request.limit]
        ]

    @staticmethod
    def _target_url(url_or_name: str, city: str | None) -> str:
        parsed = urlsplit(url_or_name)
        if parsed.scheme in {"http", "https"}:
            validate_dianping_url(url_or_name)
            return url_or_name
        keyword = quote(" ".join(item for item in (city, url_or_name) if item))
        return f"https://www.dianping.com/search/keyword/1/0_{keyword}"

    @classmethod
    def _search_start_url(cls, request: RestaurantSearchInput) -> str:
        if request.city in cls._city_slugs:
            return f"https://www.dianping.com/{cls._city_slugs[request.city]}/ch10"
        return "https://www.dianping.com/citylist"

    @staticmethod
    def _detail_script(url: str) -> str:
        return f'''from json import dumps
new_tab({url!r})
wait_for_load()
result = js("""(() => {{
  const text = document.body.innerText || "";
  const jsonld = [...document.querySelectorAll('script[type="application/ld+json"]')]
    .map(node => node.textContent || "");
  return JSON.stringify({{url: location.href, text, jsonld}});
}})()""")
print(result)
'''

    @staticmethod
    def _search_script(
        url: str,
        limit: int,
        *,
        city: str | None = None,
        cuisine: str | None = None,
        location: str | None = None,
        sort: str = "smart",
        page: int = 1,
    ) -> str:
        filters = json.dumps(
            {
                "city": city,
                "cuisine": {"日料": "日本菜"}.get(cuisine or "", cuisine),
                "location": location,
                "sort": DianpingBrowserProvider._sort_labels.get(sort),
                "page": page,
            },
            ensure_ascii=False,
        )
        return f'''import json

new_tab({url!r})
wait_for_load()
filters = {filters}
city_payload = js("""(() => {{
  const label = {filters}.city;
  const node = label ? [...document.querySelectorAll('a')]
    .find(item => (item.textContent || '').trim() === label) : null;
  return JSON.stringify({{href: node?.href || location.href}});
}})()""")
city_href = json.loads(city_payload).get("href")
city_base = city_href.split("/ch10", 1)[0] + "/ch10"
new_tab(city_base)
wait_for_load()
filter_payload = js("""(() => {{
  const filters = {filters};
  const find = (label) => {{
    if (!label || label === '智能') return null;
    const node = [...document.querySelectorAll('a')]
      .find(item => (item.textContent || '').trim() === label);
    return node?.href || null;
  }};
  return JSON.stringify({{cuisine: find(filters.cuisine), location: find(filters.location), sort: find(filters.sort)}});
}})()""")
filter_links = json.loads(filter_payload)
parts = []
for href in filter_links.values():
    if href and "/ch10" in href:
        parts.append(
            href.split("/ch10", 1)[1]
            .split("?", 1)[0]
            .split("#", 1)[0]
            .lstrip("/")
        )
if filters["page"] > 1:
    parts.append("p" + str(filters["page"]))
target = city_base + (("/" + "".join(parts)) if parts else "")
new_tab(target)
wait_for_load()
result = js("""(() => {{
  const links = [...document.querySelectorAll('a[data-click-name="shop_title_click"]')]
    .slice(0, {limit})
    .map(node => {{
      const card = node.closest('li') || node.closest('.txt');
      const star = card?.querySelector('.star_icon .star')?.className.match(/star_(\\d+)/);
      return {{
        name: (node.innerText || '').trim(),
        source_url: node.href,
        text: (card?.innerText || node.innerText || '').trim(),
        rating: star ? Number(star[1]) / 10 : null,
        recommended_dishes: [...(card?.querySelectorAll('.recommend-click') || [])]
          .map(item => (item.innerText || '').trim()).filter(Boolean)
      }};
    }})
    .filter(item => item.name);
  return JSON.stringify({{url: location.href, restaurants: links}});
}})()""")
print(result)
'''

    @classmethod
    def _restaurant_from_search_item(cls, item: dict[str, Any]) -> Restaurant:
        text = str(item.get("text") or "")
        category_line = next(
            (
                line.strip()
                for line in text.splitlines()
                if "|" in line
                and line.replace("|", "").strip()
                and "推荐菜" not in line
            ),
            "",
        )
        category_parts = [part.strip() for part in category_line.split("|")]
        category = "|".join(category_parts[:-1]) if len(category_parts) > 1 else ""
        location = category_parts[-1] if category_parts else ""
        return Restaurant(
            name=str(item.get("name") or "未命名餐厅"),
            cuisine=category.strip() or "未知",
            address=location.strip() or "未识别到商圈",
            price_per_person=cls._price_per_person(text) or 0,
            distance_km=0,
            recommended_dishes=list(item.get("recommended_dishes") or []),
            rating=cls._float_or_none(item.get("rating")),
            review_summary=cls._review_summary(text),
            source_url=str(item.get("source_url") or ""),
            source_fetched_at=cls._now(),
        )

    @staticmethod
    def _decode(output: str) -> dict[str, Any]:
        for line in reversed(output.splitlines()):
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                return value
        raise ValueError("browser-harness did not return a JSON object")

    @staticmethod
    def _structured_restaurant(jsonld: Any) -> dict[str, Any]:
        if not jsonld:
            return {}
        for item in jsonld if isinstance(jsonld, list) else [jsonld]:
            try:
                value = json.loads(item) if isinstance(item, str) else item
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict) and value.get("@type") in {"Restaurant", "FoodEstablishment"}:
                rating = value.get("aggregateRating", {}).get("ratingValue")
                address = value.get("address", {})
                return {
                    "name": value.get("name"),
                    "address": address.get("streetAddress") if isinstance(address, dict) else address,
                    "opening_hours": value.get("openingHours"),
                    "rating": rating,
                }
        return {}

    @staticmethod
    def _recommended_dishes(text: str) -> list[str]:
        lines = [line.strip(" ·•-：:") for line in text.splitlines() if line.strip()]
        for index, line in enumerate(lines):
            if "推荐菜" in line:
                dishes: list[str] = []
                for candidate in lines[index + 1 :]:
                    if candidate.startswith("去大众点评App"):
                        break
                    if candidate in {"查看更多"}:
                        continue
                    if candidate.startswith("网友推荐") or re.fullmatch(r"\d+人推荐", candidate):
                        continue
                    dishes.append(candidate)
                    if len(dishes) == 10:
                        break
                return dishes
        return []

    @staticmethod
    def _name(text: str) -> str | None:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for index, line in enumerate(lines[:-1]):
            if line == "打开App":
                return lines[index + 1]
        return None

    @staticmethod
    def _cuisine(text: str) -> str | None:
        for line in text.splitlines():
            value = line.strip()
            candidate = value.split("路")[-1]
            if any(term in candidate for term in ("菜", "烤鸭", "火锅", "烧烤")):
                return candidate
        return None

    @staticmethod
    def _address(text: str) -> str | None:
        for line in text.splitlines():
            value = line.strip()
            if re.search(r"\d+号", value) and len(value) >= 6:
                return value
        return None

    @staticmethod
    def _price_per_person(text: str) -> float | None:
        match = re.search(r"(?:人均\s*)?[¥￥]\s*([\d.]+)(?:\s*/人)?", text)
        return float(match.group(1)) if match else None

    @staticmethod
    def _opening_hours(text: str) -> str | None:
        match = re.search(
            r"(?:营业时间|营业中?)\s*[:：]?\s*([0-9]{1,2}:[0-9]{2}\s*[-至]\s*[0-9]{1,2}:[0-9]{2}(?:\s*,\s*[0-9]{1,2}:[0-9]{2}\s*[-至]\s*[0-9]{1,2}:[0-9]{2})?)",
            text,
        )
        return match.group(1) if match else None

    @staticmethod
    def _rating(text: str) -> float | None:
        match = re.search(r"(?:评分|口碑|口味)\s*[:：]?\s*([0-5](?:\.\d+)?)", text)
        if not match:
            match = re.search(r"(?:^|\n)([0-5](?:\.\d+)?)\n\d+条", text)
        return float(match.group(1)) if match else None

    @staticmethod
    def _review_summary(text: str) -> str | None:
        for line in text.splitlines():
            if any(term in line for term in ("好评", "评价", "口碑")) and len(line.strip()) > 4:
                return line.strip()[:200]
        return None

    @staticmethod
    def _float_or_none(value: Any) -> float | None:
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
