from __future__ import annotations

import re
from dataclasses import dataclass

from poe2_currency.models import CashItemPrice, ScoutItemPrice, normalize_item_name

QUANTITY_PREFIX = re.compile(r"^\s*(?P<quantity>\d+(?:\.\d+)?)\s+")


@dataclass(frozen=True)
class ArbitrageCandidate:
    cash_item: CashItemPrice
    scout_item: ScoutItemPrice

    @property
    def listing_quantity(self) -> float:
        match = QUANTITY_PREFIX.match(self.cash_item.title)
        if not match:
            return 1.0
        return float(match.group("quantity"))

    @property
    def listing_divine_value(self) -> float:
        return self.listing_quantity * self.scout_item.divine_price

    @property
    def usd_per_divine(self) -> float:
        return self.cash_item.price_usd / self.listing_divine_value

    def arbitrage_multiple(self, direct_divine_usd: float) -> float:
        return direct_divine_usd / self.usd_per_divine

    def to_row(self, rank: int, direct_divine_usd: float) -> dict[str, object]:
        return {
            "arbitrage_rank": rank,
            "arbitrage_multiple": round(self.arbitrage_multiple(direct_divine_usd), 4),
            "poecurrency_title": self.cash_item.title,
            "poecurrency_category": self.cash_item.category,
            "poecurrency_price_usd": round(self.cash_item.price_usd, 4),
            "poecurrency_stock": self.cash_item.stock,
            "listing_quantity": round(self.listing_quantity, 4),
            "scout_name": self.scout_item.name,
            "scout_category": self.scout_item.category_label,
            "scout_kind": self.scout_item.kind,
            "scout_divine_price": round(self.scout_item.divine_price, 6),
            "listing_divine_value": round(self.listing_divine_value, 6),
            "scout_quantity": self.scout_item.quantity,
            "price_per_divine_usd": round(self.usd_per_divine, 6),
            "usd_per_divine": round(self.usd_per_divine, 6),
            "direct_divine_price_usd": round(direct_divine_usd, 4),
        }


def find_candidates(
    cash_items: list[CashItemPrice],
    scout_items: list[ScoutItemPrice],
    min_divine_price: float = 0.0,
    scout_kind: str | None = None,
) -> list[ArbitrageCandidate]:
    if scout_kind:
        scout_items = [item for item in scout_items if item.kind == scout_kind]
    all_scout_keys = {item.key for item in scout_items}
    scout_by_key = {item.key: item for item in scout_items if item.divine_price >= min_divine_price}
    candidates: list[ArbitrageCandidate] = []

    for cash_item in cash_items:
        scout_item = scout_by_key.get(cash_item.key)
        if scout_item:
            candidates.append(ArbitrageCandidate(cash_item, scout_item))
            continue
        if cash_item.key in all_scout_keys:
            continue

        fallback = _best_substring_match(cash_item, scout_by_key)
        if fallback:
            candidates.append(ArbitrageCandidate(cash_item, fallback))

    return sorted(candidates, key=lambda candidate: candidate.usd_per_divine)


def _best_substring_match(
    cash_item: CashItemPrice,
    scout_by_key: dict[str, ScoutItemPrice],
) -> ScoutItemPrice | None:
    cash_key = cash_item.key
    best: ScoutItemPrice | None = None
    best_len = 0
    for scout_key, scout_item in scout_by_key.items():
        if len(scout_key) < 6:
            continue
        if scout_key in cash_key or normalize_item_name(scout_item.name) in cash_key:
            if len(scout_key) > best_len:
                best = scout_item
                best_len = len(scout_key)
    return best
