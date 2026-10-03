# Inference Exchange Ticker Plant (`inference-exchange-ticker-plant`)

[![Test Suite](https://github.com/qzyu999/inference-exchange-ticker-plant/actions/workflows/tests.yml/badge.svg)](https://github.com/qzyu999/inference-exchange-ticker-plant/actions/workflows/tests.yml)
[![Consolidated Tape Ingest](https://github.com/qzyu999/inference-exchange-ticker-plant/actions/workflows/tape-cron.yml/badge.svg)](https://github.com/qzyu999/inference-exchange-ticker-plant/actions/workflows/tape-cron.yml)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

An institutional-grade market data collection engine and **Consolidated Tape** for AI inference pricing. 

Modeled on the architecture of real stock and commodities exchanges (NYSE, NASDAQ, CME Group, ICE), it uses modular **Feed Handlers** with Kubernetes-style declarative manifests to ingest, normalize, archive, and query historical inference prices across all venues — from OpenRouter and cloud GPU hosters to frontier labs and OTC community drops on X/Twitter.

---

## The Exchange Architecture (TradFi Analogue)

| Stock & Commodity Exchange Concept | AI Inference Analogue | `ticker-plant` Implementation |
| :--- | :--- | :--- |
| **Ticker Plant** | Central price ingest, normalization, and archival engine | `ticker_plant.engine.TickerPlant` |
| **Feed Handler** | Venue-specific connectivity driver (FIX / ITCH / REST) | Pluggable `FeedHandler` classes |
| **Consolidated Tape** | Universal public time-series trade & quote log | `tape.db` SQLite/DuckDB store |
| **Instrument Symbology** | Standardized ticker symbols (e.g. CUSIP/ISIN to `AAPL`) | `InstrumentMapping` (resolves raw IDs to `LLAMA-3.1-70B`) |
| **NBBO (National Best Bid/Offer)** | Lowest/highest available price across all venues | `ticker-plant tape bbo` |
| **Level 2 Market Depth** | Full book of all venue offers ranked by price | `ticker-plant tape depth <instrument>` |

```
                     ┌──────────────────────────────────────────────┐
                     │           Declarative Manifests              │
                     │  manifests/venues/*.yaml                     │
                     │  manifests/instruments/*.yaml                │
                     └──────────────────────┬───────────────────────┘
                                            │
                                            ▼
                     ┌──────────────────────────────────────────────┐
                     │                 Ticker Plant                 │
                     │                                              │
                     │  Feed Handlers (Parallel Asynchronous Ingest) │
                     │   ├── OpenRouter (Endpoints Unbundler)       │
                     │   ├── Groq / Cerebras (ASIC LPU)             │
                     │   ├── DeepInfra / Together / Fireworks (GPU) │
                     │   ├── OpenAI / Anthropic / DeepSeek (Labs)   │
                     │   └── OTC Community Drops (Twitter/Discord)  │
                     └──────────────────────┬───────────────────────┘
                                            │
                                            ▼
                     ┌──────────────────────────────────────────────┐
                     │          Instrument Symbology Layer          │
                     │  Maps raw provider IDs -> Canonical Keys     │
                     └──────────────────────┬───────────────────────┘
                                            │
                                            ▼
                     ┌──────────────────────────────────────────────┐
                     │              Consolidated Tape               │
                     │  SQLite Time-Series Tape (tape.db)           │
                     │  • BBO (Best Bid & Offer)                    │
                     │  • Level 2 Depth of Market                   │
                     │  • Cross-Venue Spread Disparity %            │
                     │  • Multi-Month Price Trajectory              │
                     └──────────────────────┬───────────────────────┘
                                            │
                     ┌──────────────────────┴───────────────────────┐
                     │                                              │
                     ▼                                              ▼
        Terminal CLI (`ticker-plant`)              GitHub Actions Scheduled Cron
    (bbo, depth, history, export)              (Runs every 4h, commits to git)
```

---

## Key Features

1. **Kubernetes-Style Declarative Customizability**: Add any API endpoint, new provider, or obscure community GPU cluster in seconds using clean YAML manifests (`kind: FeedHandler` and `kind: InstrumentMapping`). Zero code modifications required.
2. **Multi-Venue Feed Handlers**:
   - **OpenRouter Endpoints Driver**: Unbundles OpenRouter's monolithic catalog into individual upstream infrastructure hosts (Nebius, Novita, Cerebras, DeepInfra, Hyperbolic, etc.).
   - **OpenAI-Compatible Driver**: Connects directly to `/v1/models` across any provider with JSONPath/normalizer extraction.
   - **Static Rate Card Driver**: Declarative quote sheets for frontier labs (OpenAI, Anthropic, Google) with prompt cache write/read discounts.
   - **Community / Social Drops Driver**: Ingests point-in-time quotes announced on X/Twitter or Discord.
   - **LiteLLM Archive Replayer**: Instantly backfills 12–18 months of historical rate cards from community price archives.
3. **Institutional Analytics**:
   - **BBO (Best Bid/Offer)**: Real-time top of book, median price, and cross-venue spread across all venues.
   - **Depth of Market**: Level 2 book displaying all provider quotes ranked by price, context window, and TPS.
   - **Historical Candles & Spread Trajectory**: Daily price compression tracking over 30/90/365 days.
4. **Zero-Infra Scheduled Automation**:
   - Built-in **GitHub Actions Cron Workflow** (`.github/workflows/tape-cron.yml`): Runs automatically every 4 hours on free GitHub runners, updates the tape, and commits the updated data directly to the repo. No Docker, Airflow, or active laptop required!
   - Built-in **Terminal Daemon** (`ticker-plant watch --interval 30m`): For interactive terminal use with live countdown ticker.

---

## Installation

```bash
# Clone the repository
git clone https://github.com/qzyu999/inference-exchange-ticker-plant.git
cd inference-exchange-ticker-plant

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install package
pip install -e ".[dev]"
```

---

## CLI Usage

### 1. Ingest Market Data
Run a single collection cycle across all active venue feed handlers:
```bash
ticker-plant collect
```

### 2. View National Best Bid & Offer (Top of Book)
Display the cheapest venue, highest venue, spread disparity, and median price across all models:
```bash
ticker-plant tape bbo
```
*Sample Output:*
```
                         Consolidated Tape — Best Available Offers (BBO)
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┓
┃ Instrument        ┃ Best Venue   ┃ Best Out ($) ┃ Best In ($) ┃ Median Out ┃ Highest Out ┃ Spread % ┃ Venues ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━┩
│ LLAMA-3.1-8B      │ novita       │ $0.05        │ $0.04       │ $0.08       │ $0.18       │ +260%    │      7 │
│ LLAMA-3.1-70B     │ novita       │ $0.35        │ $0.28       │ $0.50       │ $0.90       │ +157%    │      7 │
│ LLAMA-3.3-70B     │ novita       │ $0.30        │ $0.20       │ $0.38       │ $0.79       │ +163%    │      4 │
│ DEEPSEEK-V3       │ deepseek     │ $1.10        │ $0.27       │ $1.10       │ $1.10       │ +0%      │      2 │
│ DEEPSEEK-R1       │ community    │ $0.70        │ $0.40       │ $2.19       │ $2.50       │ +257%    │      6 │
│ GPT-4O            │ openai       │ $10.00       │ $2.50       │ $10.00      │ $10.00      │ +0%      │      1 │
│ CLAUDE-3.5-SONNET │ anthropic    │ $15.00       │ $3.00       │ $15.00      │ $15.00      │ +0%      │      1 │
└───────────────────┴──────────────┴──────────────┴─────────────┴────────────┴─────────────┴──────────┴────────┘
```

### 3. Level 2 Market Depth Book
Inspect the full list of competing providers for an instrument ranked by price:
```bash
ticker-plant tape depth LLAMA-3.1-70B
```
*Sample Output:*
```
                              Level 2 Market Depth — LLAMA-3.1-70B
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━┓
┃ Venue      ┃ Type          ┃ Raw Model ID                   ┃ Input ($) ┃ Cache Read ┃ Output ($) ┃ Context ┃ Age (h)  ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━┩
│ novita     │ commodity-gpu │ meta-llama/llama-3.1-70b       │ $0.28     │ —          │ $0.35      │ 131,072 │ 0.1h     │
│ deepinfra  │ commodity-gpu │ meta-llama/Llama-3.1-70B       │ $0.35     │ —          │ $0.40      │ 131,072 │ 0.1h     │
│ nebius     │ commodity-gpu │ meta-llama/Meta-Llama-3.1-70B  │ $0.35     │ —          │ $0.40      │ 131,072 │ 0.1h     │
│ cerebras   │ asic-lpu      │ llama3.1-70b                   │ $0.60     │ —          │ $0.60      │ 8,192   │ 0.1h     │
│ groq       │ asic-lpu      │ llama-3.1-70b-versatile        │ $0.59     │ —          │ $0.79      │ 131,072 │ 0.1h     │
│ together   │ commodity-gpu │ meta-llama/Meta-Llama-3.1-70B  │ $0.88     │ —          │ $0.88      │ 131,072 │ 0.1h     │
│ fireworks  │ commodity-gpu │ accounts/fireworks/models/...  │ $0.90     │ —          │ $0.90      │ 131,072 │ 0.1h     │
└━━━━━━━━━━━━┴━━━━━━━━━━━━━━━┴━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┴━━━━━━━━━━━┴━━━━━━━━━━━━┴━━━━━━━━━━━━┴━━━━━━━━━┴━━━━━━━━━━┘
```

### 4. Historical Trajectory (Price & Spread History)
Track how prices and cross-venue spreads compressed over time:
```bash
ticker-plant tape history DEEPSEEK-R1 --days 30
```

### 5. Interactive Terminal Watcher (Zero External Tools)
Keep a live watch loop running in a terminal tab:
```bash
ticker-plant watch --interval 30m
```

### 6. Export the Tape
Export normalized ticks to JSON or CSV for charting or external consumers:
```bash
ticker-plant tape export --format json --output data/tape.json
ticker-plant tape export --format csv --output data/tape.csv --latest-only
```

---

## Adding a New Venue in 5 Lines of YAML

Create a new file in `manifests/venues/<provider>.yaml`:

```yaml
apiVersion: tickerplant.inference.exchange/v1alpha1
kind: FeedHandler
metadata:
  name: hyper-cluster
  venue_type: commodity-gpu
spec:
  driver: static-ratecard
  quotes:
    - raw_model_id: "deepseek-ai/DeepSeek-R1"
      input_usd_mtok: 0.35
      output_usd_mtok: 0.65
      notes: "8x H200 PCIe cluster drop"
```

Validate your manifests immediately:
```bash
ticker-plant validate manifests/
```

---

## Scheduled Ingestion via GitHub Actions

The repository includes a ready-to-run GitHub Actions workflow (`.github/workflows/tape-cron.yml`).

Every 4 hours, GitHub's free runners:
1. Wake up and run `ticker-plant collect`.
2. Commit fresh ticks to `data/tape.db`, `data/latest_bbo.json`, and `data/latest_bbo.csv`.
3. Push changes back to the repository.

This gives you a permanent, vendor-neutral, append-only historical pricing tape running 24/7 without keeping a local server or laptop open.

---

## License

Apache-2.0 License.
