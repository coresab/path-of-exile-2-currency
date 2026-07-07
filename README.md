# Path of Exile 2 Currency

A small Python toolkit for collecting Path of Exile 2 currency market snapshots and valuing trades from the command line.

The toolkit now supports two live sources:

- POE2Scout API: all currency and unique categories, normalized to divine-orb prices.
- POECurrency: all POE 2 item categories from `poe-2-items`, normalized to USD prices.
- `arbitrage`: joins matching items and ranks by cheapest `usd_per_divine`.
- `value` converts one or more currency amounts into a target currency.

## Quick Start

```bash
python3 -m poe2_currency fetch-scout
python3 -m poe2_currency fetch-poecurrency
python3 -m poe2_currency arbitrage \
  --scout data/YYYYMMDD-HHMMSS-poe2scout-items.json \
  --poecurrency data/YYYYMMDD-HHMMSS-poecurrency-items.json \
  --direct-divine-usd 0.05 \
  --scout-kind currency \
  --min-divine 0.01 \
  --limit 0 \
  --out exports/arbitrage.csv
```

## Project Layout

```text
poe2_currency/
  __main__.py          CLI entry point
  cli.py              command definitions
  models.py           snapshot and currency models
  pricing.py          valuation engine
  arbitrage.py        item matching and report rows
  storage.py          JSON snapshot persistence
  adapters/
    base.py           market-source interface
    sample.py         built-in seed data
    poe2scout.py      POE2Scout API adapter
    poecurrency.py    POECurrency HTML/API adapter
data/                 saved snapshots
exports/              future CSV/report output
tests/                unit tests
```

## Notes

Currency rates are stored as `chaos_equivalent`: the number of chaos orbs one unit of the currency is worth. That keeps conversions simple:

```text
amount * source_chaos_equivalent / target_chaos_equivalent
```

Real market adapters should normalize their output into the `MarketSnapshot` model in `poe2_currency/models.py`.

## Live Data Commands

Fetch POE2Scout data for the current softcore league:

```bash
python3 -m poe2_currency fetch-scout --league "Runes of Aldur" --reference-currency divine
```

Fetch POECurrency listings for the matching softcore server:

```bash
python3 -m poe2_currency fetch-poecurrency --server "Runes of Aldur SC"
```

Generate the comparison report:

```bash
python3 -m poe2_currency arbitrage \
  --scout data/20260707-054528-poe2scout-items.json \
  --poecurrency data/20260707-054617-poecurrency-items.json \
  --direct-divine-usd 0.05 \
  --scout-kind currency \
  --min-divine 0.01 \
  --limit 0 \
  --out exports/arbitrage.csv
```

`arbitrage_multiple` is the main ranking column. Higher is better. It is calculated as:

```text
direct_divine_price_usd / usd_per_divine
```

For example, if an item effectively costs `$0.01` per divine and direct divine buying costs `$0.05`, the arbitrage multiple is `5x`.

`price_per_divine_usd` is the direct scan column for your question: how many dollars it costs to buy that good and trade it into one divine. Lower is better.

## Caveats

- POE2Scout prices are market estimates. Verify any large spread in-game before acting.
- POECurrency prices may be per item or per unit/stack depending on category. Treat very small USD prices as leads to inspect, not guaranteed profit.
- Real-money item trading may violate game or platform rules. Check the relevant terms before using the output beyond research.
