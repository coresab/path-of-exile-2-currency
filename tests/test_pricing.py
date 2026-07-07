from datetime import datetime, timezone
from unittest import TestCase, main

from poe2_currency.models import CurrencyRate, MarketSnapshot
from poe2_currency.arbitrage import ArbitrageCandidate, find_candidates
from poe2_currency.models import CashItemPrice, ScoutItemPrice
from poe2_currency.pricing import CurrencyAmount, PriceBook, parse_currency_amount


class PricingTests(TestCase):
    def test_parse_currency_amount(self):
        amount = parse_currency_amount("3 exalted orb")

        self.assertEqual(amount.amount, 3)
        self.assertEqual(amount.currency, "exalted orb")

    def test_total_converts_to_target_currency(self):
        snapshot = MarketSnapshot(
            source="test",
            captured_at=datetime.now(timezone.utc),
            rates=(
                CurrencyRate("Chaos Orb", 1),
                CurrencyRate("Exalted Orb", 8),
                CurrencyRate("Divine Orb", 80),
            ),
        )

        total = PriceBook(snapshot).total(
            [CurrencyAmount(2, "exalt"), CurrencyAmount(16, "chaos")],
            "divine",
        )

        self.assertEqual(total, 0.4)

    def test_arbitrage_does_not_fallback_when_exact_match_is_filtered(self):
        cash = CashItemPrice(
            source="poecurrency",
            server="Runes of Aldur SC",
            category_id=1,
            category="Crafted Currency / Essences",
            goods_no="1",
            title="Greater Essence of Command",
            price_usd=0.01,
        )
        scout_items = [
            ScoutItemPrice("poe2scout", "Runes of Aldur", 1, "essence-of-command", "Essence of Command", "essences", "Essences", "currency", 1.0),
            ScoutItemPrice("poe2scout", "Runes of Aldur", 2, "greater-essence-of-command", "Greater Essence of Command", "essences", "Essences", "currency", 0.001),
        ]

        candidates = find_candidates([cash], scout_items, min_divine_price=0.01)

        self.assertEqual(candidates, [])

    def test_arbitrage_row_includes_rank_and_multiple(self):
        cash = CashItemPrice(
            source="poecurrency",
            server="Runes of Aldur SC",
            category_id=1,
            category="Currency",
            goods_no="1",
            title="700 Exalted Orb",
            price_usd=0.01,
        )
        scout = ScoutItemPrice(
            "poe2scout",
            "Runes of Aldur",
            1,
            "exalted",
            "Exalted Orb",
            "currency",
            "Currency",
            "currency",
            1 / 700,
        )

        row = ArbitrageCandidate(cash, scout).to_row(rank=1, direct_divine_usd=0.05)

        self.assertEqual(row["arbitrage_rank"], 1)
        self.assertEqual(row["arbitrage_multiple"], 5.0)
        self.assertEqual(row["price_per_divine_usd"], 0.01)
        self.assertNotIn("goods_no", row)

    def test_arbitrage_can_filter_to_currency_matches(self):
        cash_items = [
            CashItemPrice("poecurrency", "Runes of Aldur SC", 1, "Currency", "1", "Divine Orb", 0.05),
            CashItemPrice("poecurrency", "Runes of Aldur SC", 2, "Weapons", "2", "Mageblood", 10.0),
        ]
        scout_items = [
            ScoutItemPrice("poe2scout", "Runes of Aldur", 1, "divine", "Divine Orb", "currency", "Currency", "currency", 1.0),
            ScoutItemPrice("poe2scout", "Runes of Aldur", 2, "mageblood", "Mageblood", "accessory", "Accessories", "unique", 400.0),
        ]

        candidates = find_candidates(cash_items, scout_items, scout_kind="currency")

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].scout_item.kind, "currency")


if __name__ == "__main__":
    main()
