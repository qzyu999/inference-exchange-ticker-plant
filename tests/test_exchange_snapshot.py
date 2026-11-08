from ticker_plant.exchange_snapshot import normalize_model, merge_history


def test_full_identity_free_and_missing_cache():
    a = normalize_model({'id':'qwen/model-v1', 'name':'V1','pricing':{'prompt':'0','completion':'0.0000002'}}, 100)
    b = normalize_model({'id':'qwen/model-v2', 'pricing':{'prompt':'0.0000001','completion':'0.0000002'}}, 100)
    assert a['id'] != b['id']
    assert a['offers'][0]['input'] == '0'
    assert a['offers'][0]['cache_read'] is None
    assert a['offers'][0]['output'] == '0.2000000'


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


@__import__("pytest").mark.asyncio
async def test_endpoint_failure_retains_old_timestamp():
    import httpx
    from ticker_plant.exchange_snapshot import collect
    old = normalize_model({'id':'x/y','pricing':{'prompt':'0','completion':'0'}},100)
    old['offers'].append({**old['offers'][0], 'id':'openrouter/x/y/provider','provider':'Provider'})
    def handler(request):
        if str(request.url).endswith('/endpoints'): return httpx.Response(503)
        return httpx.Response(200,json={'data':[{'id':'x/y','pricing':{'prompt':'0','completion':'0'}}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await collect({'generation':1,'models':[old]}, {}, client,200)
    offers = {o['id']:o for o in result['models'][0]['offers']}
    assert offers['openrouter/x/y/provider']['observed_at'] == 100
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
