import tempfile
from pathlib import Path
import pytest
from ticker_plant.models import PriceQuote, TapeTick
from ticker_plant.tape.store import ConsolidatedTapeStore
from ticker_plant.tape.analytics import get_bbo, get_depth


@pytest.fixture
def populated_store():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_tape.db"
        store = ConsolidatedTapeStore(db_path)

        quotes = [
            # Groq: high-speed, slightly higher price
            PriceQuote("groq", "llama-3.1-70b-versatile", 0.59, 0.79, venue_type="asic-lpu", tps=280),
            # DeepInfra: low cost
            PriceQuote("deepinfra", "meta-llama/Llama-3.1-70B-Instruct", 0.35, 0.40, venue_type="commodity-gpu"),
            # Together: intermediate
            PriceQuote("together", "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo", 0.88, 0.88, venue_type="commodity-gpu"),
            # Novita: lowest
            PriceQuote("novita", "meta-llama/llama-3.1-70b-instruct", 0.28, 0.35, venue_type="commodity-gpu"),
        ]

        ticks = [TapeTick.from_quote(q, "LLAMA-3.1-70B") for q in quotes]
        store.append_ticks(ticks)

        yield store
        store.close()


def test_bbo_calculation(populated_store):
    bbo_list = get_bbo(populated_store, "LLAMA-3.1-70B")
    assert len(bbo_list) == 1
    bbo = bbo_list[0]

    assert bbo.instrument == "LLAMA-3.1-70B"
    assert bbo.cheapest_output_venue == "novita"
    assert bbo.cheapest_output_price == 0.35
    assert bbo.highest_output_venue == "together"
    assert bbo.highest_output_price == 0.88
    assert bbo.venue_count == 4
    assert bbo.spread_pct > 100.0  # (0.88 - 0.35) / 0.35 * 100 ~ 151%


def test_depth_sorting(populated_store):
    depth = get_depth(populated_store, "LLAMA-3.1-70B")
    assert len(depth) == 4

    # Must be sorted ascending by output price
    prices = [d.output_usd_mtok for d in depth]
    assert prices == sorted(prices)
    assert depth[0].venue == "novita"
    assert depth[-1].venue == "together"
