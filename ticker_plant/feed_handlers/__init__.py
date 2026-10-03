"""Feed Handlers registry and factory."""

from __future__ import annotations

from typing import TYPE_CHECKING
from ticker_plant.feed_handlers.base import BaseFeedHandler
from ticker_plant.feed_handlers.openrouter import OpenRouterFeedHandler
from ticker_plant.feed_handlers.openai_compat import OpenAICompatibleFeedHandler
from ticker_plant.feed_handlers.static_ratecard import StaticRatecardFeedHandler
from ticker_plant.feed_handlers.web_scraper import WebScraperFeedHandler
from ticker_plant.feed_handlers.litellm_archive import LiteLLMArchiveFeedHandler

if TYPE_CHECKING:
    from ticker_plant.config import FeedHandlerManifest


DRIVERS = {
    "openrouter-endpoints": OpenRouterFeedHandler,
    "openai-compatible": OpenAICompatibleFeedHandler,
    "static-ratecard": StaticRatecardFeedHandler,
    "web-scraper": WebScraperFeedHandler,
    "litellm-archive": LiteLLMArchiveFeedHandler,
}


def create_feed_handler(manifest: FeedHandlerManifest) -> BaseFeedHandler:
    """Instantiate a feed handler for a given manifest spec."""
    driver_name = manifest.spec.driver
    handler_cls = DRIVERS.get(driver_name)
    if not handler_cls:
        raise ValueError(f"Unknown feed handler driver: {driver_name}")
    return handler_cls(manifest)
