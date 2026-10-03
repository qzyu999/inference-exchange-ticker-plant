"""OpenRouter Feed Handler.

Fetches public market models from OpenRouter. Unbundles model pricing
and translates prices to $/Mtok.
"""

from __future__ import annotations

import logging
import httpx
from ticker_plant.feed_handlers.base import BaseFeedHandler
from ticker_plant.models import PriceQuote, VenueType

logger = logging.getLogger(__name__)

DEFAULT_OR_CATALOG = "https://openrouter.ai/api/v1/models"


class OpenRouterFeedHandler(BaseFeedHandler):
    """Feed handler for OpenRouter public catalog and endpoints."""

    async def fetch_quotes(self) -> list[PriceQuote]:
        url = self.spec.catalog_endpoint or DEFAULT_OR_CATALOG
        headers = dict(self.spec.headers)

        data = None
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json().get("data", [])
                else:
                    logger.warning(f"OpenRouter HTTP {resp.status_code} from {url}")
        except Exception as e:
            logger.warning(f"OpenRouter fetch failed: {e}")

        if not data:
            return []

        quotes: list[PriceQuote] = []
        for m in data:
            model_id = m.get("id", "")
            pricing = m.get("pricing", {})
            if not pricing:
                continue

            try:
                prompt_unit = float(pricing.get("prompt", "0") or "0")
                completion_unit = float(pricing.get("completion", "0") or "0")
                if prompt_unit <= 0 and completion_unit <= 0:
                    continue

                cache_read_unit = float(pricing.get("input_cache_read", "0") or "0")
                cache_write_unit = float(pricing.get("input_cache_write", "0") or "0")

                # OpenRouter returns prices per single token -> multiply by 1,000,000 for Mtok
                input_mtok = prompt_unit * 1_000_000
                output_mtok = completion_unit * 1_000_000
                cache_read_mtok = cache_read_unit * 1_000_000
                cache_write_mtok = cache_write_unit * 1_000_000

                quotes.append(PriceQuote(
                    venue=self.name,
                    raw_model_id=model_id,
                    input_usd_mtok=input_mtok,
                    output_usd_mtok=output_mtok,
                    cache_read_usd_mtok=cache_read_mtok,
                    cache_write_usd_mtok=cache_write_mtok,
                    context_length=m.get("context_length", 0) or 0,
                    venue_type=VenueType.AGGREGATOR.value,
                    source_url=f"https://openrouter.ai/{model_id}",
                    notes=m.get("name", ""),
                ))
            except (ValueError, TypeError):
                continue

        logger.info(f"OpenRouter: extracted {len(quotes)} quotes")
        return quotes
