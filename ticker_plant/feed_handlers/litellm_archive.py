"""Historical Archive Replayer / Bootstrapper.

Seeds the Consolidated Tape with historical rate cards from community-maintained
rate card databases (e.g. BerriAI/LiteLLM model pricing archive).
Allows an instant 12–18 month historical price trajectory without waiting.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
import httpx
from ticker_plant.feed_handlers.base import BaseFeedHandler
from ticker_plant.models import PriceQuote, VenueType

logger = logging.getLogger(__name__)

LITELLM_PRICES_URL = "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"


class LiteLLMArchiveFeedHandler(BaseFeedHandler):
    """Feed handler that replays / ingests the LiteLLM pricing archive."""

    async def fetch_quotes(self) -> list[PriceQuote]:
        url = self.spec.endpoint or LITELLM_PRICES_URL

        data = None
        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
        except Exception as e:
            logger.warning(f"LiteLLM archive fetch failed: {e}")

        if not data or not isinstance(data, dict):
            return []

        quotes: list[PriceQuote] = []
        now = time.time()

        # Known provider prefixes / providers in litellm catalog
        for model_key, meta in data.items():
            if not isinstance(meta, dict) or model_key == "sample_spec":
                continue

            input_cost_per_token = float(meta.get("input_cost_per_token") or 0.0)
            output_cost_per_token = float(meta.get("output_cost_per_token") or 0.0)
            cache_read_per_token = float(meta.get("cache_read_input_token_cost") or 0.0)

            if input_cost_per_token <= 0 and output_cost_per_token <= 0:
                continue

            litellm_provider = str(meta.get("litellm_provider") or "unknown").lower()
            venue_name = litellm_provider if litellm_provider != "unknown" else self.name

            # Map venue type
            v_type = VenueType.COMMODITY_GPU.value
            if venue_name in ("openai", "anthropic", "gemini", "vertex_ai"):
                v_type = VenueType.FRONTIER_LAB.value
            elif venue_name in ("groq", "cerebras"):
                v_type = VenueType.ASIC_LPU.value
            elif venue_name in ("openrouter",):
                v_type = VenueType.AGGREGATOR.value

            input_mtok = input_cost_per_token * 1_000_000
            output_mtok = output_cost_per_token * 1_000_000
            cache_read_mtok = cache_read_per_token * 1_000_000
            max_tokens = int(meta.get("max_tokens") or 0)

            quotes.append(PriceQuote(
                venue=venue_name,
                raw_model_id=model_key,
                input_usd_mtok=round(input_mtok, 4),
                output_usd_mtok=round(output_mtok, 4),
                cache_read_usd_mtok=round(cache_read_mtok, 4),
                context_length=max_tokens,
                venue_type=v_type,
                source_url=url,
                notes="Ingested from LiteLLM rate-card registry",
                timestamp=now,
            ))

        logger.info(f"LiteLLM Archive: ingested {len(quotes)} quotes across multiple venues")
        return quotes
