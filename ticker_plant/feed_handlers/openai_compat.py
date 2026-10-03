"""Generic OpenAI-Compatible Feed Handler.

Connects to any provider implementing standard /v1/models or custom JSON endpoints.
Uses normalizer rules defined in the YAML manifest to extract pricing and model attributes.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any
import httpx
from ticker_plant.feed_handlers.base import BaseFeedHandler
from ticker_plant.models import PriceQuote

logger = logging.getLogger(__name__)


def _extract_path(obj: Any, path: str) -> Any:
    """Extract nested value by dot-notation, e.g. 'pricing.prompt'."""
    parts = path.split(".")
    curr = obj
    for part in parts:
        if isinstance(curr, dict):
            curr = curr.get(part)
        else:
            return None
    return curr


def _expand_env_vars(val: str) -> str:
    """Expand ${VAR} or $VAR in header values."""
    pattern = re.compile(r"\$\{?([a-zA-Z_][a-zA-Z0-9_]*)\}?")
    return pattern.sub(lambda m: os.environ.get(m.group(1), ""), val)


class OpenAICompatibleFeedHandler(BaseFeedHandler):
    """Feed handler for OpenAI-compatible REST endpoints."""

    async def fetch_quotes(self) -> list[PriceQuote]:
        url = self.spec.endpoint
        if not url:
            logger.warning(f"Venue [{self.name}] has no endpoint defined")
            return []

        # Expand environment variables in headers (e.g. Bearer ${API_KEY})
        headers = {k: _expand_env_vars(v) for k, v in self.spec.headers.items()}
        # If an Authorization header has an empty token, skip making the request if auth is strictly required
        if "Authorization" in headers and not headers["Authorization"].strip().split()[-1]:
            logger.debug(f"Venue [{self.name}] missing API token in environment, skipping live call")
            # If static fallback quotes are defined, return those
            if self.spec.quotes:
                from ticker_plant.feed_handlers.static_ratecard import StaticRatecardFeedHandler
                return await StaticRatecardFeedHandler(self.manifest).fetch_quotes()
            return []

        norm = self.spec.normalizer
        quotes: list[PriceQuote] = []

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code != 200:
                    logger.warning(f"Venue [{self.name}] HTTP {resp.status_code} from {url}")
                    if self.spec.quotes:
                        from ticker_plant.feed_handlers.static_ratecard import StaticRatecardFeedHandler
                        return await StaticRatecardFeedHandler(self.manifest).fetch_quotes()
                    return []
                data = resp.json()
        except Exception as e:
            logger.warning(f"Venue [{self.name}] fetch error: {e}")
            if self.spec.quotes:
                from ticker_plant.feed_handlers.static_ratecard import StaticRatecardFeedHandler
                return await StaticRatecardFeedHandler(self.manifest).fetch_quotes()
            return []

        models_list = data if isinstance(data, list) else data.get("data", data.get("models", []))

        unit_multiplier = 1.0
        if norm.price_unit == "usd_per_token":
            unit_multiplier = 1_000_000.0
        elif norm.price_unit == "usd_per_ktok":
            unit_multiplier = 1_000.0
        elif norm.price_unit == "cent_per_mtok":
            unit_multiplier = 0.01

        for m in models_list:
            model_id = str(_extract_path(m, norm.model_id_path) or "")
            if not model_id:
                continue

            inp_val = _extract_path(m, norm.input_price_path)
            out_val = _extract_path(m, norm.output_price_path)
            cache_read_val = _extract_path(m, norm.cache_read_path) or 0.0
            cache_write_val = _extract_path(m, norm.cache_write_path) or 0.0
            ctx_val = _extract_path(m, norm.context_length_path) or 0

            try:
                inp_price = float(inp_val or 0.0) * unit_multiplier
                out_price = float(out_val or 0.0) * unit_multiplier
                cache_read = float(cache_read_val or 0.0) * unit_multiplier
                cache_write = float(cache_write_val or 0.0) * unit_multiplier
                ctx_len = int(ctx_val or 0)
            except (ValueError, TypeError):
                continue

            if inp_price <= 0 and out_price <= 0:
                continue

            quotes.append(PriceQuote(
                venue=self.name,
                raw_model_id=model_id,
                input_usd_mtok=round(inp_price, 4),
                output_usd_mtok=round(out_price, 4),
                cache_read_usd_mtok=round(cache_read, 4),
                cache_write_usd_mtok=round(cache_write, 4),
                context_length=ctx_len,
                venue_type=self.venue_type,
                source_url=url,
            ))

        logger.info(f"OpenAICompatible [{self.name}]: extracted {len(quotes)} quotes")
        return quotes
