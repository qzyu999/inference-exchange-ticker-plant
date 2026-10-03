import tempfile
from pathlib import Path
import pytest
from ticker_plant.models import PriceQuote, TapeTick
from ticker_plant.tape.store import ConsolidatedTapeStore


@pytest.fixture
def temp_store():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_tape.db"
        store = ConsolidatedTapeStore(db_path)
        yield store
        store.close()


def test_append_and_count(temp_store):
    assert temp_store.count_ticks() == 0

    quote1 = PriceQuote(
        venue="groq",
        raw_model_id="llama-3.1-70b-versatile",
        input_usd_mtok=0.59,
        output_usd_mtok=0.79,
    )
    quote2 = PriceQuote(
        venue="deepinfra",
        raw_model_id="meta-llama/Llama-3.1-70B-Instruct",
        input_usd_mtok=0.35,
        output_usd_mtok=0.40,
    )

    tick1 = TapeTick.from_quote(quote1, "LLAMA-3.1-70B")
    tick2 = TapeTick.from_quote(quote2, "LLAMA-3.1-70B")

    committed = temp_store.append_ticks([tick1, tick2])
    assert committed == 2
    assert temp_store.count_ticks() == 2

    distinct_venues = temp_store.get_distinct_venues()
    assert "groq" in distinct_venues
    assert "deepinfra" in distinct_venues

    distinct_inst = temp_store.get_distinct_instruments()
    assert distinct_inst == ["LLAMA-3.1-70B"]


def test_latest_ticks_per_venue(temp_store):
    quote_old = PriceQuote(
        venue="groq",
        raw_model_id="llama-3.1-8b-instant",
        input_usd_mtok=0.08,
        output_usd_mtok=0.10,
    )
    quote_new = PriceQuote(
        venue="groq",
        raw_model_id="llama-3.1-8b-instant",
        input_usd_mtok=0.05,
        output_usd_mtok=0.08,
    )

    t1 = TapeTick.from_quote(quote_old, "LLAMA-3.1-8B")
    t2 = TapeTick.from_quote(quote_new, "LLAMA-3.1-8B")

    temp_store.append_ticks([t1, t2])

    latest = temp_store.get_latest_ticks_per_venue("LLAMA-3.1-8B")
    assert len(latest) == 1
    assert latest[0].output_usd_mtok == 0.08
