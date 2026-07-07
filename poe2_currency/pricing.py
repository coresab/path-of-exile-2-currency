from __future__ import annotations

import re
from dataclasses import dataclass

from poe2_currency.models import MarketSnapshot, normalize_currency_name


class PricingError(ValueError):
    pass


@dataclass(frozen=True)
class CurrencyAmount:
    amount: float
    currency: str

    @property
    def key(self) -> str:
        return normalize_currency_name(self.currency)


AMOUNT_PATTERN = re.compile(r"^\s*(?P<amount>\d+(?:\.\d+)?)\s+(?P<currency>.+?)\s*$")
ALIASES = {
    "alc": "alchemy orb",
    "alchemy": "alchemy orb",
    "chaos": "chaos orb",
    "div": "divine orb",
    "divine": "divine orb",
    "ex": "exalted orb",
    "exalt": "exalted orb",
    "exalted": "exalted orb",
    "regal": "regal orb",
}


def parse_currency_amount(value: str) -> CurrencyAmount:
    match = AMOUNT_PATTERN.match(value)
    if not match:
        raise PricingError(f"Could not parse currency amount: {value!r}")
    return CurrencyAmount(
        amount=float(match.group("amount")),
        currency=match.group("currency"),
    )


class PriceBook:
    def __init__(self, snapshot: MarketSnapshot) -> None:
        self.snapshot = snapshot
        self.rates = snapshot.by_name()

    def convert(self, value: CurrencyAmount, target_currency: str) -> float:
        source_rate = self._rate_for(value.currency)
        target_rate = self._rate_for(target_currency)
        return value.amount * source_rate.chaos_equivalent / target_rate.chaos_equivalent

    def total(self, values: list[CurrencyAmount], target_currency: str) -> float:
        return sum(self.convert(value, target_currency) for value in values)

    def _rate_for(self, currency: str):
        key = normalize_currency_name(currency)
        key = ALIASES.get(key, key)
        if key not in self.rates and not key.endswith(" orb"):
            key = f"{key} orb"
        try:
            return self.rates[key]
        except KeyError as exc:
            known = ", ".join(sorted(rate.name for rate in self.rates.values()))
            raise PricingError(f"Unknown currency {currency!r}. Known currencies: {known}") from exc
