"""Kubernetes-style declarative manifest parser and validator.

Supports:
- kind: FeedHandler
- kind: InstrumentMapping
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Literal
from pydantic import BaseModel, Field, model_validator
import yaml


API_VERSION = "tickerplant.inference.exchange/v1alpha1"


# ─── FeedHandler Manifest Models ───────────────────────────────

class PricingMappingSpec(BaseModel):
    """Declarative path mapping for price components and unit conversion."""
    prompt_path: str = "pricing.prompt"
    completion_path: str = "pricing.completion"
    cache_read_path: str = "pricing.input_cache_read"
    cache_write_path: str = "pricing.input_cache_write"
    unit: Literal["usd_per_token", "usd_per_mtok", "usd_per_ktok", "cent_per_mtok", "cent_per_token"] = "usd_per_token"


class AttributeMappingSpec(BaseModel):
    """Declarative path mapping for model attributes and SLA metrics."""
    context_length_path: str = "context_length"
    quantization_path: str = "quantization"
    max_completion_tokens_path: str = "max_completion_tokens"
    uptime_path: str = "uptime_last_1d"
    tps_path: str = "tps"
    latency_path: str = "latency"
    notes_path: str = "name"


class NormalizerSpec(BaseModel):
    """How to parse price units, model IDs, and attributes from API payloads."""
    items_path: str = "data"
    model_id_path: str = "id"
    pricing: PricingMappingSpec = Field(default_factory=PricingMappingSpec)
    attributes: AttributeMappingSpec = Field(default_factory=AttributeMappingSpec)

    # Legacy flat fields compatibility
    price_unit: str | None = None
    input_price_path: str | None = None
    output_price_path: str | None = None
    cache_read_path: str | None = None
    cache_write_path: str | None = None
    context_length_path: str | None = None

    @model_validator(mode="after")
    def sync_legacy(self) -> NormalizerSpec:
        if self.price_unit:
            self.pricing.unit = self.price_unit  # type: ignore
        if self.input_price_path:
            self.pricing.prompt_path = self.input_price_path
        if self.output_price_path:
            self.pricing.completion_path = self.output_price_path
        if self.cache_read_path:
            self.pricing.cache_read_path = self.cache_read_path
        if self.cache_write_path:
            self.pricing.cache_write_path = self.cache_write_path
        if self.context_length_path:
            self.attributes.context_length_path = self.context_length_path
        return self


class SubResourceSpec(BaseModel):
    """Sub-resource URL expansion template for parent-child API models."""
    url_template: str
    items_path: str = "data.endpoints"
    concurrency: int = 8


class UnbundleSpec(BaseModel):
    """Declarative unbundling specification to expand multi-host aggregator endpoints."""
    enabled: bool = True
    mode: Literal["sub_resource", "nested_array", "key_value_map"] = "sub_resource"
    sub_resource: SubResourceSpec | None = None
    items_path: str = "endpoints"
    venue_path: str = "provider_name"
    venue_type_map: dict[str, str] = Field(default_factory=dict)
    model_patterns: list[str] = Field(default_factory=lambda: ["*"])
    max_sub_resources: int = 100


class FilterRuleSpec(BaseModel):
    """Declarative quote filter rule."""
    path: str
    operator: Literal["gt", "gte", "lt", "lte", "eq", "ne", "in", "contains"] = "eq"
    value: Any = None


class CollectorSpec(BaseModel):
    """Declarative REST HTTP collector specification."""
    driver: str = "rest-declarative"
    endpoint: str | None = None
    method: str = "GET"
    headers: dict[str, str] = Field(default_factory=dict)
    unbundle: UnbundleSpec | None = None


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
        "rest-declarative",
        "openrouter-endpoints",
        "openai-compatible",
        "static-ratecard",
        "web-scraper",
        "litellm-archive",
    ] = "static-ratecard"
    collector: CollectorSpec | None = None
    catalog_endpoint: str | None = None
    endpoint: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    normalizer: NormalizerSpec = Field(default_factory=NormalizerSpec)
    filters: list[FilterRuleSpec] = Field(default_factory=list)
    poll_interval: str = "30m"
    active: bool = True
    quotes: list[StaticQuoteSpec] = Field(default_factory=list)

    @model_validator(mode="after")
    def sync_collector_defaults(self) -> FeedHandlerSpec:
        if not self.collector and (self.endpoint or self.catalog_endpoint):
            self.collector = CollectorSpec(
                driver=self.driver,
                endpoint=self.endpoint or self.catalog_endpoint,
                headers=self.headers,
            )
        elif self.collector:
            if not self.endpoint:
                self.endpoint = self.collector.endpoint
            if not self.headers:
                self.headers = self.collector.headers
            if self.collector.driver and self.driver == "static-ratecard":
                self.driver = self.collector.driver  # type: ignore
        return self


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
