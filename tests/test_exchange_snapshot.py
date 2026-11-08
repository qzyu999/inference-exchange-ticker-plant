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
