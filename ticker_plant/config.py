"""Kubernetes-style declarative manifest parser and validator.

Supports:
- kind: FeedHandler
- kind: InstrumentMapping
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Literal
from pydantic import BaseModel, Field
import yaml


API_VERSION = "tickerplant.inference.exchange/v1alpha1"


# ─── FeedHandler Manifest Models ───────────────────────────────

class NormalizerSpec(BaseModel):
    """How to parse price units and model IDs from API payloads."""
    price_unit: Literal["usd_per_token", "usd_per_mtok", "usd_per_ktok", "cent_per_mtok"] = "usd_per_token"
    model_id_path: str = "id"
    input_price_path: str = "pricing.prompt"
    output_price_path: str = "pricing.completion"
    cache_read_path: str = "pricing.input_cache_read"
    cache_write_path: str = "pricing.input_cache_write"
    context_length_path: str = "context_length"


class StaticQuoteSpec(BaseModel):
    """A static rate-card quote inside a manifest."""
    instrument: str | None = None
    raw_model_id: str
    input_usd_mtok: float
    output_usd_mtok: float
    cache_read_usd_mtok: float = 0.0
    cache_write_usd_mtok: float = 0.0
    context_length: int = 0
    tps: float | None = None
    reported_at: str | None = None
    source_ref: str | None = None
    notes: str = ""


class FeedHandlerMetadata(BaseModel):
    name: str
    venue_type: str = "commodity-gpu"
    display_name: str | None = None
    tags: list[str] = Field(default_factory=list)


class FeedHandlerSpec(BaseModel):
    driver: Literal[
        "openrouter-endpoints",
        "openai-compatible",
        "static-ratecard",
        "web-scraper",
        "litellm-archive",
    ]
    catalog_endpoint: str | None = None
    endpoint: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    normalizer: NormalizerSpec = Field(default_factory=NormalizerSpec)
    poll_interval: str = "30m"
    active: bool = True
    quotes: list[StaticQuoteSpec] = Field(default_factory=list)


class FeedHandlerManifest(BaseModel):
    apiVersion: str = API_VERSION
    kind: Literal["FeedHandler"]
    metadata: FeedHandlerMetadata
    spec: FeedHandlerSpec


# ─── InstrumentMapping Manifest Models ─────────────────────────

class InstrumentDefinition(BaseModel):
    canonical_key: str              # e.g. LLAMA-3.1-70B
    display_name: str              # e.g. Meta Llama 3.1 70B Instruct
    family: str                    # e.g. llama
    aliases: list[str] = Field(default_factory=list)
    patterns: list[str] = Field(default_factory=list)

    def matches(self, raw_id: str) -> bool:
        """Check if a raw provider model ID matches this canonical instrument."""
        raw_clean = raw_id.strip().lower()
        if raw_clean == self.canonical_key.lower():
            return True
        for alias in self.aliases:
            if raw_clean == alias.strip().lower():
                return True
        for pattern in self.patterns:
            try:
                if re.search(pattern, raw_id, re.IGNORECASE):
                    return True
            except re.error:
                continue
        return False


class InstrumentMappingMetadata(BaseModel):
    name: str


class InstrumentMappingSpec(BaseModel):
    instruments: list[InstrumentDefinition]


class InstrumentMappingManifest(BaseModel):
    apiVersion: str = API_VERSION
    kind: Literal["InstrumentMapping"]
    metadata: InstrumentMappingMetadata
    spec: InstrumentMappingSpec


# ─── Manifest Loader ───────────────────────────────────────────

class ManifestRegistry:
    """Discovers, validates, and indexes all manifests."""

    def __init__(self):
        self.feed_handlers: dict[str, FeedHandlerManifest] = {}
        self.instruments: dict[str, InstrumentDefinition] = {}

    def load_file(self, path: Path | str) -> Any:
        path = Path(path)
        with open(path, "r", encoding="utf-8") as f:
            docs = list(yaml.safe_load_all(f))

        loaded = []
        for doc in docs:
            if not isinstance(doc, dict):
                continue
            kind = doc.get("kind")
            if kind == "FeedHandler":
                manifest = FeedHandlerManifest.model_validate(doc)
                self.feed_handlers[manifest.metadata.name] = manifest
                loaded.append(manifest)
            elif kind == "InstrumentMapping":
                manifest = InstrumentMappingManifest.model_validate(doc)
                for inst in manifest.spec.instruments:
                    self.instruments[inst.canonical_key] = inst
                loaded.append(manifest)
        return loaded

    def load_directory(self, dir_path: Path | str) -> int:
        """Scan a directory recursively for all .yaml and .yml manifests."""
        dir_path = Path(dir_path)
        if not dir_path.exists():
            return 0
        count = 0
        for yaml_file in sorted(dir_path.glob("**/*.y*ml")):
            items = self.load_file(yaml_file)
            count += len(items)
        return count

    def resolve_instrument(self, raw_model_id: str) -> str:
        """Resolve a raw provider model ID to its canonical instrument key.

        Falls back to normalized raw_id if no matching alias or pattern exists.
        """
        for key, inst in self.instruments.items():
            if inst.matches(raw_model_id):
                return key

        # Fallback: clean up raw model ID into uppercase slug
        cleaned = re.sub(r"^[^/]+/", "", raw_model_id)  # strip namespace
        cleaned = re.sub(r"[-_.]instruct$", "", cleaned, flags=re.IGNORECASE)
        return cleaned.upper()
