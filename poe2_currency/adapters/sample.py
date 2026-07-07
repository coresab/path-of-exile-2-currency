from __future__ import annotations

from datetime import datetime, timezone

from poe2_currency.adapters.base import MarketDataAdapter
from poe2_currency.models import CurrencyRate, MarketSnapshot


class SampleMarketDataAdapter(MarketDataAdapter):
    source_name = "sample"

    def fetch_snapshot(self) -> MarketSnapshot:
        return MarketSnapshot(
            source=self.source_name,
            captured_at=datetime.now(timezone.utc),
            rates=(
                CurrencyRate("Chaos Orb", 1.0),
                CurrencyRate("Exalted Orb", 8.0),
                CurrencyRate("Regal Orb", 0.5),
                CurrencyRate("Alchemy Orb", 0.25),
                CurrencyRate("Divine Orb", 90.0),
            ),
        )

