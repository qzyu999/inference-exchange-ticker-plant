"""Abstract base interface for all venue Feed Handlers."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ticker_plant.config import FeedHandlerManifest
    from ticker_plant.models import PriceQuote

logger = logging.getLogger(__name__)


class BaseFeedHandler(ABC):
    """Base class for market data venue feed handlers."""

    def __init__(self, manifest: FeedHandlerManifest):
        self.manifest = manifest
        self.name = manifest.metadata.name
        self.venue_type = manifest.metadata.venue_type
        self.spec = manifest.spec

    @abstractmethod
    async def fetch_quotes(self) -> list[PriceQuote]:
        """Fetch current price quotes from this venue.

        Returns a list of raw PriceQuote objects (before canonical mapping).
        """
        raise NotImplementedError
