from __future__ import annotations

import argparse
from pathlib import Path

from poe2_currency.adapters.poecurrency import PoeCurrencyAdapter
from poe2_currency.adapters.poe2scout import Poe2ScoutAdapter
from poe2_currency.adapters.sample import SampleMarketDataAdapter
from poe2_currency.arbitrage import find_candidates
from poe2_currency.pricing import PriceBook, PricingError, parse_currency_amount
from poe2_currency.storage import (
    latest_snapshot,
    load_cash_items,
    load_scout_items,
    load_snapshot,
    save_item_snapshot,
    save_snapshot,
    write_csv,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="poe2-currency",
        description="Collect and value Path of Exile 2 currency market data.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_sample = subparsers.add_parser("fetch-sample", help="write a sample market snapshot")
    fetch_sample.add_argument("--data-dir", type=Path, default=Path("data"))

    fetch_scout = subparsers.add_parser("fetch-scout", help="fetch POE2Scout prices in divine orbs")
    fetch_scout.add_argument("--realm", default="poe2")
    fetch_scout.add_argument("--league", default="Runes of Aldur")
    fetch_scout.add_argument("--reference-currency", default="divine")
    fetch_scout.add_argument("--data-dir", type=Path, default=Path("data"))

    fetch_poecurrency = subparsers.add_parser("fetch-poecurrency", help="fetch POECurrency item prices in USD")
    fetch_poecurrency.add_argument("--server", default="Runes of Aldur SC")
    fetch_poecurrency.add_argument("--data-dir", type=Path, default=Path("data"))

    arbitrage = subparsers.add_parser("arbitrage", help="rank matched cash-site items by USD per divine")
    arbitrage.add_argument("--scout", type=Path, required=True, help="POE2Scout item snapshot JSON")
    arbitrage.add_argument("--poecurrency", type=Path, required=True, help="POECurrency item snapshot JSON")
    arbitrage.add_argument("--min-divine", type=float, default=0.0)
    arbitrage.add_argument("--limit", type=int, default=50, help="number of rows to write; use 0 for all matches")
    arbitrage.add_argument(
        "--scout-kind",
        choices=("all", "currency", "unique"),
        default="all",
        help="filter by POE2Scout matched item kind",
    )
    arbitrage.add_argument(
        "--direct-divine-usd",
        type=float,
        required=True,
        help="cash-site USD price for buying 1 divine orb directly",
    )
    arbitrage.add_argument("--out", type=Path, default=Path("exports/arbitrage.csv"))

    refresh = subparsers.add_parser("refresh", help="fetch live data and regenerate the arbitrage CSV")
    refresh.add_argument("--realm", default="poe2")
    refresh.add_argument("--league", default="Runes of Aldur")
    refresh.add_argument("--server", default="Runes of Aldur SC")
    refresh.add_argument("--reference-currency", default="divine")
    refresh.add_argument("--direct-divine-usd", type=float, required=True)
    refresh.add_argument("--scout-kind", choices=("all", "currency", "unique"), default="currency")
    refresh.add_argument("--min-divine", type=float, default=0.01)
    refresh.add_argument("--limit", type=int, default=0, help="number of rows to write; use 0 for all matches")
    refresh.add_argument("--data-dir", type=Path, default=Path("data"))
    refresh.add_argument("--out", type=Path, default=Path("exports/arbitrage.csv"))

    value = subparsers.add_parser("value", help="value one or more currency amounts")
    value.add_argument("amounts", nargs="+", help='currency amount, e.g. "3 exalted orb"')
    value.add_argument("--in", dest="target_currency", default="chaos orb")
    value.add_argument("--snapshot", type=Path, help="snapshot JSON file; defaults to latest in data/")
    value.add_argument("--data-dir", type=Path, default=Path("data"))

    return parser


def fetch_sample(args: argparse.Namespace) -> int:
    snapshot = SampleMarketDataAdapter().fetch_snapshot()
    path = save_snapshot(snapshot, args.data_dir)
    print(f"Saved {path}")
    return 0


def fetch_scout(args: argparse.Namespace) -> int:
    snapshot = Poe2ScoutAdapter(realm=args.realm, league=args.league).fetch_all_items(args.reference_currency)
    path = save_item_snapshot(snapshot, args.data_dir)
    print(f"Saved {len(snapshot.items)} POE2Scout items to {path}")
    return 0


def fetch_poecurrency(args: argparse.Namespace) -> int:
    snapshot = PoeCurrencyAdapter(server=args.server).fetch_all_items()
    path = save_item_snapshot(snapshot, args.data_dir)
    print(f"Saved {len(snapshot.items)} POECurrency items to {path}")
    return 0


def run_arbitrage(args: argparse.Namespace) -> int:
    scout_items = load_scout_items(args.scout)
    cash_items = load_cash_items(args.poecurrency)
    write_arbitrage_report(
        scout_items=scout_items,
        cash_items=cash_items,
        direct_divine_usd=args.direct_divine_usd,
        scout_kind=args.scout_kind,
        min_divine_price=args.min_divine,
        limit=args.limit,
        out=args.out,
    )
    return 0


def write_arbitrage_report(
    scout_items,
    cash_items,
    direct_divine_usd: float,
    scout_kind: str,
    min_divine_price: float,
    limit: int,
    out: Path,
) -> list[dict[str, object]]:
    scout_kind_filter = None if scout_kind == "all" else scout_kind
    candidates = find_candidates(cash_items, scout_items, min_divine_price=min_divine_price, scout_kind=scout_kind_filter)
    selected_candidates = candidates if limit == 0 else candidates[:limit]
    rows = [
        candidate.to_row(rank=index, direct_divine_usd=direct_divine_usd)
        for index, candidate in enumerate(selected_candidates, start=1)
    ]
    write_csv(out, rows)
    print(f"Wrote {len(rows)} candidates to {out}")
    if rows:
        best = rows[0]
        print(
            "Best: "
            f"{best['poecurrency_title']} -> {best['scout_divine_price']} div "
            f"at ${best['poecurrency_price_usd']} "
            f"({best['arbitrage_multiple']}x vs direct divine)"
        )
    return rows


def refresh_report(args: argparse.Namespace) -> int:
    scout_snapshot = Poe2ScoutAdapter(realm=args.realm, league=args.league).fetch_all_items(args.reference_currency)
    scout_path = save_item_snapshot(scout_snapshot, args.data_dir)
    print(f"Saved {len(scout_snapshot.items)} POE2Scout items to {scout_path}")

    cash_snapshot = PoeCurrencyAdapter(server=args.server).fetch_all_items()
    cash_path = save_item_snapshot(cash_snapshot, args.data_dir)
    print(f"Saved {len(cash_snapshot.items)} POECurrency items to {cash_path}")

    write_arbitrage_report(
        scout_items=list(scout_snapshot.items),
        cash_items=list(cash_snapshot.items),
        direct_divine_usd=args.direct_divine_usd,
        scout_kind=args.scout_kind,
        min_divine_price=args.min_divine,
        limit=args.limit,
        out=args.out,
    )
    return 0


def value_trade(args: argparse.Namespace) -> int:
    snapshot_path = args.snapshot or latest_snapshot(args.data_dir)
    snapshot = load_snapshot(snapshot_path)
    price_book = PriceBook(snapshot)
    values = [parse_currency_amount(amount) for amount in args.amounts]
    total = price_book.total(values, args.target_currency)
    print(f"{total:.4f} {args.target_currency}")
    print(f"Snapshot: {snapshot_path}")
    return 0


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "fetch-sample":
            raise SystemExit(fetch_sample(args))
        if args.command == "fetch-scout":
            raise SystemExit(fetch_scout(args))
        if args.command == "fetch-poecurrency":
            raise SystemExit(fetch_poecurrency(args))
        if args.command == "arbitrage":
            raise SystemExit(run_arbitrage(args))
        if args.command == "refresh":
            raise SystemExit(refresh_report(args))
        if args.command == "value":
            raise SystemExit(value_trade(args))
    except (FileNotFoundError, PricingError, ValueError) as exc:
        parser.exit(1, f"error: {exc}\n")
