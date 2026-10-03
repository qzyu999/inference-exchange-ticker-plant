"""Domain models for the Inference Exchange Ticker Plant.

Modeled on traditional financial exchange symbology and market data concepts.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class VenueType(str, Enum):
    """Categorization of execution venue / provider."""
    ASIC_LPU = "asic-lpu"                # Groq, Cerebras, SambaNova
    COMMODITY_GPU = "commodity-gpu"      # DeepInfra, Together, Fireworks, Nebius, Novita, Chutes
    FRONTIER_LAB = "frontier-lab"        # OpenAI, Anthropic, Google, DeepSeek
    AGGREGATOR = "aggregator"            # OpenRouter, Portkey, LiteLLM
    COMMUNITY = "community"              # Decentralized / Twitter drops / Discord clusters


@dataclass
class PriceQuote:
    """Raw unmapped price quote extracted by a feed handler."""
    venue: str
    raw_model_id: str
    input_usd_mtok: float
    output_usd_mtok: float
    cache_read_usd_mtok: float = 0.0
    cache_write_usd_mtok: float = 0.0
    context_length: int = 0
    venue_type: str = VenueType.COMMODITY_GPU.value
    tps: float | None = None
    ttft_ms: float | None = None
    source_url: str = ""
    notes: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class TapeTick:
    """The fundamental atom of the Consolidated Tape.

    A normalized, timestamped price quote for a canonical instrument.
    """
    tick_id: str
    timestamp: float
    iso_time: str
    venue: str
    venue_type: str
    raw_model_id: str
    instrument: str                      # Canonical key (e.g. LLAMA-3.1-70B)
    input_usd_mtok: float                # $/Mtok prompt
    output_usd_mtok: float               # $/Mtok completion
    cache_read_usd_mtok: float = 0.0     # $/Mtok cache read
    cache_write_usd_mtok: float = 0.0    # $/Mtok cache write
    context_length: int = 0
    tps: float | None = None
    ttft_ms: float | None = None
    source_url: str = ""
    notes: str = ""

    @classmethod
    def from_quote(cls, quote: PriceQuote, instrument: str) -> TapeTick:
        now_ts = quote.timestamp or time.time()
        iso = datetime.fromtimestamp(now_ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return cls(
            tick_id=uuid.uuid4().hex[:16],
            timestamp=now_ts,
            iso_time=iso,
            venue=quote.venue,
            venue_type=quote.venue_type,
            raw_model_id=quote.raw_model_id,
            instrument=instrument,
            input_usd_mtok=round(quote.input_usd_mtok, 4),
            output_usd_mtok=round(quote.output_usd_mtok, 4),
            cache_read_usd_mtok=round(quote.cache_read_usd_mtok, 4),
            cache_write_usd_mtok=round(quote.cache_write_usd_mtok, 4),
            context_length=quote.context_length,
            tps=quote.tps,
            ttft_ms=quote.ttft_ms,
            source_url=quote.source_url,
            notes=quote.notes,
        )


@dataclass
class BestBidOffer:
    """Top of book (BBO) for a canonical instrument across all venues."""
    instrument: str
    cheapest_output_venue: str
    cheapest_output_price: float
    cheapest_input_venue: str
    cheapest_input_price: float
    highest_output_venue: str
    highest_output_price: float
    venue_count: int
    median_output_price: float
    spread_pct: float                    # (highest - lowest) / lowest * 100
    last_updated: str


@dataclass
class DepthEntry:
    """A single venue offer in the market depth book."""
    venue: str
    venue_type: str
    raw_model_id: str
    input_usd_mtok: float
    output_usd_mtok: float
    cache_read_usd_mtok: float
    context_length: int
    tps: float | None
    age_hours: float
