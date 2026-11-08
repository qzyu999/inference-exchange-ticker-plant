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
model-name aliases. The initial registry is empty. Do not infer equivalence from
model family or parameter count. Add aliases only after checking the exact model
version and variant. Unmatched IE models remain visible separately.

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
