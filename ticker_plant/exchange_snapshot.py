"""Versioned Exchange export. API observations retain their source and route.

Run with python -m ticker_plant.exchange_snapshot. Files become visible together
in one Git commit. This export is independent of the legacy financial tape.
"""
import asyncio
import hashlib
import json
import os
import time
from decimal import Decimal
from pathlib import Path
from urllib.parse import quote

import httpx


def rate(value):
    if value is None:
        return None
    d = Decimal(str(value))
    # OpenRouter's automatic routes use -1 when the serving model determines price.
    if d == -1:
        return None
    if not d.is_finite() or d < 0 or d * 1_000_000 > 1_000_000:
        raise ValueError('Invalid price')
    return str(d * 1_000_000)


def normalize_model(model, now):
    mid = model['id']
    pricing = model.get('pricing') or {}
    offer = {'id': 'openrouter/' + mid, 'provider': 'OpenRouter catalog',
             'route': 'OpenRouter', 'input': rate(pricing.get('prompt')),
             'output': rate(pricing.get('completion')),
             'cache_read': rate(pricing.get('input_cache_read')),
             'cache_write': rate(pricing.get('input_cache_write')),
             'observed_at': now, 'quantization': None,
             'context_length': model.get('context_length'),
             'source_url': 'https://openrouter.ai/' + quote(mid, safe='/'),
             'source_type': 'api', 'comparable': False, 'history': []}
    return {'id': mid, 'name': model.get('name', mid), 'aliases': [], 'offers': [offer],
            'source_ids': [{'source': 'openrouter', 'model_id': mid}],
            **{key: model.get(key) for key in
               ('family', 'release', 'total_parameters', 'active_parameters', 'variant_tags')}}


def merge_history(previous, current, now):
    """Keep last actual observation per UTC day/offer for 90 days.

    Failed or missing sources keep their old timestamps. Offers age out of the
    retained catalog after 90 days. Never manufacture an observation on failure.
    """
    old = {m['id']: m for m in previous}
    for model in current:
        prior = {o['id']: o for o in old.get(model['id'], {}).get('offers', [])}
        for offer in model['offers']:
            days = {int(p['at']) // 86400: p for p in prior.get(offer['id'], {}).get('history', [])}
            point = {k: offer.get(k) for k in ('input', 'cache_read', 'output')}
            point['at'] = offer['observed_at']
            days[int(point['at']) // 86400] = point
            offer['history'] = [p for _, p in sorted(days.items()) if p['at'] >= now - 90 * 86400][-90:]
            prior[offer['id']] = offer
        if model.get('_preserve_aliases'):
            model['aliases'] = old.get(model['id'], {}).get('aliases', [])
            previous_model = old.get(model['id'], {})
            ids = {(item['source'], item['model_id'].casefold()): item for item in
                   [*previous_model.get('source_ids', []), *model.get('source_ids', [])]}
            model['source_ids'] = list(ids.values())
            for key in ('family', 'release', 'total_parameters', 'active_parameters', 'variant_tags'):
                if model.get(key) is None:
                    model[key] = previous_model.get(key)
        model.pop('_preserve_aliases', None)
        model['offers'] = list(prior.values())
        old[model['id']] = model
    result = []
    for model in old.values():
        model['offers'] = [o for o in model['offers'] if o['observed_at'] >= now - 90 * 86400]
        if model['offers']:
            result.append(model)
    return sorted(result, key=lambda m: m['id'])


async def collect(previous, aliases, client, now, *, sources=None):
    response = await client.get('https://openrouter.ai/api/v1/models')
    response.raise_for_status()
    models = response.json()['data']
    if not isinstance(models, list) or not models:
        raise ValueError('Empty or invalid catalog; retain last publication')
    semaphore = asyncio.Semaphore(8)
    failures = []

    async def fetch(model):
        normalized = normalize_model(model, now)
        normalized['aliases'] = aliases.get(model['id'], [])
        reviewed = (sources or {}).get(model['id'], {})
        for key in ('family', 'release', 'total_parameters', 'active_parameters', 'variant_tags'):
            if key in reviewed:
                normalized[key] = reviewed[key]
        normalized['source_ids'].extend(reviewed.get('source_ids', []))
        async with semaphore:
            try:
                url = 'https://openrouter.ai/api/v1/models/' + quote(model['id'], safe='/') + '/endpoints'
                r = await client.get(url)
                r.raise_for_status()
                endpoints = r.json()['data']['endpoints']
                for e in endpoints:
                    # A tag is needed to distinguish multiple endpoints from one provider.
                    tag = e.get('tag') or e.get('name')
                    provider = e.get('provider_name')
                    if not tag or not provider:
                        continue
                    item = normalize_model({'id': model['id'], 'pricing': e.get('pricing', {})}, now)['offers'][0]
                    item.update(id='openrouter/' + model['id'] + '/' + tag,
                                provider=provider, quantization=e.get('quantization'),
                                context_length=e.get('context_length'), comparable=not e.get('pricing', {}).get('request'),
                                conditions='See source for tier and auxiliary charges')
                    normalized['offers'].append(item)
            except (httpx.HTTPError, KeyError, ValueError, TypeError) as exc:
                failures.append({'model': model['id'], 'error': type(exc).__name__})
        return normalized

    current = await asyncio.gather(*(fetch(m) for m in models))
    return {'schema_version': 1, 'generation': previous.get('generation', 0) + 1,
            'generated_at': now, 'sources': {'openrouter': {'observed_at': now, 'endpoint_failures': failures}},
            'models': merge_history(previous.get('models', []), current, now)}


def direct_models(cards, now):
    """Reviewed USD/Mtok rate cards. Reading a file never advances verified_at."""
    result = []
    for card in cards:
        verified = card['verified_at']
        if type(verified) not in (int, float) or not 0 < verified <= now:
            raise ValueError('Invalid verification time')
        if not card['source_url'].startswith('https://'):
            raise ValueError('Invalid source URL')
        for key in ('input', 'cache_read', 'output', 'cache_write'):
            value = card.get(key)
            if value is not None:
                d = Decimal(str(value))
                if not isinstance(value, str) or not d.is_finite() or d < 0:
                    raise ValueError('Invalid direct rate')
        offer = {**card, 'route': 'Direct', 'source_type': 'manual',
                 'observed_at': verified, 'history': [], 'comparable': not bool(card.get('conditions'))}
        result.append({'id': card['model_id'], 'name': card.get('name', card['model_id']),
                       'aliases': [], '_preserve_aliases': True, 'offers': [offer],
                       'source_ids': card.get('source_ids', []),
                       **{key: card.get(key) for key in
                          ('family', 'release', 'total_parameters', 'active_parameters', 'variant_tags')}})
    return result


async def main():
    dest = Path('data/exchange'); dest.mkdir(parents=True, exist_ok=True)
    target = dest / 'snapshot.json'
    previous = json.loads(target.read_text()) if target.exists() else {}
    aliases_path = Path('manifests/exchange-aliases.json')
    aliases = json.loads(aliases_path.read_text()) if aliases_path.exists() else {}
    sources_path = Path('manifests/exchange-sources.json')
    sources = json.loads(sources_path.read_text()) if sources_path.exists() else {}
    headers = {}
    if os.getenv('OPENROUTER_API_KEY'):
        headers['Authorization'] = 'Bearer ' + os.environ['OPENROUTER_API_KEY']
    async with httpx.AsyncClient(timeout=30, headers=headers) as client:
        result = await collect(previous, aliases, client, int(time.time()), sources=sources)
    direct_path = Path('manifests/exchange-direct.json')
    cards = json.loads(direct_path.read_text()) if direct_path.exists() else []
    result['models'] = merge_history(result['models'], direct_models(cards, result['generated_at']), result['generated_at'])
    raw = json.dumps(result, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    if len(raw) > 64 * 1024 * 1024:
        raise ValueError('Snapshot exceeds 64 MiB. Partition before publishing.')
    tmp = dest / 'snapshot.tmp'; tmp.write_bytes(raw); tmp.replace(target)
    manifest = {'schema_version': 1, 'generation': result['generation'],
                'sha256': hashlib.sha256(raw).hexdigest(), 'file': 'snapshot.json'}
    (dest / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    asyncio.run(main())
