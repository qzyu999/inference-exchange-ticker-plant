"""Consolidated Tape analytics: BBO, market depth, and cross-venue spread calculations."""

from __future__ import annotations

import statistics
import time
from collections import defaultdict
from ticker_plant.models import BestBidOffer, DepthEntry
from ticker_plant.tape.store import ConsolidatedTapeStore


def get_bbo(store: ConsolidatedTapeStore, instrument: str | None = None) -> list[BestBidOffer]:
    """Calculate the Best Bid and Offer (top of book) for instruments.

    Finds the lowest price offer, highest price offer, venue count, median price,
    and cross-venue spread percentage across all competing venues.
    """
    ticks = store.get_latest_ticks_per_venue(instrument)
    by_inst: dict[str, list] = defaultdict(list)
    for t in ticks:
        by_inst[t.instrument].append(t)

    results: list[BestBidOffer] = []
    for inst, inst_ticks in sorted(by_inst.items()):
        # Sort by output price (primary pricing metric)
        valid_out = [t for t in inst_ticks if t.output_usd_mtok > 0]
        valid_in = [t for t in inst_ticks if t.input_usd_mtok > 0]
        if not valid_out:
            continue

        cheapest_out_tick = min(valid_out, key=lambda x: x.output_usd_mtok)
        highest_out_tick = max(valid_out, key=lambda x: x.output_usd_mtok)
        cheapest_in_tick = min(valid_in, key=lambda x: x.input_usd_mtok) if valid_in else cheapest_out_tick

        out_prices = [t.output_usd_mtok for t in valid_out]
        median_out = statistics.median(out_prices)
        spread_pct = 0.0
        if cheapest_out_tick.output_usd_mtok > 0:
            spread_pct = (
                (highest_out_tick.output_usd_mtok - cheapest_out_tick.output_usd_mtok)
                / cheapest_out_tick.output_usd_mtok
                * 100.0
            )

        results.append(BestBidOffer(
            instrument=inst,
            cheapest_output_venue=cheapest_out_tick.venue,
            cheapest_output_price=cheapest_out_tick.output_usd_mtok,
            cheapest_input_venue=cheapest_in_tick.venue,
            cheapest_input_price=cheapest_in_tick.input_usd_mtok,
            highest_output_venue=highest_out_tick.venue,
            highest_output_price=highest_out_tick.output_usd_mtok,
            venue_count=len(inst_ticks),
            median_output_price=round(median_out, 4),
            spread_pct=round(spread_pct, 1),
            last_updated=cheapest_out_tick.iso_time,
        ))

    return results


def get_depth(store: ConsolidatedTapeStore, instrument: str) -> list[DepthEntry]:
    """Calculate the Level 2 market depth book for a single instrument across venues."""
    ticks = store.get_latest_ticks_per_venue(instrument)
    now = time.time()

    # Sort strictly by output price ascending
    sorted_ticks = sorted(ticks, key=lambda x: (x.output_usd_mtok, x.input_usd_mtok))

    depth: list[DepthEntry] = []
    for t in sorted_ticks:
        age_hours = round((now - t.timestamp) / 3600.0, 1)
        depth.append(DepthEntry(
            venue=t.venue,
            venue_type=t.venue_type,
            raw_model_id=t.raw_model_id,
            input_usd_mtok=t.input_usd_mtok,
            output_usd_mtok=t.output_usd_mtok,
            cache_read_usd_mtok=t.cache_read_usd_mtok,
            context_length=t.context_length,
            tps=t.tps,
            age_hours=age_hours,
        ))
    return depth


def get_history_summary(store: ConsolidatedTapeStore, instrument: str, days: int = 30) -> list[dict]:
    """Group historical ticks into daily snapshots per venue."""
    ticks = store.get_historical_ticks(instrument, days)
    daily_venue: dict[str, dict[str, dict]] = defaultdict(dict)

    for t in ticks:
        day = t.iso_time[:10]  # YYYY-MM-DD
        daily_venue[day][t.venue] = {
            "venue": t.venue,
            "input": t.input_usd_mtok,
            "output": t.output_usd_mtok,
            "cache_read": t.cache_read_usd_mtok,
            "venue_type": t.venue_type,
        }

    history: list[dict] = []
    for day in sorted(daily_venue.keys()):
        venues_data = list(daily_venue[day].values())
        out_prices = [v["output"] for v in venues_data if v["output"] > 0]
        min_out = min(out_prices) if out_prices else 0.0
        max_out = max(out_prices) if out_prices else 0.0
        median_out = statistics.median(out_prices) if out_prices else 0.0
        history.append({
            "date": day,
            "venue_count": len(venues_data),
            "min_output": min_out,
            "max_output": max_out,
            "median_output": round(median_out, 4),
            "venues": venues_data,
        })
    return history
