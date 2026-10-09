import pytest
from ticker_plant.config import FeedHandlerManifest
from ticker_plant.feed_handlers.universal import UniversalFeedHandler, _convert_price, _slugify_venue, _matches_pattern


def test_convert_price():
    assert _convert_price(0.000001, "usd_per_token") == 1.0
    assert _convert_price(0.5, "usd_per_mtok") == 0.5
    assert _convert_price(0.002, "usd_per_ktok") == 2.0
    assert _convert_price(50, "cent_per_mtok") == 0.5
    assert _convert_price(0.00001, "cent_per_token") == 0.1
    assert _convert_price(0, "usd_per_token") == 0.0


def test_slugify_venue():
    slug, vtype = _slugify_venue("Amazon Bedrock")
    assert slug == "bedrock"
    assert vtype == "commodity-gpu"

    slug, vtype = _slugify_venue("Groq", {"groq": "asic-lpu"})
    assert slug == "groq"
    assert vtype == "asic-lpu"

    slug, vtype = _slugify_venue("Together AI")
    assert slug == "together"


def test_matches_pattern():
    assert _matches_pattern("meta-llama/llama-3.1-70b-instruct", ["meta-llama/*"])
    assert _matches_pattern("deepseek/deepseek-r1", ["*deepseek*"])
    assert not _matches_pattern("openai/gpt-4o", ["meta-llama/*", "deepseek/*"])


@pytest.mark.asyncio
async def test_universal_key_value_map():
    manifest_dict = {
        "apiVersion": "tickerplant.inference.exchange/v1alpha1",
        "kind": "FeedHandler",
        "metadata": {
            "name": "registry-test",
            "venue_type": "aggregator",
        },
        "spec": {
            "driver": "rest-declarative",
            "collector": {
                "endpoint": "https://example.com/models.json",
                "unbundle": {
                    "enabled": True,
                    "mode": "key_value_map",
                    "venue_path": "provider",
                    "venue_type_map": {"cerebras": "asic-lpu"},
                },
            },
            "normalizer": {
                "pricing": {
                    "prompt_path": "cost.prompt",
                    "completion_path": "cost.completion",
                    "unit": "usd_per_token",
                },
                "attributes": {
                    "context_length_path": "ctx",
                },
            },
        },
    }
    manifest = FeedHandlerManifest.model_validate(manifest_dict)
    handler = UniversalFeedHandler(manifest)

    mock_data = {
        "llama-70b": {
            "provider": "Cerebras",
            "cost": {"prompt": "0.0000006", "completion": "0.0000006"},
            "ctx": 131072,
        },
        "deepseek-r1": {
            "provider": "DeepInfra",
            "cost": {"prompt": "0.0000007", "completion": "0.00000219"},
            "ctx": 65536,
        },
    }

    quotes = handler._extract_key_value_map(mock_data, manifest.spec.collector.unbundle, manifest.spec.normalizer)
    assert len(quotes) == 2
    assert quotes[0].venue == "cerebras"
    assert quotes[0].venue_type == "asic-lpu"
    assert quotes[0].output_usd_mtok == 0.6
    assert quotes[0].context_length == 131072

    assert quotes[1].venue == "deepinfra"
    assert quotes[1].output_usd_mtok == 2.19


@pytest.mark.asyncio
async def test_universal_nested_array():
    manifest_dict = {
        "apiVersion": "tickerplant.inference.exchange/v1alpha1",
        "kind": "FeedHandler",
        "metadata": {
            "name": "gateway-test",
            "venue_type": "aggregator",
        },
        "spec": {
            "driver": "rest-declarative",
            "collector": {
                "endpoint": "https://example.com/models",
                "unbundle": {
                    "enabled": True,
                    "mode": "nested_array",
                    "items_path": "endpoints",
                    "venue_path": "host",
                },
            },
            "normalizer": {
                "items_path": "data",
                "model_id_path": "id",
                "pricing": {
                    "prompt_path": "price.in",
                    "completion_path": "price.out",
                    "unit": "usd_per_mtok",
                },
            },
        },
    }
    manifest = FeedHandlerManifest.model_validate(manifest_dict)
    handler = UniversalFeedHandler(manifest)

    mock_data = {
        "data": [
            {
                "id": "meta-llama/llama-3.1-70b",
                "endpoints": [
                    {"host": "DeepInfra", "price": {"in": 0.23, "out": 0.40}},
                    {"host": "Together", "price": {"in": 0.88, "out": 0.88}},
                ],
            }
        ]
    }

    quotes = handler._extract_nested_array(mock_data, manifest.spec.collector.unbundle, manifest.spec.normalizer)
    assert len(quotes) == 2
    assert quotes[0].venue == "deepinfra"
    assert quotes[0].raw_model_id == "meta-llama/llama-3.1-70b"
    assert quotes[0].output_usd_mtok == 0.40
    assert quotes[1].venue == "together"
    assert quotes[1].output_usd_mtok == 0.88
