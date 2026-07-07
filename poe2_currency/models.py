from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


def normalize_currency_name(name: str) -> str:
    return " ".join(name.strip().lower().replace("_", " ").replace("-", " ").split())


@dataclass(frozen=True)
class CurrencyRate:
    name: str
    chaos_equivalent: float
    confidence: float = 1.0

    def __post_init__(self) -> None:
        if self.chaos_equivalent <= 0:
            raise ValueError("chaos_equivalent must be positive")
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")

    @property
    def key(self) -> str:
        return normalize_currency_name(self.name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "chaos_equivalent": self.chaos_equivalent,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CurrencyRate":
        return cls(
            name=str(data["name"]),
            chaos_equivalent=float(data["chaos_equivalent"]),
            confidence=float(data.get("confidence", 1.0)),
        )


@dataclass(frozen=True)
class MarketSnapshot:
    source: str
    captured_at: datetime
    rates: tuple[CurrencyRate, ...]

    def __post_init__(self) -> None:
        if not self.rates:
            raise ValueError("snapshot must contain at least one rate")

    def by_name(self) -> dict[str, CurrencyRate]:
        return {rate.key: rate for rate in self.rates}

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "captured_at": self.captured_at.isoformat(),
            "rates": [rate.to_dict() for rate in self.rates],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MarketSnapshot":
        captured_at = datetime.fromisoformat(str(data["captured_at"]))
        if captured_at.tzinfo is None:
            captured_at = captured_at.replace(tzinfo=timezone.utc)
        return cls(
            source=str(data["source"]),
            captured_at=captured_at,
            rates=tuple(CurrencyRate.from_dict(rate) for rate in data["rates"]),
        )


@dataclass(frozen=True)
class ScoutItemPrice:
    source: str
    league: str
    item_id: int
    api_id: str
    name: str
    category: str
    category_label: str
    kind: str
    divine_price: float
    quantity: int | None = None
    icon_url: str | None = None

    @property
    def key(self) -> str:
        return normalize_item_name(self.name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "league": self.league,
            "item_id": self.item_id,
            "api_id": self.api_id,
            "name": self.name,
            "category": self.category,
            "category_label": self.category_label,
            "kind": self.kind,
            "divine_price": self.divine_price,
            "quantity": self.quantity,
            "icon_url": self.icon_url,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScoutItemPrice":
        return cls(
            source=str(data["source"]),
            league=str(data["league"]),
            item_id=int(data["item_id"]),
            api_id=str(data.get("api_id", "")),
            name=str(data["name"]),
            category=str(data["category"]),
            category_label=str(data["category_label"]),
            kind=str(data["kind"]),
            divine_price=float(data["divine_price"]),
            quantity=int(data["quantity"]) if data.get("quantity") is not None else None,
            icon_url=str(data["icon_url"]) if data.get("icon_url") else None,
        )


@dataclass(frozen=True)
class CashItemPrice:
    source: str
    server: str
    category_id: int
    category: str
    goods_no: str
    title: str
    price_usd: float
    stock: int | None = None
    image_url: str | None = None
    sku: str | None = None

    @property
    def comparable_name(self) -> str:
        return strip_listing_suffix(self.title)

    @property
    def key(self) -> str:
        return normalize_item_name(self.comparable_name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "server": self.server,
            "category_id": self.category_id,
            "category": self.category,
            "goods_no": self.goods_no,
            "title": self.title,
            "comparable_name": self.comparable_name,
            "price_usd": self.price_usd,
            "stock": self.stock,
            "image_url": self.image_url,
            "sku": self.sku,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CashItemPrice":
        return cls(
            source=str(data["source"]),
            server=str(data["server"]),
            category_id=int(data["category_id"]),
            category=str(data["category"]),
            goods_no=str(data["goods_no"]),
            title=str(data["title"]),
            price_usd=float(data["price_usd"]),
            stock=int(data["stock"]) if data.get("stock") is not None else None,
            image_url=str(data["image_url"]) if data.get("image_url") else None,
            sku=str(data["sku"]) if data.get("sku") else None,
        )


@dataclass(frozen=True)
class ItemSnapshot:
    source: str
    captured_at: datetime
    items: tuple[ScoutItemPrice | CashItemPrice, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "captured_at": self.captured_at.isoformat(),
            "items": [item.to_dict() for item in self.items],
        }


def normalize_item_name(name: str) -> str:
    value = strip_listing_suffix(name)
    value = value.lower().replace("&", " and ")
    value = "".join(char if char.isalnum() else " " for char in value)
    return " ".join(value.split())


def strip_listing_suffix(name: str) -> str:
    return name.split("#", 1)[0].replace("POECurrency POE 2", "").strip()
