"""Static Ratecard Feed Handler.

Ingests declarative price quotes directly specified in YAML manifests.
Ideal for frontier labs (OpenAI, Anthropic, Google) that publish static rate cards,
and community/OTC announcements on Twitter/Discord.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from ticker_plant.feed_handlers.base import BaseFeedHandler
from ticker_plant.models import PriceQuote

logger = logging.getLogger(__name__)


class StaticRatecardFeedHandler(BaseFeedHandler):
    """Feed handler for declarative ratecards."""

    async def fetch_quotes(self) -> list[PriceQuote]:
        quotes: list[PriceQuote] = []
        now = time.time()

        for q in self.spec.quotes:
            # Parse reported_at if available
            ts = now
            if q.reported_at:
                try:
                    dt = datetime.fromisoformat(q.reported_at.replace("Z", "+00:00"))
                    ts = dt.timestamp()
                except Exception:
                    ts = now

            quotes.append(PriceQuote(
                venue=self.name,
                raw_model_id=q.raw_model_id,
                input_usd_mtok=q.input_usd_mtok,
                output_usd_mtok=q.output_usd_mtok,
                cache_read_usd_mtok=q.cache_read_usd_mtok,
                cache_write_usd_mtok=q.cache_write_usd_mtok,
                context_length=q.context_length,
                venue_type=self.venue_type,
                tps=q.tps,
                source_url=q.source_ref or "",
                notes=q.notes,
                timestamp=ts,
            ))

        logger.debug(f"StaticRatecard [{self.name}]: loaded {len(quotes)} quotes")
        return quotes
