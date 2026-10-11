"""Consolidated Tape SQLite storage engine.

Maintains an immutable time-series tape of every market tick ingested across venues.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any
from ticker_plant.models import TapeTick, DemandMetric

DEFAULT_DB_PATH = Path("data/tape.db")


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

CREATE TABLE IF NOT EXISTS model_demand (
    instrument TEXT PRIMARY KEY,
    timestamp REAL NOT NULL,
    iso_time TEXT NOT NULL,
    openrouter_rank INTEGER,
    openrouter_weekly_tokens INTEGER,
    openrouter_requests INTEGER,
    openrouter_spend_usd REAL,
    openrouter_model_id TEXT,
    hf_model_id TEXT,
    hf_downloads_30d INTEGER,
    hf_likes INTEGER,
    arena_rank INTEGER,
    arena_rating REAL,
    arena_votes INTEGER,
    arena_model_name TEXT,
    demand_index REAL
);

CREATE INDEX IF NOT EXISTS idx_demand_ts ON model_demand(timestamp);
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

    def upsert_demand_metrics(self, metrics: list[DemandMetric]) -> int:
        """Insert or update consolidated model demand telemetry."""
        if not metrics:
            return 0

        rows = [
            (
                m.instrument,
                m.timestamp,
                m.iso_time,
                m.openrouter_rank,
                m.openrouter_weekly_tokens,
                m.openrouter_requests,
                m.openrouter_spend_usd,
                m.openrouter_model_id,
                m.hf_model_id,
                m.hf_downloads_30d,
                m.hf_likes,
                m.arena_rank,
                m.arena_rating,
                m.arena_votes,
                m.arena_model_name,
                m.demand_index,
            )
            for m in metrics
        ]

        query = """
        INSERT INTO model_demand (
            instrument, timestamp, iso_time, openrouter_rank, openrouter_weekly_tokens,
            openrouter_requests, openrouter_spend_usd, openrouter_model_id,
            hf_model_id, hf_downloads_30d, hf_likes,
            arena_rank, arena_rating, arena_votes, arena_model_name, demand_index
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(instrument) DO UPDATE SET
            timestamp=excluded.timestamp,
            iso_time=excluded.iso_time,
            openrouter_rank=COALESCE(excluded.openrouter_rank, model_demand.openrouter_rank),
            openrouter_weekly_tokens=COALESCE(excluded.openrouter_weekly_tokens, model_demand.openrouter_weekly_tokens),
            openrouter_requests=COALESCE(excluded.openrouter_requests, model_demand.openrouter_requests),
            openrouter_spend_usd=COALESCE(excluded.openrouter_spend_usd, model_demand.openrouter_spend_usd),
            openrouter_model_id=COALESCE(excluded.openrouter_model_id, model_demand.openrouter_model_id),
            hf_model_id=COALESCE(excluded.hf_model_id, model_demand.hf_model_id),
            hf_downloads_30d=COALESCE(excluded.hf_downloads_30d, model_demand.hf_downloads_30d),
            hf_likes=COALESCE(excluded.hf_likes, model_demand.hf_likes),
            arena_rank=COALESCE(excluded.arena_rank, model_demand.arena_rank),
            arena_rating=COALESCE(excluded.arena_rating, model_demand.arena_rating),
            arena_votes=COALESCE(excluded.arena_votes, model_demand.arena_votes),
            arena_model_name=COALESCE(excluded.arena_model_name, model_demand.arena_model_name),
            demand_index=COALESCE(excluded.demand_index, model_demand.demand_index)
        """
        with self._conn:
            cursor = self._conn.executemany(query, rows)
            return cursor.rowcount

    def get_all_demand_metrics(self) -> dict[str, DemandMetric]:
        """Fetch latest demand metrics for all instruments."""
        query = "SELECT * FROM model_demand ORDER BY COALESCE(demand_index, 0) DESC, instrument ASC"
        rows = self._conn.execute(query).fetchall()
        return {r["instrument"]: self._row_to_demand_metric(r) for r in rows}

    def get_demand_metric(self, instrument: str) -> DemandMetric | None:
        """Fetch demand metric for a single instrument."""
        query = "SELECT * FROM model_demand WHERE instrument = ?"
        row = self._conn.execute(query, (instrument.upper(),)).fetchone()
        return self._row_to_demand_metric(row) if row else None

    @staticmethod
    def _row_to_demand_metric(r: sqlite3.Row) -> DemandMetric:
        return DemandMetric(
            instrument=r["instrument"],
            timestamp=r["timestamp"],
            iso_time=r["iso_time"],
            openrouter_rank=r["openrouter_rank"],
            openrouter_weekly_tokens=r["openrouter_weekly_tokens"],
            openrouter_requests=r["openrouter_requests"],
            openrouter_spend_usd=r["openrouter_spend_usd"],
            openrouter_model_id=r["openrouter_model_id"],
            hf_model_id=r["hf_model_id"],
            hf_downloads_30d=r["hf_downloads_30d"],
            hf_likes=r["hf_likes"],
            arena_rank=r["arena_rank"],
            arena_rating=r["arena_rating"],
            arena_votes=r["arena_votes"],
            arena_model_name=r["arena_model_name"],
            demand_index=r["demand_index"],
        )

