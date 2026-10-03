import pytest
from ticker_plant.config import FeedHandlerManifest
from ticker_plant.feed_handlers import create_feed_handler
from ticker_plant.feed_handlers.static_ratecard import StaticRatecardFeedHandler


@pytest.mark.asyncio
async def test_static_ratecard_feed_handler():
    manifest_dict = {
        "apiVersion": "tickerplant.inference.exchange/v1alpha1",
        "kind": "FeedHandler",
        "metadata": {
            "name": "test-venue",
            "venue_type": "commodity-gpu",
        },
        "spec": {
            "driver": "static-ratecard",
            "quotes": [
                {
                    "raw_model_id": "test/model-1",
                    "input_usd_mtok": 0.10,
                    "output_usd_mtok": 0.20,
                    "cache_read_usd_mtok": 0.05,
                }
            ],
        },
    }

    manifest = FeedHandlerManifest.model_validate(manifest_dict)
    handler = create_feed_handler(manifest)
    assert isinstance(handler, StaticRatecardFeedHandler)

    quotes = await handler.fetch_quotes()
    assert len(quotes) == 1
    q = quotes[0]
    assert q.venue == "test-venue"
    assert q.raw_model_id == "test/model-1"
    assert q.input_usd_mtok == 0.10
    assert q.output_usd_mtok == 0.20
    assert q.cache_read_usd_mtok == 0.05
