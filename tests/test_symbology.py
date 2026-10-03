from pathlib import Path
import pytest
from ticker_plant.config import ManifestRegistry


@pytest.fixture
def registry():
    manifests_dir = Path(__file__).parent.parent / "manifests"
    reg = ManifestRegistry()
    reg.load_directory(manifests_dir)
    return reg


def test_llama_resolution(registry):
    assert registry.resolve_instrument("meta-llama/Llama-3.1-70B-Instruct") == "LLAMA-3.1-70B"
    assert registry.resolve_instrument("meta-llama/llama-3.1-70b-instruct") == "LLAMA-3.1-70B"
    assert registry.resolve_instrument("llama-3.1-70b-versatile") == "LLAMA-3.1-70B"
    assert registry.resolve_instrument("accounts/fireworks/models/llama-v3p1-70b-instruct") == "LLAMA-3.1-70B"


def test_deepseek_resolution(registry):
    assert registry.resolve_instrument("deepseek-chat") == "DEEPSEEK-V3"
    assert registry.resolve_instrument("deepseek/deepseek-chat") == "DEEPSEEK-V3"
    assert registry.resolve_instrument("deepseek-reasoner") == "DEEPSEEK-R1"
    assert registry.resolve_instrument("deepseek/deepseek-r1") == "DEEPSEEK-R1"
    assert registry.resolve_instrument("deepseek-r1-distill-llama-70b") == "DEEPSEEK-R1-DISTILL-70B"


def test_frontier_resolution(registry):
    assert registry.resolve_instrument("gpt-4o") == "GPT-4O"
    assert registry.resolve_instrument("gpt-4o-mini") == "GPT-4O-MINI"
    assert registry.resolve_instrument("claude-3-5-sonnet-20241022") == "CLAUDE-3.5-SONNET"
    assert registry.resolve_instrument("claude-3-5-haiku-20241022") == "CLAUDE-3.5-HAIKU"
