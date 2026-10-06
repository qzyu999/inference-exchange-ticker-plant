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
    # Fine-tunes must become standalone instruments
    assert registry.resolve_instrument("nousresearch/hermes-3-llama-3.1-70b") == "HERMES-3-LLAMA-3.1-70B"
    assert registry.resolve_instrument("aion-labs/aion-rp-llama-3.1-8b") == "AION-RP-LLAMA-3.1-8B"


def test_deepseek_resolution(registry):
    assert registry.resolve_instrument("deepseek-chat") == "DEEPSEEK-V3"
    assert registry.resolve_instrument("deepseek/deepseek-chat") == "DEEPSEEK-V3"
    assert registry.resolve_instrument("deepseek-reasoner") == "DEEPSEEK-R1"
    assert registry.resolve_instrument("deepseek/deepseek-r1") == "DEEPSEEK-R1"
    assert registry.resolve_instrument("deepseek-r1-distill-llama-70b") == "DEEPSEEK-R1-DISTILL-70B"
    # Experimental and dated checkpoints must not collide with canonical contracts
    assert registry.resolve_instrument("deepseek/deepseek-v3.1-terminus") == "DEEPSEEK-V3.1-TERMINUS"
    assert registry.resolve_instrument("deepseek/deepseek-v3.2") == "DEEPSEEK-V3.2"
    assert registry.resolve_instrument("deepseek/deepseek-r1-0528") == "DEEPSEEK-R1-0528"


def test_frontier_resolution(registry):
    assert registry.resolve_instrument("gpt-4o") == "GPT-4O"
    assert registry.resolve_instrument("gpt-4o-mini") == "GPT-4O-MINI"
    assert registry.resolve_instrument("claude-3-5-sonnet-20241022") == "CLAUDE-3.5-SONNET"
    assert registry.resolve_instrument("claude-3-5-haiku-20241022") == "CLAUDE-3.5-HAIKU"
    # Batch endpoints and dated snapshots must become standalone instruments
    assert registry.resolve_instrument("openai/gpt-4o:batch") == "GPT-4O:BATCH"
    assert registry.resolve_instrument("openai/gpt-4o-2024-05-13") == "GPT-4O-2024-05-13"
    assert registry.resolve_instrument("openai/gpt-4o-mini:batch") == "GPT-4O-MINI:BATCH"
