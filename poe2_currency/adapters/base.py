from __future__ import annotations

from abc import ABC, abstractmethod

from poe2_currency.models import MarketSnapshot


class MarketDataAdapter(ABC):
    source_name: str

    @abstractmethod
    def fetch_snapshot(self) -> MarketSnapshot:
        """Fetch and normalize a currency market snapshot."""

