"""Consolidated Tape SQLite storage engine.

Maintains an immutable time-series tape of every market tick ingested across venues.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any
from ticker_plant.models import TapeTick

DEFAULT_DB_PATH = Path("tape.db")


SCHEMA = """
CREATE TABLE IF NOT EXISTS ticks (
    tick_id TEXT PRIMARY KEY,
    timestamp REAL NOT NULL,
    iso_time TEXT NOT NULL,
    venue TEXT NOT NULL,
    venue_type TEXT NOT NULL,
    raw_model_id TEXT NOT NULL,
    instrument TEXT NOT NULL,
    input_usd_mtok REAL NOT NULL,
    output_usd_mtok REAL NOT NULL,
    cache_read_usd_mtok REAL NOT NULL DEFAULT 0.0,
    cache_write_usd_mtok REAL NOT NULL DEFAULT 0.0,
    context_length INTEGER NOT NULL DEFAULT 0,
    tps REAL,
    ttft_ms REAL,
    source_url TEXT,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_ticks_instrument_ts ON ticks(instrument, timestamp);
CREATE INDEX IF NOT EXISTS idx_ticks_venue_ts ON ticks(venue, timestamp);
CREATE INDEX IF NOT EXISTS idx_ticks_ts ON ticks(timestamp);
"""


class ConsolidatedTapeStore:
    """Manages appending and querying the SQLite Consolidated Tape."""

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        with self._conn:
            self._conn.executescript(SCHEMA)

    def close(self):
        self._conn.close()

    def append_ticks(self, ticks: list[TapeTick]) -> int:
        """Insert ticks into the tape. Ignores duplicates if tick_id collides."""
        if not ticks:
            return 0

        rows = [
            (
                t.tick_id,
                t.timestamp,
                t.iso_time,
                t.venue,
                t.venue_type,
                t.raw_model_id,
                t.instrument,
                t.input_usd_mtok,
                t.output_usd_mtok,
                t.cache_read_usd_mtok,
                t.cache_write_usd_mtok,
                t.context_length,
                t.tps,
                t.ttft_ms,
                t.source_url,
                t.notes,
            )
            for t in ticks
        ]

        query = """
        INSERT OR IGNORE INTO ticks (
            tick_id, timestamp, iso_time, venue, venue_type, raw_model_id,
            instrument, input_usd_mtok, output_usd_mtok, cache_read_usd_mtok,
            cache_write_usd_mtok, context_length, tps, ttft_ms, source_url, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        with self._conn:
            cursor = self._conn.executemany(query, rows)
            return cursor.rowcount

    def get_latest_ticks_per_venue(self, instrument: str | None = None) -> list[TapeTick]:
        """Fetch the most recent tick from each venue for a given instrument (or all instruments)."""
        params: list[Any] = []
        where_clause = ""
        if instrument:
            where_clause = "WHERE instrument = ?"
            params.append(instrument.upper())

        query = f"""
        SELECT * FROM ticks
        WHERE rowid IN (
            SELECT MAX(rowid)
            FROM ticks
            {where_clause}
            GROUP BY instrument, venue
        )
        ORDER BY instrument ASC, output_usd_mtok ASC
        """
        rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_tick(r) for r in rows]

    def get_historical_ticks(self, instrument: str, days: int = 30) -> list[TapeTick]:
        """Fetch ticks for an instrument within the past N days."""
        cutoff = time.time() - (days * 86400)
        query = """
        SELECT * FROM ticks
        WHERE instrument = ? AND timestamp >= ?
        ORDER BY timestamp ASC
        """
        rows = self._conn.execute(query, (instrument.upper(), cutoff)).fetchall()
        return [self._row_to_tick(r) for r in rows]

    def get_distinct_instruments(self) -> list[str]:
        query = "SELECT DISTINCT instrument FROM ticks ORDER BY instrument ASC"
        rows = self._conn.execute(query).fetchall()
        return [r["instrument"] for r in rows]

    def get_distinct_venues(self) -> list[str]:
        query = "SELECT DISTINCT venue FROM ticks ORDER BY venue ASC"
        rows = self._conn.execute(query).fetchall()
        return [r["venue"] for r in rows]

    def count_ticks(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) as count FROM ticks").fetchone()
        return row["count"] if row else 0

    @staticmethod
    def _row_to_tick(r: sqlite3.Row) -> TapeTick:
        return TapeTick(
            tick_id=r["tick_id"],
            timestamp=r["timestamp"],
            iso_time=r["iso_time"],
            venue=r["venue"],
            venue_type=r["venue_type"],
            raw_model_id=r["raw_model_id"],
            instrument=r["instrument"],
            input_usd_mtok=r["input_usd_mtok"],
            output_usd_mtok=r["output_usd_mtok"],
            cache_read_usd_mtok=r["cache_read_usd_mtok"],
            cache_write_usd_mtok=r["cache_write_usd_mtok"],
            context_length=r["context_length"],
            tps=r["tps"],
            ttft_ms=r["ttft_ms"],
            source_url=r["source_url"] or "",
            notes=r["notes"] or "",
        )
