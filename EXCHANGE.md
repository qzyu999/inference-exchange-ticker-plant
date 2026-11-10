# Exchange catalog publication

Tracking: https://github.com/qzyu999/inference-exchange/issues/269

The full PRD, protocol, deployment guide, and formal verification model live in
`inference-exchange/docs/design/exchange-catalog-prd.md` and `formal/ticker/`.

Run `python -m ticker_plant.exchange_snapshot` from the repository root.
The dedicated Publish Exchange catalog workflow runs every four hours.
It collects the full OpenRouter catalog and endpoint details with concurrency 8.
The legacy financial tape remains separate. Both workflows share a writer lock.

Outputs: `data/exchange/snapshot.json` and `data/exchange/manifest.json`.
Commit them together. The coordinator resolves a commit SHA before reading them.
A failed collection must not create a new publication. Endpoint failures retain
prior endpoint prices and their original timestamps. Removed offers age out after
90 days. Check source failure counts before calling coverage complete.

`manifests/exchange-aliases.json` maps exact OpenRouter model IDs to reviewed IE
model-name aliases.
Do not infer equivalence from model family or parameter count.
Check the exact model version before adding an alias.
Check the variant before adding an alias.
Unmatched IE models remain visible separately.

The registry maps `Llama 3.2 1B Instruct` to
`meta-llama/llama-3.2-1b-instruct` for comparison.
Issue #279 records the live provider name and the upstream checkpoint.
The alias does not verify a Bartowski artifact hash.
The alias does not establish runtime identity.
The alias does not make Q4_K_M equivalent to an upstream quantization.
The registry has no alias for `Qwen2.5 0.5B Instruct`.

`manifests/exchange-sources.json` declares reviewed source relations and facets.
Each source relation has a namespace and a raw model ID.
Do not infer a Hugging Face repository from an OpenRouter slug.
The collector declares its native OpenRouter IDs separately.
`openrouter_vendor_families` maps exact OpenRouter vendor namespaces to families.
The map contains reviewed display labels.
It does not establish model identity.
A per-model reviewed family has first priority.
A family from the source has second priority.
The vendor map supplies a family only when neither has a family.
A per-model null family also overrides the map.
The map applies to current and retained OpenRouter models.
It does not apply to models with only direct offers.
`openrouter_vendor_family_exceptions` states why a namespace has no shared family.
Review each new namespace before publication.
Add it to the map or the exception list.
The snapshot coverage test rejects a namespace absent from both.
The coordinator uses published family fields for the IE search fallback.
Each new catalog generation refreshes that family list.
The Llama relation identifies the Instruct checkpoint.
It does not identify the Base checkpoint or verify a provider artifact.

Each offer declares `quote_kind` as `catalog` or `endpoint`.
Catalog quotes do not identify a named serving endpoint.
Deploy the coordinator schema and web labels before this publisher change.
The publisher backfills legacy kinds from its own offer ID contracts.
It preserves the original observation times during that backfill.
It rejects a legacy record with an unknown origin.
Legacy direct offers require an exact ID from the reviewed direct-card manifest.
Provider and route labels do not establish an offer origin.
The exporter rejects duplicate model IDs, aliases, source IDs, and offer IDs.
It performs this check before writing a publication.
Retained OpenRouter models receive native source IDs and current reviewed aliases.
Those updates do not refresh observation times.

`manifests/exchange-direct.json` contains reviewed direct-provider rate cards.
The initial file is empty because legacy static rates have no verified date.
Each item has `model_id`, `name`, a globally distinct offer `id`, `provider`,
`source_url`, `verified_at` (Unix seconds), `input`, `cache_read`, `output`,
optional `cache_write`, `quantization`, and `context_length`. Prices are decimal
strings in USD per million tokens. Unknown values are null. The model_id is the
canonical catalog ID if the same model is verified, or a distinct source-qualified
ID otherwise. Re-reading a card does not refresh verified_at. Separate prices
with different request/context tiers into separate offers and mark conditions.

Only standard flat per-token quotes should qualify for headline comparisons.
Account-specific discounts and unmodeled tier conditions need separate support.
A direct card's source_type is manual and route is Direct. Do not copy an
OpenRouter quote into a Direct card.

Test with `pytest tests/ -q`. A collector key, if required, belongs in the
OPENROUTER_API_KEY Actions secret. No user keys enter this pipeline.

No first snapshot is bundled in the implementation PR. Run the publication
workflow after merge, then configure the coordinator as described in the PRD.
