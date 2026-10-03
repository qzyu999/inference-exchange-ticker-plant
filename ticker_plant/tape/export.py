"""Export utilities for Consolidated Tape data (JSON, CSV)."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path
from ticker_plant.tape.store import ConsolidatedTapeStore
from ticker_plant.tape.analytics import get_bbo, get_depth


def export_tape_json(store: ConsolidatedTapeStore, output_file: Path | str, latest_only: bool = False):
    """Export tape ticks to a JSON file."""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if latest_only:
        ticks = store.get_latest_ticks_per_venue()
    else:
        # Export all ticks
        rows = store._conn.execute("SELECT * FROM ticks ORDER BY timestamp ASC").fetchall()
        ticks = [store._row_to_tick(r) for r in rows]

    data = [asdict(t) for t in ticks]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def export_tape_csv(store: ConsolidatedTapeStore, output_file: Path | str, latest_only: bool = False):
    """Export tape ticks to a CSV file."""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if latest_only:
        ticks = store.get_latest_ticks_per_venue()
    else:
        rows = store._conn.execute("SELECT * FROM ticks ORDER BY timestamp ASC").fetchall()
        ticks = [store._row_to_tick(r) for r in rows]

    if not ticks:
        return

    fieldnames = list(asdict(ticks[0]).keys())
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for t in ticks:
            writer.writerow(asdict(t))
