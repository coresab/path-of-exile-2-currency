from __future__ import annotations

import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Iterable

from poe2_currency.models import CashItemPrice, ItemSnapshot, MarketSnapshot, ScoutItemPrice


def default_data_dir() -> Path:
    return Path.cwd() / "data"


def snapshot_filename(snapshot: MarketSnapshot) -> str:
    timestamp = snapshot.captured_at.strftime("%Y%m%d-%H%M%S")
    safe_source = snapshot.source.lower().replace(" ", "-")
    return f"{timestamp}-{safe_source}.json"


def save_snapshot(snapshot: MarketSnapshot, data_dir: Path | None = None) -> Path:
    directory = data_dir or default_data_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / snapshot_filename(snapshot)
    path.write_text(json.dumps(snapshot.to_dict(), indent=2) + "\n", encoding="utf-8")
    return path


def save_item_snapshot(snapshot: ItemSnapshot, data_dir: Path | None = None) -> Path:
    directory = data_dir or default_data_dir()
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = snapshot.captured_at.strftime("%Y%m%d-%H%M%S")
    safe_source = snapshot.source.lower().replace(" ", "-")
    path = directory / f"{timestamp}-{safe_source}-items.json"
    path.write_text(json.dumps(snapshot.to_dict(), indent=2) + "\n", encoding="utf-8")
    return path


def load_scout_items(path: Path) -> list[ScoutItemPrice]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [ScoutItemPrice.from_dict(item) for item in data["items"]]


def load_cash_items(path: Path) -> list[CashItemPrice]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [CashItemPrice.from_dict(item) for item in data["items"]]


def write_csv(path: Path, rows: Iterable[dict[str, object]]) -> None:
    rows = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def load_snapshot(path: Path) -> MarketSnapshot:
    return MarketSnapshot.from_dict(json.loads(path.read_text(encoding="utf-8")))


def latest_snapshot(data_dir: Path | None = None) -> Path:
    directory = data_dir or default_data_dir()
    snapshots = sorted(directory.glob("*.json"), key=lambda path: path.stat().st_mtime)
    if not snapshots:
        raise FileNotFoundError(f"No snapshots found in {directory}")
    return snapshots[-1]


def parse_snapshot_time(value: str) -> datetime:
    return datetime.fromisoformat(value)
