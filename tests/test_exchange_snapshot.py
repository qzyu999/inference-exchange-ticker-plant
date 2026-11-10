from ticker_plant.exchange_snapshot import normalize_model, merge_history
import pytest


def test_full_identity_free_and_missing_cache():
    a = normalize_model({'id':'qwen/model-v1', 'name':'V1','pricing':{'prompt':'0','completion':'0.0000002'}}, 100)
    b = normalize_model({'id':'qwen/model-v2', 'pricing':{'prompt':'0.0000001','completion':'0.0000002'}}, 100)
    assert a['id'] != b['id']
    assert a['offers'][0]['input'] == '0'
    assert a['offers'][0]['cache_read'] is None
    assert a['offers'][0]['output'] == '0.2000000'
    assert a['offers'][0]['quote_kind'] == 'catalog'


def test_history_preserves_observations_and_deduplicates_daily():
    old = normalize_model({'id':'x/y','pricing':{'prompt':'0','completion':'0'}}, 100)
    new = normalize_model({'id':'x/y','pricing':{'prompt':'0','completion':'0.000001'}}, 200)
    merged = merge_history([old], [new], 200)
    assert len(merged[0]['offers'][0]['history']) == 1
    assert merged[0]['offers'][0]['history'][0]['output'] == '1.000000'
    assert merge_history(merged, [], 300)[0]['offers'][0]['observed_at'] == 200


def test_direct_ratecard_keeps_verification_time_and_route():
    from ticker_plant.exchange_snapshot import direct_models
    card = {'model_id':'x/y','name':'Model','provider':'Together','id':'together/model',
            'source_url':'https://example.com/prices','verified_at':100,
            'input':'0.1','cache_read':None,'output':'0.2','quantization':'FP16','context_length':4096}
    model = direct_models([card], now=500)[0]
    assert model['offers'][0]['route'] == 'Direct'
    assert model['offers'][0]['observed_at'] == 100
    assert model['offers'][0]['input'] == '0.1'
    assert model['offers'][0]['quote_kind'] == 'endpoint'


@__import__("pytest").mark.asyncio
async def test_endpoint_failure_retains_old_timestamp():
    import httpx
    from ticker_plant.exchange_snapshot import collect
    old = normalize_model({'id':'x/y','pricing':{'prompt':'0','completion':'0'}},100)
    old['offers'].append({**old['offers'][0], 'id':'openrouter/x/y/provider','provider':'Provider',
                          'quote_kind':'endpoint'})
    def handler(request):
        if str(request.url).endswith('/endpoints'): return httpx.Response(503)
        return httpx.Response(200,json={'data':[{'id':'x/y','pricing':{'prompt':'0','completion':'0'}}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await collect({'generation':1,'models':[old]}, {}, client,200)
    offers = {o['id']:o for o in result['models'][0]['offers']}
    assert offers['openrouter/x/y/provider']['observed_at'] == 100
    assert offers['openrouter/x/y/provider']['quote_kind'] == 'endpoint'
    assert offers['openrouter/x/y']['observed_at'] == 200
    assert len(result['sources']['openrouter']['endpoint_failures']) == 1


def test_retention_is_at_most_90_days_and_alias_can_be_removed():
    old = normalize_model({'id':'x/y'},100)
    old['aliases'] = ['wrong alias']
    old['offers'][0]['history'] = [{'at':100+i*86400,'input':None,'output':None,'cache_read':None} for i in range(90)]
    new = normalize_model({'id':'x/y'},100+90*86400)
    merged = merge_history([old],[new],100+90*86400)
    assert len(merged[0]['offers'][0]['history']) == 90
    assert merged[0]['aliases'] == []


def test_dynamic_price_sentinel_is_unknown_not_free():
    model = normalize_model({'id':'openrouter/auto','pricing':{'prompt':'-1','completion':'-1'}},100)
    assert model['offers'][0]['input'] is None
    assert model['offers'][0]['output'] is None


@__import__("pytest").mark.asyncio
async def test_reviewed_llama_alias_is_published_without_qwen_alias():
    import json
    from pathlib import Path
    import httpx
    from ticker_plant.exchange_snapshot import collect
    aliases = json.loads((Path(__file__).resolve().parents[1] / 'manifests/exchange-aliases.json').read_text())
    def handler(request):
        if str(request.url).endswith('/endpoints'):
            return httpx.Response(200, json={'data': {'endpoints': []}})
        return httpx.Response(200, json={'data': [
            {'id': 'meta-llama/llama-3.2-1b-instruct'},
            {'id': 'qwen/qwen3.5-9b'},
        ]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        sources = json.loads((Path(__file__).resolve().parents[1] / 'manifests/exchange-sources.json').read_text())
        result = await collect({}, aliases, client, 200, sources=sources)
    models = {m['id']: m for m in result['models']}
    assert models['meta-llama/llama-3.2-1b-instruct']['aliases'] == ['Llama 3.2 1B Instruct']
    assert models['qwen/qwen3.5-9b']['aliases'] == []
    assert models['qwen/qwen3.5-9b']['family'] == 'qwen'
    assert models['meta-llama/llama-3.2-1b-instruct']['source_ids'] == [
        {'source': 'openrouter', 'model_id': 'meta-llama/llama-3.2-1b-instruct'},
        {'source': 'huggingface', 'model_id': 'meta-llama/Llama-3.2-1B-Instruct'}]
    assert not any('Qwen2.5 0.5B Instruct' in names for names in aliases.values())


def test_direct_rates_preserve_reviewed_source_identity():
    from ticker_plant.exchange_snapshot import direct_models
    prior = normalize_model({'id': 'x/y', 'family': 'example'}, 100)
    prior['source_ids'].append({'source': 'huggingface', 'model_id': 'org/model'})
    card = {'id': 'direct/x', 'model_id': 'x/y', 'provider': 'Provider',
            'source_url': prior['offers'][0]['source_url'], 'verified_at': 150,
            'input': '0.1', 'output': '0.2'}
    merged = merge_history([prior], direct_models([card], 200), 200)[0]
    assert merged['family'] == 'example'
    assert {'source': 'huggingface', 'model_id': 'org/model'} in merged['source_ids']


def test_legacy_quote_backfill_keeps_observations_and_uses_factory_ids():
    from copy import deepcopy
    import pytest
    old = normalize_model({'id': 'x/y'}, 100)
    old['offers'][0].pop('quote_kind')
    old['offers'][0]['provider'] = 'A label that is not a provider'
    endpoint = {**deepcopy(old['offers'][0]), 'id': 'openrouter/x/y/tag', 'provider': 'OpenRouter'}
    old['offers'].append(endpoint)
    merged = merge_history([old], [], 200)[0]['offers']
    assert [o['quote_kind'] for o in merged] == ['catalog', 'endpoint']
    assert [o['observed_at'] for o in merged] == [100, 100]
    unknown = normalize_model({'id': 'x/y'}, 100)
    unknown['offers'][0].pop('quote_kind')
    unknown['offers'][0]['id'] = 'unrecognized/source'
    with pytest.raises(ValueError, match='origin'):
        merge_history([unknown], [], 200)


@__import__("pytest").mark.asyncio
async def test_catalog_and_endpoint_kinds_are_declared_separately():
    import httpx
    from ticker_plant.exchange_snapshot import collect
    def handler(request):
        if str(request.url).endswith('/endpoints'):
            return httpx.Response(200, json={'data': {'endpoints': [
                {'tag': 'endpoint', 'provider_name': 'Cloudflare', 'pricing': {'prompt': '0'}}]}})
        return httpx.Response(200, json={'data': [{'id': 'x/y'}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await collect({}, {}, client, 200)
    offers = result['models'][0]['offers']
    assert [o['quote_kind'] for o in offers] == ['catalog', 'endpoint']
    assert offers[1]['provider'] == 'Cloudflare'
    assert offers[1]['route'] == 'OpenRouter'


def test_native_source_and_family_do_not_come_from_name_or_slug():
    model = normalize_model({'id': 'vendor/model', 'name': 'Llama 7B',
                             'hugging_face_id': 'unreviewed/model'}, 100)
    assert model['source_ids'] == [{'source': 'openrouter', 'model_id': 'vendor/model'}]
    assert model['family'] is None
    supplied = normalize_model({'id': 'vendor/other', 'name': 'Different name',
                                'family': 'supplied-family'}, 100)
    assert supplied['family'] == 'supplied-family'


@pytest.mark.parametrize('case', [
    'model', 'alias', 'alias-model-id', 'source-within-model', 'source-across-models', 'offer',
])
def test_duplicate_identities_are_rejected(case):
    from ticker_plant.exchange_snapshot import validate_identities
    first = normalize_model({'id': 'x/one'}, 100)
    second = normalize_model({'id': 'x/two'}, 100)
    if case == 'model':
        second['id'] = first['id']
    elif case == 'alias':
        first['aliases'] = ['Local Name']
        second['aliases'] = ['local name']
    elif case == 'alias-model-id':
        first['aliases'] = ['x/two']
    elif case == 'source-within-model':
        first['source_ids'].append(dict(first['source_ids'][0]))
    elif case == 'source-across-models':
        first['source_ids'].append({'source': 'huggingface', 'model_id': 'org/Model'})
        second['source_ids'].append({'source': 'huggingface', 'model_id': 'org/model'})
    else:
        second['offers'][0]['id'] = first['offers'][0]['id']
    with pytest.raises(ValueError, match='Duplicate'):
        validate_identities([first, second])


@pytest.mark.asyncio
async def test_collection_rejects_duplicate_aliases_before_returning_publication():
    import httpx
    from ticker_plant.exchange_snapshot import collect
    def handler(request):
        if str(request.url).endswith('/endpoints'):
            return httpx.Response(200, json={'data': {'endpoints': []}})
        return httpx.Response(200, json={'data': [{'id': 'x/one'}, {'id': 'x/two'}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ValueError, match='alias'):
            await collect({}, {'x/one': ['Local'], 'x/two': ['local']}, client, 200)


@pytest.mark.asyncio
async def test_retained_models_receive_manifest_identity_without_new_observations():
    import httpx
    from ticker_plant.exchange_snapshot import collect
    mid = 'meta-llama/llama-3.2-1b-instruct'
    old = normalize_model({'id': mid}, 100)
    old.pop('source_ids')
    old['offers'][0].pop('quote_kind')
    def handler(request):
        if str(request.url).endswith('/endpoints'):
            return httpx.Response(200, json={'data': {'endpoints': []}})
        return httpx.Response(200, json={'data': [{'id': 'qwen/other', 'family': 'qwen'}]})
    reviewed = {'source': 'huggingface', 'model_id': 'meta-llama/Llama-3.2-1B-Instruct'}
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await collect({'generation': 1, 'models': [old]}, {mid: ['Llama 3.2 1B Instruct']},
                               client, 200, sources={mid: {'family': 'llama', 'source_ids': [reviewed]}})
    retained = next(m for m in result['models'] if m['id'] == mid)
    assert retained['aliases'] == ['Llama 3.2 1B Instruct']
    assert retained['family'] == 'llama'
    assert retained['source_ids'] == [{'source': 'openrouter', 'model_id': mid}, reviewed]
    assert retained['offers'][0]['observed_at'] == 100
    assert retained['offers'][0]['quote_kind'] == 'catalog'


def test_direct_legacy_kind_requires_reviewed_offer_id():
    from ticker_plant.exchange_snapshot import declared_quote_kind
    legacy = {'id': 'direct/reviewed', 'provider': 'OpenRouter catalog', 'route': 'OpenRouter',
              'source_type': 'manual', 'model_id': 'x/y', 'verified_at': 100, 'observed_at': 100}
    with pytest.raises(ValueError, match='origin'):
        declared_quote_kind('x/y', legacy)
    assert declared_quote_kind('x/y', legacy, direct_offer_ids={('x/y', 'direct/reviewed')}) == 'endpoint'


def test_two_direct_providers_can_share_one_checkpoint_without_duplicate_sources():
    from ticker_plant.exchange_snapshot import direct_models
    cards = [{
        'id': 'direct/' + provider, 'model_id': 'x/y', 'provider': provider,
        'source_url': normalize_model({'id': 'x/y'}, 100)['offers'][0]['source_url'], 'verified_at': 100,
        'input': '0.1', 'output': '0.2',
        'source_ids': [{'source': 'huggingface', 'model_id': 'org/checkpoint'}],
    } for provider in ('one', 'two')]
    merged = merge_history([], direct_models(cards, 200), 200)
    assert len(merged) == 1
    assert len(merged[0]['offers']) == 2
    assert len(merged[0]['source_ids']) == 1
    assert {o['quote_kind'] for o in merged[0]['offers']} == {'endpoint'}


@pytest.mark.asyncio
@pytest.mark.parametrize('case', ['alias', 'source'])
async def test_invalid_identity_never_replaces_the_last_publication(tmp_path, monkeypatch, case):
    import json
    import ticker_plant.exchange_snapshot as exporter
    destination = tmp_path / 'data' / 'exchange'
    destination.mkdir(parents=True)
    old = json.dumps({'schema_version': 1, 'generation': 1, 'generated_at': 100, 'models': []})
    target = destination / 'snapshot.json'
    target.write_text(old)
    first = normalize_model({'id': 'x/one'}, 200)
    second = normalize_model({'id': 'x/two'}, 200)
    if case == 'alias':
        first['aliases'] = ['Local']
        second['aliases'] = ['local']
    else:
        shared = {'source': 'huggingface', 'model_id': 'org/model'}
        first['source_ids'].append(shared)
        second['source_ids'].append(shared)
    async def invalid_collection(*args, **kwargs):
        return {'schema_version': 1, 'generation': 2, 'generated_at': 200,
                'models': [first, second]}
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(exporter, 'collect', invalid_collection)
    with pytest.raises(ValueError, match='Duplicate'):
        await exporter.main()
    assert target.read_text() == old
    assert not (destination / 'snapshot.tmp').exists()
    assert not (destination / 'manifest.json').exists()
