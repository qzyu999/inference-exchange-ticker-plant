"""Tests for Ecosystem Demand and Adoption Telemetry."""

import json
from pathlib import Path
import pytest
from ticker_plant.config import ManifestRegistry, DemandSignalFeedManifest
from ticker_plant.models import DemandMetric
from ticker_plant.tape.store import ConsolidatedTapeStore
from ticker_plant.tape.export import export_demand_json, export_demand_csv, export_demand_js
from ticker_plant.demand.collector import (
    OpenRouterDemandCollector,
    HuggingFaceDemandCollector,
    LMSysArenaDemandCollector,
    DemandIngestionEngine,
)


def test_demand_manifest_validation():
    manifest_dict = {
        "apiVersion": "tickerplant.inference.exchange/v1alpha1",
        "kind": "DemandSignalFeed",
        "metadata": {
            "name": "test-feed",
            "category": "aggregator-throughput",
        },
        "spec": {
            "source": "openrouter",
            "driver": "openrouter-rankings",
            "endpoint": "https://openrouter.ai/rankings",
            "schedule": "*/30 * * * *",
            "active": True,
        },
    }
    manifest = DemandSignalFeedManifest.model_validate(manifest_dict)
    assert manifest.metadata.name == "test-feed"
    assert manifest.spec.source == "openrouter"
    assert manifest.spec.active is True


def test_manifest_registry_loads_demand(tmp_path: Path):
    yaml_content = """
apiVersion: tickerplant.inference.exchange/v1alpha1
kind: DemandSignalFeed
metadata:
  name: or-test
  category: aggregator-throughput
spec:
  source: openrouter
  driver: openrouter-rankings
  endpoint: "https://openrouter.ai/rankings"
"""
    manifest_file = tmp_path / "demand.yaml"
    manifest_file.write_text(yaml_content)

    registry = ManifestRegistry()
    registry.load_file(manifest_file)
    assert "or-test" in registry.demand_feeds
    assert registry.demand_feeds["or-test"].spec.source == "openrouter"


def test_tape_store_demand_crud(tmp_path: Path):
    db_file = tmp_path / "test_tape.db"
    store = ConsolidatedTapeStore(db_path=db_file)

    metric = DemandMetric(
        instrument="LLAMA-3.1-70B",
        timestamp=1700000000.0,
        iso_time="2023-11-14T22:13:20Z",
        openrouter_rank=4,
        openrouter_weekly_tokens=5000000000,
        openrouter_requests=2500000,
        openrouter_spend_usd=4500.50,
        hf_model_id="meta-llama/Llama-3.1-70B-Instruct",
        hf_downloads_30d=82500,
        hf_likes=1006,
        arena_rank=8,
        arena_rating=0.0894,
        arena_votes=41908,
        arena_model_name="Llama 3.1 70B Instruct",
        demand_index=88.5,
    )

    committed = store.upsert_demand_metrics([metric])
    assert committed == 1

    fetched = store.get_demand_metric("LLAMA-3.1-70B")
    assert fetched is not None
    assert fetched.instrument == "LLAMA-3.1-70B"
    assert fetched.openrouter_weekly_tokens == 5000000000
    assert fetched.hf_downloads_30d == 82500
    assert fetched.arena_votes == 41908
    assert fetched.demand_index == 88.5

    all_metrics = store.get_all_demand_metrics()
    assert "LLAMA-3.1-70B" in all_metrics

    # Test update preserves and merges
    metric_update = DemandMetric(
        instrument="LLAMA-3.1-70B",
        timestamp=1700000100.0,
        iso_time="2023-11-14T22:15:00Z",
        openrouter_weekly_tokens=6000000000,
    )
    store.upsert_demand_metrics([metric_update])
    updated = store.get_demand_metric("LLAMA-3.1-70B")
    assert updated.openrouter_weekly_tokens == 6000000000
    assert updated.hf_downloads_30d == 82500  # Kept previous value


def test_export_demand_files(tmp_path: Path):
    db_file = tmp_path / "test_tape.db"
    store = ConsolidatedTapeStore(db_path=db_file)

    metric = DemandMetric(
        instrument="DEEPSEEK-R1",
        timestamp=1700000000.0,
        iso_time="2023-11-14T22:13:20Z",
        openrouter_rank=1,
        openrouter_weekly_tokens=30000000000,
        hf_downloads_30d=1100000,
        arena_votes=180000,
        demand_index=99.2,
    )
    store.upsert_demand_metrics([metric])

    json_out = tmp_path / "demand.json"
    csv_out = tmp_path / "demand.csv"
    js_out = tmp_path / "demand.js"

    export_demand_json(store, json_out)
    export_demand_csv(store, csv_out)
    export_demand_js(store, js_out)

    assert json_out.exists()
    with open(json_out) as f:
        data = json.load(f)
        assert "DEEPSEEK-R1" in data
        assert data["DEEPSEEK-R1"]["demand_index"] == 99.2

    assert csv_out.exists()
    assert js_out.exists()
    js_text = js_out.read_text()
    assert "window.TICKER_DEMAND_DATA = " in js_text
