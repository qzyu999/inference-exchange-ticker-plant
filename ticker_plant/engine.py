"""Ticker Plant central engine.

Orchestrates concurrent feed handler execution, instrument resolution,
and atomic commits to the Consolidated Tape.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence
from ticker_plant.config import ManifestRegistry
from ticker_plant.feed_handlers import create_feed_handler
from ticker_plant.models import PriceQuote, TapeTick
from ticker_plant.tape.store import ConsolidatedTapeStore

logger = logging.getLogger(__name__)


@dataclass
class IngestionReport:
    venues_polled: int
    venues_succeeded: int
    venues_failed: int
    quotes_received: int
    ticks_committed: int
    duration_seconds: float
    venue_breakdown: dict[str, int]


class TickerPlant:
    """The central Ticker Plant orchestrator."""

    def __init__(
        self,
        manifests_dir: Path | str = "manifests",
        db_path: Path | str = "tape.db",
    ):
        self.manifests_dir = Path(manifests_dir)
        self.registry = ManifestRegistry()
        self.registry.load_directory(self.manifests_dir)
        self.store = ConsolidatedTapeStore(db_path=db_path)

    async def poll_venue(self, venue_name: str) -> list[PriceQuote]:
        """Poll a single venue feed handler."""
        manifest = self.registry.feed_handlers.get(venue_name)
        if not manifest:
            raise ValueError(f"Venue manifest not found: {venue_name}")

        handler = create_feed_handler(manifest)
        try:
            return await handler.fetch_quotes()
        except Exception as e:
            logger.error(f"FeedHandler [{venue_name}] error: {e}", exc_info=True)
            return []

    async def run_cycle(self, selected_venues: Sequence[str] | None = None) -> IngestionReport:
        """Run a full market data collection cycle across all active venues."""
        import time
        start_t = time.time()

        active_venues = [
            v for v, m in self.registry.feed_handlers.items()
            if m.spec.active and (selected_venues is None or v in selected_venues)
        ]

        tasks = [self.poll_venue(v) for v in active_venues]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_ticks: list[TapeTick] = []
        breakdown: dict[str, int] = {}
        succeeded = 0
        failed = 0

        for venue_name, res in zip(active_venues, results):
            if isinstance(res, Exception):
                logger.error(f"Venue [{venue_name}] execution failed: {res}")
                failed += 1
                breakdown[venue_name] = 0
                continue

            succeeded += 1
            quotes: list[PriceQuote] = res
            breakdown[venue_name] = len(quotes)

            for q in quotes:
                instrument = self.registry.resolve_instrument(q.raw_model_id)
                tick = TapeTick.from_quote(q, instrument=instrument)
                all_ticks.append(tick)

        committed = self.store.append_ticks(all_ticks)
        duration = time.time() - start_t

        return IngestionReport(
            venues_polled=len(active_venues),
            venues_succeeded=succeeded,
            venues_failed=failed,
            quotes_received=len(all_ticks),
            ticks_committed=committed,
            duration_seconds=round(duration, 2),
            venue_breakdown=breakdown,
        )
