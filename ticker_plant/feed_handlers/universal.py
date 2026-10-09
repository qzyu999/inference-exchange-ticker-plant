"""Universal Declarative Feed Handler.

100% declarative REST/HTTP collector driven by Kubernetes-style FeedHandler CRD specs.
Supports dot-notation path extraction, multi-venue unbundling, sub-resource expansion,
and pricing unit conversion without hardcoded vendor heuristics.
"""

from __future__ import annotations

import asyncio
import fnmatch
import logging
import os
import re
import time
from typing import Any
import httpx
from ticker_plant.feed_handlers.base import BaseFeedHandler
from ticker_plant.models import PriceQuote, VenueType

logger = logging.getLogger(__name__)


def _extract_path(obj: Any, path: str) -> Any:
    """Extract nested value by dot-notation, e.g. 'pricing.prompt' or 'data.endpoints'."""
    if not path or not obj:
        return None
    parts = path.split(".")
    curr = obj
    for part in parts:
        if isinstance(curr, dict):
            curr = curr.get(part)
        elif isinstance(curr, (list, tuple)) and part.isdigit():
            idx = int(part)
            curr = curr[idx] if idx < len(curr) else None
        else:
            return None
    return curr


def _expand_env_vars(val: str) -> str:
    """Expand ${VAR} or $VAR in header values."""
    pattern = re.compile(r"\$\{?([a-zA-Z_][a-zA-Z0-9_]*)\}?")
    return pattern.sub(lambda m: os.environ.get(m.group(1), ""), val)


def _convert_price(val: Any, unit: str) -> float:
    """Convert pricing value to standard $/Mtok."""
    try:
        fval = float(val or 0.0)
    except (ValueError, TypeError):
        return 0.0

    if fval <= 0:
        return 0.0

    if unit == "usd_per_token":
        return fval * 1_000_000.0
    elif unit == "usd_per_ktok":
        return fval * 1_000.0
    elif unit == "cent_per_mtok":
        return fval * 0.01
    elif unit == "cent_per_token":
        return fval * 10_000.0
    # Default is usd_per_mtok
    return fval


def _slugify_venue(
    venue_raw: str,
    venue_type_map: dict[str, str] | None = None,
    default_venue_type: str = VenueType.COMMODITY_GPU.value,
) -> tuple[str, str]:
    """Clean and normalize venue name and resolve venue type."""
    v_map = venue_type_map or {}
    clean_name = re.sub(r"[^a-zA-Z0-9_-]+", "-", venue_raw.strip().lower()).strip("-")
    if not clean_name:
        clean_name = "unknown"

    # Normalize common provider aliases
    aliases = {
        "amazon-bedrock": "bedrock",
        "amazon": "bedrock",
        "google-vertex": "vertex_ai",
        "google": "vertex_ai",
        "together-ai": "together",
        "fireworks-ai": "fireworks",
    }
    clean_name = aliases.get(clean_name, clean_name)

    # Resolve venue type
    v_type = v_map.get(clean_name)
    if not v_type:
        if clean_name in ("groq", "cerebras", "sambanova"):
            v_type = VenueType.ASIC_LPU.value
        elif clean_name in ("openai", "anthropic", "deepseek"):
            v_type = VenueType.FRONTIER_LAB.value
        elif clean_name in ("openrouter", "portkey", "litellm"):
            v_type = VenueType.AGGREGATOR.value
        else:
            v_type = v_map.get("default", default_venue_type)

    return clean_name, v_type


def _matches_pattern(model_id: str, patterns: list[str]) -> bool:
    """Check if model ID matches any of the glob patterns."""
    if not patterns or "*" in patterns:
        return True
    return any(fnmatch.fnmatch(model_id.lower(), p.lower()) for p in patterns)


def _eval_filter(obj: Any, rule: Any) -> bool:
    """Evaluate a declarative filter rule against an object."""
    val = _extract_path(obj, rule.path)
    target = rule.value
    op = rule.operator

    try:
        if op == "gt":
            return float(val or 0.0) > float(target)
        elif op == "gte":
            return float(val or 0.0) >= float(target)
        elif op == "lt":
            return float(val or 0.0) < float(target)
        elif op == "lte":
            return float(val or 0.0) <= float(target)
        elif op == "eq":
            return str(val).lower() == str(target).lower()
        elif op == "ne":
            return str(val).lower() != str(target).lower()
        elif op == "contains":
            return str(target).lower() in str(val).lower()
        elif op == "in":
            return str(val) in target
    except (ValueError, TypeError):
        return False
    return True


class UniversalFeedHandler(BaseFeedHandler):
    """Universal Declarative Feed Handler."""

    async def fetch_quotes(self) -> list[PriceQuote]:
        collector = self.spec.collector
        endpoint = (collector.endpoint if collector else None) or self.spec.endpoint or self.spec.catalog_endpoint
        if not endpoint:
            logger.warning(f"Venue [{self.name}] has no endpoint defined")
            return await self._fallback_quotes()

        headers = {k: _expand_env_vars(v) for k, v in (collector.headers if collector else self.spec.headers).items()}

        # If Authorization header is empty or has no token (e.g. "Bearer "), omit it for public endpoints
        if "Authorization" in headers:
            auth_token = headers["Authorization"].strip().replace("Bearer", "").strip()
            if not auth_token:
                del headers["Authorization"]

        unbundle = collector.unbundle if collector else None
        norm = self.spec.normalizer

        data = None
        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                resp = await client.get(endpoint, headers=headers)
                if resp.status_code != 200:
                    logger.warning(f"Venue [{self.name}] HTTP {resp.status_code} from {endpoint}")
                    return await self._fallback_quotes()
                data = resp.json()
        except Exception as e:
            logger.warning(f"Venue [{self.name}] HTTP fetch error: {e}")
            return await self._fallback_quotes()

        if not data:
            return await self._fallback_quotes()

        quotes: list[PriceQuote] = []

        # ── Mode A: Key-Value Map (e.g. LiteLLM pricing database) ──
        if unbundle and unbundle.enabled and unbundle.mode == "key_value_map" and isinstance(data, dict):
            quotes = self._extract_key_value_map(data, unbundle, norm)

        # ── Mode B: Sub-Resource Expansion (e.g. OpenRouter /models/{id}/endpoints) ──
        elif unbundle and unbundle.enabled and unbundle.mode == "sub_resource" and unbundle.sub_resource:
            quotes = await self._extract_sub_resource(data, unbundle, norm, headers)

        # ── Mode C: Nested Array Unbundling ──
        elif unbundle and unbundle.enabled and unbundle.mode == "nested_array":
            quotes = self._extract_nested_array(data, unbundle, norm)

        # ── Mode D: Standard Direct List ──
        else:
            quotes = self._extract_standard_list(data, norm)

        # Apply declarative filters
        if self.spec.filters:
            quotes = [q for q in quotes if all(self._eval_quote_filter(q, f) for f in self.spec.filters)]

        logger.info(f"Venue [{self.name}]: extracted {len(quotes)} quotes (unbundled={bool(unbundle and unbundle.enabled)})")
        return quotes

    def _extract_standard_list(self, data: Any, norm: Any) -> list[PriceQuote]:
        """Extract quotes from a standard list of model objects."""
        items = _extract_path(data, norm.items_path) if norm.items_path else data
        if not isinstance(items, list):
            items = data.get("data", data.get("models", [])) if isinstance(data, dict) else []

        quotes = []
        for item in items:
            q = self._quote_from_object(item, norm, venue=self.name, venue_type=self.venue_type)
            if q:
                quotes.append(q)
        return quotes

    def _extract_nested_array(self, data: Any, unbundle: Any, norm: Any) -> list[PriceQuote]:
        """Extract quotes from parent items containing nested child endpoints."""
        items = _extract_path(data, norm.items_path) if norm.items_path else data
        if not isinstance(items, list):
            items = []

        quotes = []
        for item in items:
            parent_id = str(_extract_path(item, norm.model_id_path) or "")
            children = _extract_path(item, unbundle.items_path)
            if isinstance(children, list) and children:
                for child in children:
                    v_raw = str(_extract_path(child, unbundle.venue_path) or self.name)
                    v_clean, v_type = _slugify_venue(v_raw, unbundle.venue_type_map, self.venue_type)
                    q = self._quote_from_object(child, norm, venue=v_clean, venue_type=v_type, model_id_override=parent_id)
                    if q:
                        quotes.append(q)
            else:
                # Parent fallback
                q = self._quote_from_object(item, norm, venue=self.name, venue_type=self.venue_type)
                if q:
                    quotes.append(q)
        return quotes

    def _extract_key_value_map(self, data: dict, unbundle: Any, norm: Any) -> list[PriceQuote]:
        """Extract quotes from a key-value dictionary (e.g. LiteLLM registry)."""
        quotes = []
        now = time.time()
        for model_key, meta in data.items():
            if not isinstance(meta, dict) or model_key == "sample_spec":
                continue
            v_raw = str(_extract_path(meta, unbundle.venue_path) or self.name)
            if not v_raw or v_raw == "unknown":
                v_raw = self.name
            v_clean, v_type = _slugify_venue(v_raw, unbundle.venue_type_map, self.venue_type)

            inp_val = _extract_path(meta, norm.pricing.prompt_path)
            out_val = _extract_path(meta, norm.pricing.completion_path)
            cache_read_val = _extract_path(meta, norm.pricing.cache_read_path) or 0.0

            inp_p = _convert_price(inp_val, norm.pricing.unit)
            out_p = _convert_price(out_val, norm.pricing.unit)
            cache_p = _convert_price(cache_read_val, norm.pricing.unit)

            if inp_p <= 0 and out_p <= 0:
                continue

            ctx_len = int(_extract_path(meta, norm.attributes.context_length_path) or 0)

            quotes.append(PriceQuote(
                venue=v_clean,
                raw_model_id=model_key,
                input_usd_mtok=round(inp_p, 4),
                output_usd_mtok=round(out_p, 4),
                cache_read_usd_mtok=round(cache_p, 4),
                context_length=ctx_len,
                venue_type=v_type,
                source_url=f"https://catalog/{v_clean}/{model_key}",
                notes=f"Registry rate-card via {self.name}",
                timestamp=now,
            ))
        return quotes

    async def _extract_sub_resource(self, data: Any, unbundle: Any, norm: Any, headers: dict) -> list[PriceQuote]:
        """Concurrently fetch sub-resource endpoints for matching parent models."""
        sub_spec = unbundle.sub_resource
        items = _extract_path(data, norm.items_path) if norm.items_path else data
        if not isinstance(items, list):
            items = data.get("data", []) if isinstance(data, dict) else []

        semaphore = asyncio.Semaphore(sub_spec.concurrency)
        quotes: list[PriceQuote] = []
        now = time.time()

        # Identify items to expand
        to_expand = []
        fallback_items = []

        expanded_count = 0
        for item in items:
            model_id = str(_extract_path(item, norm.model_id_path) or "")
            if not model_id:
                continue

            if (
                _matches_pattern(model_id, unbundle.model_patterns)
                and expanded_count < unbundle.max_sub_resources
            ):
                to_expand.append(item)
                expanded_count += 1
            else:
                fallback_items.append(item)

        # Process fallback items directly
        for item in fallback_items:
            q = self._quote_from_object(item, norm, venue=self.name, venue_type=self.venue_type)
            if q:
                quotes.append(q)

        # Concurrently fetch sub-resources
        async with httpx.AsyncClient(timeout=15.0) as client:
            async def fetch_child(parent_item: dict) -> list[PriceQuote]:
                mid = str(_extract_path(parent_item, norm.model_id_path) or "")
                url = sub_spec.url_template.format(id=mid)
                child_quotes = []

                try:
                    async with semaphore:
                        r = await client.get(url, headers=headers)
                        if r.status_code == 200:
                            child_data = r.json()
                            endpoints = _extract_path(child_data, sub_spec.items_path) or []
                            if isinstance(endpoints, list) and endpoints:
                                for ep in endpoints:
                                    v_raw = str(_extract_path(ep, unbundle.venue_path) or self.name)
                                    v_clean, v_type = _slugify_venue(v_raw, unbundle.venue_type_map, self.venue_type)
                                    cq = self._quote_from_object(
                                        ep,
                                        norm,
                                        venue=v_clean,
                                        venue_type=v_type,
                                        model_id_override=mid,
                                        source_url=url,
                                    )
                                    if cq:
                                        child_quotes.append(cq)
                except Exception as ex:
                    logger.debug(f"Sub-resource fetch failed for {mid}: {ex}")

                # If child quotes are empty, fallback to parent quote
                if not child_quotes:
                    pq = self._quote_from_object(parent_item, norm, venue=self.name, venue_type=self.venue_type)
                    if pq:
                        child_quotes.append(pq)
                return child_quotes

            sub_results = await asyncio.gather(*[fetch_child(item) for item in to_expand], return_exceptions=True)
            for res in sub_results:
                if isinstance(res, list):
                    quotes.extend(res)

        return quotes

    def _quote_from_object(
        self,
        obj: dict,
        norm: Any,
        venue: str,
        venue_type: str,
        model_id_override: str | None = None,
        source_url: str = "",
    ) -> PriceQuote | None:
        """Parse a single PriceQuote from a JSON mapping object."""
        model_id = model_id_override or str(_extract_path(obj, norm.model_id_path) or "")
        if not model_id:
            return None

        inp_val = _extract_path(obj, norm.pricing.prompt_path)
        out_val = _extract_path(obj, norm.pricing.completion_path)
        cache_read_val = _extract_path(obj, norm.pricing.cache_read_path) or 0.0
        cache_write_val = _extract_path(obj, norm.pricing.cache_write_path) or 0.0
        ctx_val = _extract_path(obj, norm.attributes.context_length_path) or 0
        tps_val = _extract_path(obj, norm.attributes.tps_path)
        notes_val = str(_extract_path(obj, norm.attributes.notes_path) or "")

        inp_p = _convert_price(inp_val, norm.pricing.unit)
        out_p = _convert_price(out_val, norm.pricing.unit)
        cache_r = _convert_price(cache_read_val, norm.pricing.unit)
        cache_w = _convert_price(cache_write_val, norm.pricing.unit)

        if inp_p <= 0 and out_p <= 0:
            return None

        try:
            ctx_len = int(ctx_val or 0)
        except (ValueError, TypeError):
            ctx_len = 0

        tps_float = None
        if tps_val is not None:
            try:
                tps_float = float(tps_val)
            except (ValueError, TypeError):
                tps_float = None

        return PriceQuote(
            venue=venue,
            raw_model_id=model_id,
            input_usd_mtok=round(inp_p, 4),
            output_usd_mtok=round(out_p, 4),
            cache_read_usd_mtok=round(cache_r, 4),
            cache_write_usd_mtok=round(cache_w, 4),
            context_length=ctx_len,
            venue_type=venue_type,
            tps=tps_float,
            source_url=source_url or f"https://catalog/{venue}/{model_id}",
            notes=notes_val or f"{venue} endpoint",
        )

    def _eval_quote_filter(self, q: PriceQuote, rule: Any) -> bool:
        """Evaluate declarative filter rule against a PriceQuote."""
        val = getattr(q, rule.path, None)
        if val is None:
            return True
        try:
            if rule.operator == "gt":
                return float(val) > float(rule.value)
            elif rule.operator == "gte":
                return float(val) >= float(rule.value)
            elif rule.operator == "lt":
                return float(val) < float(rule.value)
            elif rule.operator == "lte":
                return float(val) <= float(rule.value)
            elif rule.operator == "eq":
                return str(val) == str(rule.value)
            elif rule.operator == "ne":
                return str(val) != str(rule.value)
        except (ValueError, TypeError):
            return False
        return True

    async def _fallback_quotes(self) -> list[PriceQuote]:
        """Return static quotes defined on the manifest if live endpoint fails."""
        if self.spec.quotes:
            from ticker_plant.feed_handlers.static_ratecard import StaticRatecardFeedHandler
            return await StaticRatecardFeedHandler(self.manifest).fetch_quotes()
        return []
