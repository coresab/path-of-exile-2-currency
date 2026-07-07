from __future__ import annotations

from datetime import datetime, timezone
from time import sleep
from urllib.parse import quote

from poe2_currency.http import get_json
from poe2_currency.models import ItemSnapshot, ScoutItemPrice


class Poe2ScoutAdapter:
    source_name = "poe2scout"
    base_url = "https://poe2scout.com/api"

    def __init__(self, realm: str = "poe2", league: str = "Runes of Aldur", pause_seconds: float = 0.1) -> None:
        self.realm = realm
        self.league = league
        self.pause_seconds = pause_seconds

    def fetch_all_items(self, reference_currency: str = "divine") -> ItemSnapshot:
        categories = self.fetch_categories()
        items: list[ScoutItemPrice] = []
        for kind, category in categories:
            items.extend(self.fetch_category(kind, category, reference_currency))
        return ItemSnapshot(
            source=self.source_name,
            captured_at=datetime.now(timezone.utc),
            items=tuple(items),
        )

    def fetch_categories(self) -> list[tuple[str, dict[str, object]]]:
        payload = get_json(self._url("Items/Categories"))
        categories: list[tuple[str, dict[str, object]]] = []
        for category in payload.get("CurrencyCategories", []):
            categories.append(("currency", category))
        for category in payload.get("UniqueCategories", []):
            categories.append(("unique", category))
        return categories

    def fetch_category(
        self,
        kind: str,
        category: dict[str, object],
        reference_currency: str,
        per_page: int = 250,
    ) -> list[ScoutItemPrice]:
        endpoint = "Currencies/ByCategory" if kind == "currency" else "Uniques/ByCategory"
        category_api_id = str(category["ApiId"])
        category_label = str(category["Label"])
        page = 1
        results: list[ScoutItemPrice] = []

        while True:
            payload = get_json(
                self._url(endpoint),
                {
                    "Category": category_api_id,
                    "ReferenceCurrency": reference_currency,
                    "Page": page,
                    "PerPage": per_page,
                },
            )
            for item in payload.get("Items", []):
                current_price = item.get("CurrentPrice")
                if current_price is None:
                    continue
                results.append(
                    ScoutItemPrice(
                        source=self.source_name,
                        league=self.league,
                        item_id=int(item["ItemId"]),
                        api_id=str(item.get("ApiId") or ""),
                        name=str(item.get("Text") or item.get("Name") or ""),
                        category=category_api_id,
                        category_label=category_label,
                        kind=kind,
                        divine_price=float(current_price),
                        quantity=int(item["CurrentQuantity"]) if item.get("CurrentQuantity") is not None else None,
                        icon_url=str(item["IconUrl"]) if item.get("IconUrl") else None,
                    )
                )
            if page >= int(payload.get("Pages", 0)):
                break
            page += 1
            sleep(self.pause_seconds)

        return results

    def _url(self, endpoint: str) -> str:
        return f"{self.base_url}/{quote(self.realm)}/Leagues/{quote(self.league)}/{endpoint}"

