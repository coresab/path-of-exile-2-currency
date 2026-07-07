from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from html import unescape
from time import sleep

from poe2_currency.http import get_json, get_text
from poe2_currency.models import CashItemPrice, ItemSnapshot


@dataclass(frozen=True)
class PoeCurrencyCategory:
    parent_id: int
    parent: str
    child_id: int
    child: str


@dataclass(frozen=True)
class PoeCurrencyServer:
    server_id: int
    name: str


class PoeCurrencyAdapter:
    source_name = "poecurrency"
    page_url = "https://www.poecurrency.com/poe-2-items"
    list_url = "https://www.poecurrency.com/poe-2-items/goods-list"
    game_sku = "pathofexile2862"

    def __init__(self, server: str = "Runes of Aldur SC", pause_seconds: float = 0.1) -> None:
        self.server = server
        self.pause_seconds = pause_seconds

    def fetch_all_items(self) -> ItemSnapshot:
        html = get_text(self.page_url)
        server = self._find_server(html, self.server)
        categories = self.parse_categories(html)
        items_by_goods_no: dict[str, CashItemPrice] = {}

        for category in categories:
            for item in self.fetch_category(server, category):
                items_by_goods_no[item.goods_no] = item
            sleep(self.pause_seconds)

        return ItemSnapshot(
            source=self.source_name,
            captured_at=datetime.now(timezone.utc),
            items=tuple(items_by_goods_no.values()),
        )

    def fetch_category(self, server: PoeCurrencyServer, category: PoeCurrencyCategory, page_size: int = 40) -> list[CashItemPrice]:
        page = 1
        results: list[CashItemPrice] = []
        while True:
            payload = get_json(
                self.list_url,
                {
                    "template_type": "items",
                    "cate_id": category.child_id,
                    "server_id": server.server_id,
                    "page": page,
                    "goods_name": "",
                    "tag": "",
                    "sort": 0,
                    "game_sku": self.game_sku,
                },
            )
            data = payload.get("data", {})
            goods = data.get("goods", [])
            for raw in goods:
                results.append(self._item_from_payload(raw, server, category))
            count = int(data.get("count", len(results)))
            if page * page_size >= count or not goods:
                break
            page += 1
            sleep(self.pause_seconds)
        return results

    def parse_categories(self, html: str) -> list[PoeCurrencyCategory]:
        parent_names = {
            int(parent_id): unescape(name).strip()
            for parent_id, name in re.findall(r'data-pid="(\d+)" data-value="([^"]+)"', html)
        }
        categories: list[PoeCurrencyCategory] = []
        for parent_id, block in re.findall(
            r'<div class="goods_childCate[^"]*" data-pid="(\d+)">(.*?)(?=<div class="goods_childCate|<div class="z-goods-filter)',
            html,
            re.S,
        ):
            parent_id_int = int(parent_id)
            parent = parent_names.get(parent_id_int, str(parent_id_int))
            for child_id, child in re.findall(r'data-cid="(\d+)" data-value="([^"]+)"', block):
                if child_id == parent_id:
                    continue
                categories.append(
                    PoeCurrencyCategory(
                        parent_id=parent_id_int,
                        parent=parent,
                        child_id=int(child_id),
                        child=unescape(child).strip(),
                    )
                )
        return categories

    def _find_server(self, html: str, server_name: str) -> PoeCurrencyServer:
        for server_id, name in re.findall(r'data-serverid="(\d+)" data-value="([^"]+)"', html):
            name = unescape(name).strip()
            if name == server_name:
                return PoeCurrencyServer(server_id=int(server_id), name=name)
        raise ValueError(f"Could not find POECurrency server {server_name!r}")

    def _item_from_payload(
        self,
        raw: dict[str, object],
        server: PoeCurrencyServer,
        category: PoeCurrencyCategory,
    ) -> CashItemPrice:
        return CashItemPrice(
            source=self.source_name,
            server=server.name,
            category_id=int(raw.get("cate_id") or category.child_id),
            category=f"{category.parent} / {category.child}",
            goods_no=str(raw["goods_no"]),
            title=str(raw["title"]),
            price_usd=float(raw["price"]),
            stock=int(raw["stock"]) if raw.get("stock") not in (None, "") else None,
            image_url=str(raw["images"]) if raw.get("images") else None,
            sku=str(raw["sku"]) if raw.get("sku") else None,
        )

