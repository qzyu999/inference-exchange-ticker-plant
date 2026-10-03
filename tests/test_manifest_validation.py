from pathlib import Path
import pytest
from ticker_plant.config import ManifestRegistry


def test_manifest_directory_loading():
    manifests_dir = Path(__file__).parent.parent / "manifests"
    registry = ManifestRegistry()
    count = registry.load_directory(manifests_dir)

    assert count > 0, "Should load at least one manifest"
    assert len(registry.feed_handlers) >= 10, "Should load at least 10 feed handlers"
    assert len(registry.instruments) >= 8, "Should load at least 8 canonical instruments"

    # Verify key venues exist
    assert "groq" in registry.feed_handlers
    assert "deepinfra" in registry.feed_handlers
    assert "openrouter" in registry.feed_handlers
    assert "openai" in registry.feed_handlers
    assert "anthropic" in registry.feed_handlers
    assert "deepseek" in registry.feed_handlers


def test_feed_handler_attributes():
    manifests_dir = Path(__file__).parent.parent / "manifests"
    registry = ManifestRegistry()
    registry.load_directory(manifests_dir)

    groq = registry.feed_handlers["groq"]
    assert groq.metadata.venue_type == "asic-lpu"
    assert len(groq.spec.quotes) > 0

    deepinfra = registry.feed_handlers["deepinfra"]
    assert deepinfra.metadata.venue_type == "commodity-gpu"
