import json
from copy import deepcopy
from pathlib import Path

import httpx
import pytest

from ticker_plant.exchange_snapshot import (
    apply_reviewed_identity,
    collect,
    normalize_model,
    validate_identities,
)


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def reviewed_sources():
    return json.loads((ROOT / 'manifests/exchange-sources.json').read_text())


@pytest.mark.parametrize(('mid', 'family'), [
    ('qwen/qwen-2.5-7b-instruct', 'qwen'),
    ('meta-llama/llama-3.1-8b-instruct', 'llama'),
    ('mistralai/codestral-2508', 'mistral'),
    ('google/gemini-3.5-flash', None),
    ('~google/gemini-pro-latest', 'gemini'),
    ('openai/o3', None),
    ('~openai/gpt-mini-latest', 'gpt'),
])
def test_reviewed_vendor_family_uses_exact_namespace(reviewed_sources, mid, family):
    model = normalize_model({'id': mid, 'name': 'Unrelated display name'}, 100)
    apply_reviewed_identity(model, {}, reviewed_sources)
    assert model['family'] == family
    assert model['id'] == mid
    assert model['aliases'] == []
    assert model['source_ids'] == [{'source': 'openrouter', 'model_id': mid}]


@pytest.mark.parametrize(('source_family', 'reviewed', 'expected'), [
    (None, {}, 'qwen'),
    ('source-family', {}, 'source-family'),
    (None, {'family': 'model-family'}, 'model-family'),
    ('source-family', {'family': 'model-family'}, 'model-family'),
    ('source-family', {'family': None}, None),
])
def test_per_model_family_overrides_source_and_vendor(source_family, reviewed, expected):
    mid = 'qwen/example'
    sources = {'openrouter_vendor_families': {'qwen': 'qwen'}, mid: reviewed}
    model = normalize_model({'id': mid, 'family': source_family}, 100)
    assert apply_reviewed_identity(model, {}, sources)['family'] == expected


def test_exception_does_not_block_per_model_or_source_family(reviewed_sources):
    mid = 'google/example'
    model = normalize_model({'id': mid, 'family': 'source-family'}, 100)
    assert apply_reviewed_identity(model, {}, reviewed_sources)['family'] == 'source-family'
    reviewed_sources[mid] = {'family': 'reviewed-family'}
    model = normalize_model({'id': mid}, 100)
    assert apply_reviewed_identity(model, {}, reviewed_sources)['family'] == 'reviewed-family'


def test_unknown_vendor_does_not_get_family_from_name_or_model_slug(reviewed_sources):
    model = normalize_model({'id': 'unknown/qwen', 'name': 'Qwen'}, 100)
    assert apply_reviewed_identity(model, {}, reviewed_sources)['family'] is None


def test_vendor_fallback_requires_openrouter_offer_provenance(reviewed_sources):
    model = normalize_model({'id': 'qwen/example'}, 100)
    model['offers'][0].update(id='direct/example', route='Direct')
    model['source_ids'] = []
    assert apply_reviewed_identity(model, {}, reviewed_sources)['family'] is None
    model['offers'][0]['id'] = 'openrouter/qwen/example/provider-tag'
    assert apply_reviewed_identity(model, {}, reviewed_sources)['family'] == 'qwen'


def test_published_snapshot_vendor_namespaces_have_reviewed_families_or_exceptions(reviewed_sources):
    snapshot = json.loads((ROOT / 'data/exchange/snapshot.json').read_text())
    vendors = {model['id'].split('/', 1)[0] for model in snapshot['models']}
    families = reviewed_sources['openrouter_vendor_families']
    exceptions = reviewed_sources['openrouter_vendor_family_exceptions']
    missing = vendors - families.keys() - exceptions.keys()
    assert not missing, f'Unreviewed OpenRouter vendor namespaces: {sorted(missing)}'
    assert {vendor for vendor, family in families.items() if family is None} <= exceptions.keys()
    assert all(isinstance(reason, str) and reason.strip() for reason in exceptions.values())
    assert all(families.get(vendor) is None for vendor in exceptions)
    assert all(family is None or isinstance(family, str) and 0 < len(family) <= 100
               and family == family.strip() for family in families.values())


def test_every_published_gemma_model_has_reviewed_gemma_family(reviewed_sources):
    snapshot = json.loads((ROOT / 'data/exchange/snapshot.json').read_text())
    models = [model for model in snapshot['models'] if '/gemma' in model['id']]
    assert models, 'The published snapshot must include Gemma models for this check'
    for model in models:
        mid = model['id']
        assert reviewed_sources.get(mid, {}).get('family') == 'gemma', mid
        enriched = apply_reviewed_identity(deepcopy(model), {}, reviewed_sources)
        assert enriched['family'] == 'gemma', mid


@pytest.mark.asyncio
async def test_collected_and_retained_models_get_vendor_family_without_merging(reviewed_sources):
    retained = normalize_model({'id': 'qwen/qwen-2.5-7b-instruct'}, 100)
    retained.pop('family')

    def handler(request):
        if str(request.url).endswith('/endpoints'):
            return httpx.Response(503)
        return httpx.Response(200, json={'data': [{'id': 'qwen/qwen3-7b'}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await collect({'generation': 1, 'models': [retained]}, {}, client, 200,
                               sources=reviewed_sources)
    models = {model['id']: model for model in result['models']}
    assert set(models) == {'qwen/qwen-2.5-7b-instruct', 'qwen/qwen3-7b'}
    assert all(model['family'] == 'qwen' for model in models.values())
    assert models['qwen/qwen-2.5-7b-instruct']['offers'][0]['observed_at'] == 100
    assert models['qwen/qwen3-7b']['offers'][0]['observed_at'] == 200
    validate_identities(result['models'])
