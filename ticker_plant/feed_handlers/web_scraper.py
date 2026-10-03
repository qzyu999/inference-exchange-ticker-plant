"""Generic Web / JSON Scraper Feed Handler.

Extracts price quotes from arbitrary JSON endpoints or web APIs using simple selectors.
"""

from __future__ import annotations

import logging
import httpx
from ticker_plant.feed_handlers.base import BaseFeedHandler
from ticker_plant.models import PriceQuote

logger = logging.getLogger(__name__)


class WebScraperFeedHandler(BaseFeedHandler):
    """Feed handler for arbitrary web/API endpoints."""

    async def fetch_quotes(self) -> list[PriceQuote]:
        url = self.spec.endpoint
        if not url:
            return []

        quotes: list[PriceQuote] = []
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, headers=self.spec.headers)
                if resp.status_code != 200:
                    logger.warning(f"WebScraper [{self.name}] HTTP {resp.status_code} from {url}")
                    return quotes
                data = resp.json()
        except Exception as e:
            logger.warning(f"WebScraper [{self.name}] fetch failed: {e}")
            return quotes

        # If data is a list of models or dict with 'models'/'data'
        items = data if isinstance(data, list) else data.get("models", data.get("data", []))
        norm = self.spec.normalizer

        for item in items:
            if not isinstance(item, dict):
                continue
            model_id = str(item.get(norm.model_id_path, item.get("name", "")) or "")
            if not model_id:
                continue

            try:
                inp_price = float(item.get("input_price", item.get("prompt_price", 0.0)) or 0.0)
                out_price = float(item.get("output_price", item.get("completion_price", 0.0)) or 0.0)
            except (ValueError, TypeError):
                continue

            if inp_price <= 0 and out_price <= 0:
                continue

            # Convert if in per-token units
            if norm.price_unit == "usd_per_token":
                inp_price *= 1_000_000
                out_price *= 1_000_000

            quotes.append(PriceQuote(
                venue=self.name,
                raw_model_id=model_id,
                input_usd_mtok=round(inp_price, 4),
                output_usd_mtok=round(out_price, 4),
                venue_type=self.venue_type,
                source_url=url,
            ))

        return quotes
