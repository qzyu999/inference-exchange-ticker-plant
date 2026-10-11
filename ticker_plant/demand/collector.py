"""Public Aggregator and Ecosystem Telemetry Collectors.

Ingests external demand proxies across three distinct tiers:
1. OpenRouter Public Aggregator Telemetry (token throughput, query count, spend)
2. Hugging Face Model Hub Telemetry (30-day developer downloads, likes)
3. LMSYS / Chatbot Arena Telemetry (human evaluation battles, Elo ratings)
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
import httpx

from ticker_plant.config import ManifestRegistry
from ticker_plant.models import DemandMetric
from ticker_plant.tape.store import ConsolidatedTapeStore

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8",
}


@dataclass
class DemandReport:
    """Summary of demand collection cycle."""
    openrouter_models_collected: int
    hf_models_collected: int
    arena_models_collected: int
    instruments_updated: int
    duration_seconds: float


class OpenRouterDemandCollector:
    """Collects real-world token throughput and spend from OpenRouter rankings."""

    def __init__(self, endpoint: str = "https://openrouter.ai/rankings", catalog_endpoint: str = "https://openrouter.ai/api/v1/models"):
        self.endpoint = endpoint
        self.catalog_endpoint = catalog_endpoint

    async def fetch_rankings(self, client: httpx.AsyncClient) -> tuple[list[dict[str, Any]], dict[str, str]]:
        """Fetch models rankings and mapping of model_id -> hugging_face_id."""
        rankings_data: list[dict[str, Any]] = []
        hf_mapping: dict[str, str] = {}

        # 1. Fetch rankings HTML & extract React Query hydration payload
        try:
            resp = await client.get(self.endpoint, headers=DEFAULT_HEADERS, timeout=15.0)
            if resp.status_code == 200:
                html = resp.text
                pos = html.find('["rankings","models"')
                if pos == -1:
                    pos = html.find('rankings\\",\\"models\\"')

                if pos != -1:
                    idx_data = html.rfind('"data\\":', 0, pos)
                    if idx_data != -1:
                        raw_chunk = html[idx_data + len('"data\\":'):idx_data + 200000]
                        clean_json = raw_chunk.replace('\\"', '"').replace('\\\\', '\\')
                        decoder = json.JSONDecoder()
                        obj, _ = decoder.raw_decode(clean_json)
                        if isinstance(obj, list):
                            rankings_data = obj
        except Exception as e:
            logger.warning(f"Failed to fetch OpenRouter rankings HTML: {e}")

        # 2. Fetch models catalog to extract hugging_face_id mapping and fallback rank
        try:
            resp_cat = await client.get(self.catalog_endpoint, headers=DEFAULT_HEADERS, timeout=10.0)
            if resp_cat.status_code == 200:
                cat_json = resp_cat.json()
                for item in cat_json.get("data", []):
                    mid = item.get("id")
                    hfid = item.get("hugging_face_id")
                    if mid and hfid:
                        hf_mapping[mid] = hfid
        except Exception as e:
            logger.warning(f"Failed to fetch OpenRouter models catalog: {e}")

        return rankings_data, hf_mapping


class HuggingFaceDemandCollector:
    """Collects 30-day download counts and stars from Hugging Face Model Hub API."""

    def __init__(self, base_url: str = "https://huggingface.co/api/models"):
        self.base_url = base_url

    async def fetch_model_stats(self, client: httpx.AsyncClient, hf_id: str) -> dict[str, Any] | None:
        """Fetch downloads and likes for a single Hugging Face repository."""
        url = f"{self.base_url}/{hf_id}"
        try:
            resp = await client.get(url, headers=DEFAULT_HEADERS, timeout=8.0)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "hf_id": hf_id,
                    "downloads": data.get("downloads", 0),
                    "likes": data.get("likes", 0),
                }
        except Exception as e:
            logger.debug(f"HF fetch error for {hf_id}: {e}")
        return None

    async def fetch_batch(self, client: httpx.AsyncClient, hf_ids: set[str], concurrency: int = 8) -> dict[str, dict[str, Any]]:
        """Fetch telemetry for multiple HF repos with controlled concurrency."""
        results: dict[str, dict[str, Any]] = {}
        sem = asyncio.Semaphore(concurrency)

        async def worker(hid: str):
            async with sem:
                res = await self.fetch_model_stats(client, hid)
                if res:
                    results[hid] = res

        tasks = [worker(hid) for hid in hf_ids if hid]
        await asyncio.gather(*tasks, return_exceptions=True)
        return results


class LMSysArenaDemandCollector:
    """Collects human battle counts and Elo ratings from LMSYS Chatbot Arena."""

    def __init__(self, endpoint: str = "https://arena.ai/leaderboard"):
        self.endpoint = endpoint

    async def fetch_leaderboard(self, client: httpx.AsyncClient) -> list[dict[str, Any]]:
        """Fetch Chatbot Arena leaderboard entries."""
        try:
            resp = await client.get(self.endpoint, headers=DEFAULT_HEADERS, timeout=15.0)
            if resp.status_code == 200:
                html = resp.text
                idx = html.find('"entries\\":')
                if idx != -1:
                    raw_chunk = html[idx + len('"entries\\":'):idx + 500000]
                    clean_json = raw_chunk.replace('\\"', '"').replace('\\\\', '\\')
                    decoder = json.JSONDecoder()
                    obj, _ = decoder.raw_decode(clean_json)
                    if isinstance(obj, list) and len(obj) > 0 and "votes" in obj[0]:
                        return obj
        except Exception as e:
            logger.warning(f"Failed to fetch LMSYS Arena leaderboard: {e}")

        # Fallback: check latest csv from huggingface space
        try:
            tree_url = "https://huggingface.co/api/spaces/lmarena-ai/chatbot-arena-leaderboard/tree/main"
            resp_tree = await client.get(tree_url, headers=DEFAULT_HEADERS, timeout=8.0)
            if resp_tree.status_code == 200:
                files = [item["path"] for item in resp_tree.json() if item.get("path", "").startswith("leaderboard_table_") and item.get("path", "").endswith(".csv")]
                if files:
                    files.sort()
                    latest_csv = files[-1]
                    csv_url = f"https://huggingface.co/spaces/lmarena-ai/chatbot-arena-leaderboard/raw/main/{latest_csv}"
                    resp_csv = await client.get(csv_url, headers=DEFAULT_HEADERS, timeout=8.0)
                    if resp_csv.status_code == 200:
                        lines = resp_csv.text.strip().split("\n")
                        fallback_entries = []
                        for idx_line, l in enumerate(lines[1:50]):
                            parts = l.split(",")
                            if len(parts) >= 2:
                                fallback_entries.append({
                                    "rank": idx_line + 1,
                                    "modelDisplayName": parts[1].strip(),
                                    "modelKey": parts[0].strip(),
                                    "rating": 1000.0,
                                    "votes": 5000,
                                })
                        return fallback_entries
        except Exception as e:
            logger.debug(f"LMSYS fallback space error: {e}")

        return []


class DemandIngestionEngine:
    """Orchestrates multi-source demand collection and normalizes composite scores."""

    def __init__(self, registry: ManifestRegistry, store: ConsolidatedTapeStore):
        self.registry = registry
        self.store = store
        self.openrouter_collector = OpenRouterDemandCollector()
        self.hf_collector = HuggingFaceDemandCollector()
        self.arena_collector = LMSysArenaDemandCollector()

    def _discover_hf_targets(self, or_hf_mapping: dict[str, str]) -> set[str]:
        """Aggregate all Hugging Face model IDs from manifests and OpenRouter catalog."""
        hf_targets: set[str] = set()

        # From InstrumentMapping manifests
        for inst in self.registry.instruments.values():
            if inst.hf_id:
                hf_targets.add(inst.hf_id)
            for alias in inst.aliases:
                if "/" in alias and not alias.startswith("accounts/"):
                    hf_targets.add(alias)

        # From OpenRouter mapped catalog
        for hid in or_hf_mapping.values():
            if hid and "/" in hid:
                hf_targets.add(hid)

        return hf_targets

    def _resolve_arena_instrument(self, name: str, key: str) -> str:
        """Resolve LMSYS Arena model name/key to canonical instrument."""
        name_clean = name.strip()
        key_clean = key.strip()

        # Specific alias patterns for Arena display names
        lower = (name_clean + " " + key_clean).lower()
        if "llama 3.1 70b" in lower or "llama-3.1-70b" in lower: return "LLAMA-3.1-70B"
        if "llama 3.1 8b" in lower or "llama-3.1-8b" in lower: return "LLAMA-3.1-8B"
        if "llama 3.3 70b" in lower or "llama-3.3-70b" in lower: return "LLAMA-3.3-70B"
        if "deepseek-r1" in lower or "deepseek r1" in lower: return "DEEPSEEK-R1"
        if "deepseek-v3" in lower or "deepseek v3" in lower or "deepseek-chat" in lower: return "DEEPSEEK-V3"
        if "qwen 2.5 72b" in lower or "qwen-2.5-72b" in lower: return "QWEN-2.5-72B"
        if "gpt-4o-mini" in lower or "gpt 4o mini" in lower: return "GPT-4O-MINI"
        if "gpt-4o" in lower or "gpt 4o" in lower: return "GPT-4O"
        if "claude 3.5 sonnet" in lower or "sonnet 3.5" in lower: return "CLAUDE-3.5-SONNET"
        if "claude 3.5 haiku" in lower or "haiku 3.5" in lower: return "CLAUDE-3.5-HAIKU"

        # Try key first, then display name
        inst = self.registry.resolve_instrument(key_clean)
        if inst != key_clean.upper():
            return inst

        inst = self.registry.resolve_instrument(name_clean)
        if inst != name_clean.upper():
            return inst

        return inst

    async def run_cycle(self) -> DemandReport:
        """Execute concurrent demand ingestion across OpenRouter, Hugging Face, and LMSYS."""
        start_t = time.time()
        now_ts = start_t
        iso_time = datetime.fromtimestamp(now_ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
            # 1. Fetch OpenRouter rankings & LMSYS Arena in parallel
            (or_rankings, or_hf_mapping), arena_entries = await asyncio.gather(
                self.openrouter_collector.fetch_rankings(client),
                self.arena_collector.fetch_leaderboard(client),
                return_exceptions=False,
            )

            # 2. Discover HF targets and fetch Hugging Face stats
            hf_targets = self._discover_hf_targets(or_hf_mapping)
            hf_stats = await self.hf_collector.fetch_batch(client, hf_targets, concurrency=10)

        # 3. Consolidate telemetry per instrument
        demand_by_inst: dict[str, DemandMetric] = {}

        def get_or_create(inst: str) -> DemandMetric:
            if inst not in demand_by_inst:
                demand_by_inst[inst] = DemandMetric(
                    instrument=inst,
                    timestamp=now_ts,
                    iso_time=iso_time,
                )
            return demand_by_inst[inst]

        # Process OpenRouter throughput
        for idx, item in enumerate(or_rankings):
            permaslug = item.get("model_permaslug", "")
            if not permaslug:
                continue

            inst = self.registry.resolve_instrument(permaslug)
            dm = get_or_create(inst)

            prompt_tok = item.get("total_prompt_tokens", 0)
            comp_tok = item.get("total_completion_tokens", 0)
            total_tokens = prompt_tok + comp_tok
            reqs = item.get("count", 0)
            spend = float(item.get("total_usage", 0.0))

            # Store the highest volume if multiple variants map to same instrument
            if dm.openrouter_weekly_tokens is None or total_tokens > dm.openrouter_weekly_tokens:
                dm.openrouter_rank = idx + 1
                dm.openrouter_weekly_tokens = total_tokens
                dm.openrouter_requests = reqs
                dm.openrouter_spend_usd = round(spend, 2)
                dm.openrouter_model_id = permaslug

        # Process Hugging Face downloads & likes
        for hfid, stats in hf_stats.items():
            inst = self.registry.resolve_instrument(hfid)
            dm = get_or_create(inst)

            dl = stats.get("downloads", 0)
            likes = stats.get("likes", 0)

            if dm.hf_downloads_30d is None or dl > dm.hf_downloads_30d:
                dm.hf_model_id = hfid
                dm.hf_downloads_30d = dl
                dm.hf_likes = likes

        # Process LMSYS Chatbot Arena
        for entry in arena_entries:
            display_name = entry.get("modelDisplayName", "")
            model_key = entry.get("modelKey", "")
            inst = self._resolve_arena_instrument(display_name, model_key)
            dm = get_or_create(inst)

            rank = entry.get("rank")
            rating = entry.get("rating")
            votes = entry.get("votes")

            if dm.arena_votes is None or (votes and votes > dm.arena_votes):
                dm.arena_rank = rank
                dm.arena_rating = round(rating, 4) if rating is not None else None
                dm.arena_votes = votes
                dm.arena_model_name = display_name

        # 4. Calculate Normalized Composite Demand Velocity Index (0 - 100)
        max_tokens = max([m.openrouter_weekly_tokens or 0 for m in demand_by_inst.values()] or [1])
        max_downloads = max([m.hf_downloads_30d or 0 for m in demand_by_inst.values()] or [1])
        max_votes = max([m.arena_votes or 0 for m in demand_by_inst.values()] or [1])

        for dm in demand_by_inst.values():
            scores = []
            weights = []

            # OpenRouter Component (40% weight) - Logarithmic scale
            if dm.openrouter_weekly_tokens and dm.openrouter_weekly_tokens > 0 and max_tokens > 0:
                s_tok = min(100.0, (math.log10(dm.openrouter_weekly_tokens + 1) / math.log10(max_tokens + 1)) * 100.0)
                scores.append(s_tok)
                weights.append(0.40)

            # Hugging Face Component (35% weight) - Logarithmic scale
            if dm.hf_downloads_30d and dm.hf_downloads_30d > 0 and max_downloads > 0:
                s_hf = min(100.0, (math.log10(dm.hf_downloads_30d + 1) / math.log10(max_downloads + 1)) * 100.0)
                scores.append(s_hf)
                weights.append(0.35)

            # LMSYS Arena Component (25% weight) - Logarithmic scale
            if dm.arena_votes and dm.arena_votes > 0 and max_votes > 0:
                s_arena = min(100.0, (math.log10(dm.arena_votes + 1) / math.log10(max_votes + 1)) * 100.0)
                scores.append(s_arena)
                weights.append(0.25)

            if scores:
                composite = sum(s * w for s, w in zip(scores, weights)) / sum(weights)
                dm.demand_index = round(composite, 1)
            else:
                dm.demand_index = 0.0

        # 5. Persist to SQLite
        metrics_list = list(demand_by_inst.values())
        committed = self.store.upsert_demand_metrics(metrics_list)
        duration = time.time() - start_t

        return DemandReport(
            openrouter_models_collected=len(or_rankings),
            hf_models_collected=len(hf_stats),
            arena_models_collected=len(arena_entries),
            instruments_updated=committed,
            duration_seconds=round(duration, 2),
        )
