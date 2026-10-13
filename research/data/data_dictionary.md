# Data Dictionary & Methodology Register
**Project**: Frontier Inference Economics & The Inference Exchange Opportunity  
**Snapshot Date**: October 10–11, 2026 (02:55 UTC)  
**Repository**: `/Users/jaredyu/Desktop/inference-exchange-ticker-plant`

---

## 1. Primary Datasets (`research/data/`)

### `sources.csv`
Master registry of all primary vendor documentation, API rate cards, hardware datasheets, benchmark leaderboards, and market ticker feeds.
* `source_id`: Canonical identifier (e.g. `SRC-001`).
* `url`: Primary web resource address.
* `title`: Title of resource.
* `publisher`: Authoring company or institution.
* `retrieved_utc`: Timestamp of data capture.
* `evidence_type`: Classification (`official`, `independent`, `community`, `derived`).
* `notes`: Contextual qualification.

### `api_prices.csv` & `api_prices_hosted.csv`
Token rate cards and architectural limits for first-party lab APIs and hosted third-party inference providers.
* `model_key`: Canonical lowercase model identifier (e.g. `claude-opus-5.5`, `deepseek-v4.1-flash`).
* `provider`: Commercial entity billing the request.
* `model_id`: Exact raw string passed in the API payload.
* `venue_type`: One of `frontier-lab-first-party`, `open-lab-first-party`, `neocloud-inference`, `asic-lpu`, `decentralized`.
* `input_usd_mtok`: Cost per 1,000,000 prompt tokens in USD.
* `output_usd_mtok`: Cost per 1,000,000 completion tokens in USD.
* `cached_input_usd_mtok`: Rate applied to cached prompt prefix tokens.
* `batch_input_usd_mtok` / `batch_output_usd_mtok`: 24-hour asynchronous batch API rate.
* `context_window`: Maximum supported context window in tokens.
* `max_output_tokens`: Maximum single-response token limit.
* `reasoning_billed_as_output`: Boolean indicating whether internal chain-of-thought tokens bill at the output rate.

### `open_weight_models.csv`
Architectural parameters and memory footprint drivers for leading open models.
* `total_params_b`: Total parameter count in billions.
* `active_params_b`: Active parameter count routed per token in Mixture-of-Experts (MoE) architectures.
* `attention_type`: Attention mechanism (`MLA` [Multi-head Latent Attention], `GQA` [Grouped Query Attention], `MHA`).
* `kv_bytes_per_token_fp16`: Bytes allocated per token in KV cache at 16-bit precision.
  * Formula for GQA: $2 \times \text{layers} \times \text{kv\_heads} \times \text{head\_dim} \times 2$ bytes.
  * Formula for MLA: $\text{layers} \times (\text{kv\_lora\_rank} + \text{qk\_rope\_head\_dim}) \times 2$ bytes.
* `official_weight_size_gb`: Base download weight size in gigabytes.

### `hardware.csv`
Specifications and acquisition costs for purchasable deployment options.
* `hw_key`: Canonical hardware slug (e.g. `mac-studio-m5-ultra-256`, `dgx-spark-128`).
* `memory_gb`: Total unified memory or GPU VRAM capacity in gigabytes.
* `memory_bandwidth_gbs`: Sustained theoretical memory bandwidth in GB/s.
* `price_usd`: Verified retail price as of October 2026.
* `measured_inference_power_w`: Measured active wall power draw during sustained LLM generation in watts.
* `idle_power_w`: Power consumption when idle in watts.

### `benchmarks.csv`
Standardized quality evaluations across frontier and open-weight models.
* `benchmark`: Standardized benchmark suite (`SWE-bench Pro`, `SWE-bench Verified`, `AA Intelligence Index`, `Terminal-Bench 4.0`).
* `score`: Reported metric value (percentage resolved or index points).
* `run_cost_usd`: Direct cost to execute the benchmark harness per task.

---

## 2. Core Economic Formulations

### A. Memory-to-Hardware Fit
Total memory required to host a model:
$$\text{Memory}_{\text{total}} = \text{Weights} + \text{KV Cache} + \text{Framework Overhead}$$
Where:
* $\text{Weights} = \text{Total Params} \times \frac{\text{Bits per Weight}}{8} \times 1.05$ (5% quantization metadata/scales overhead).
* $\text{KV Cache} = \text{KV Bytes per Token} \times \text{Context Length} \times \text{Concurrent Streams} \times \frac{\text{KV Quant Bits}}{16}$.
* $\text{Framework Overhead} \approx 4\text{ GB to }8\text{ GB}$.

### B. Hardware Total Cost of Ownership (TCO)
$$\text{TCO}_{\text{monthly}} = \text{Amortization} + \text{Financing} + \text{Electricity} + \text{Infra/Cooling} + \text{Admin Overhead}$$
Where:
* $\text{Amortization} = \frac{\text{Purchase Price} \times (1 - \text{Salvage Rate})}{\text{Useful Life Months}}$ (Salvage = 20%, Life = 36 months).
* $\text{Financing} = \frac{\text{Purchase Price} \times \text{WACC}}{12}$ (WACC = 8.0% annual).
* $\text{Electricity} = [U \times W_{\text{active}} + (1 - U) \times W_{\text{idle}}] \times \frac{730\text{ hrs}}{1000} \times \text{PUE} \times \text{Rate}_{\text{kWh}}$.
* $U \in [0, 1]$ is the productive utilization rate.

### C. Fully Loaded Cost per Token
$$\text{Cost per }1\text{M Output Tokens} = \frac{\text{TCO}_{\text{monthly}}}{U \times 730 \times 3600 \times \text{Decode TPS}} \times 10^6$$

### D. Quality-Adjusted Task Economics
$$\text{Expected Cost per Successful Task} = \frac{\text{Cost per Attempt}}{P(\text{Success})} + [1 - P(\text{Success})] \times \text{Human Debugging Cost}$$
Where human debugging cost represents senior developer time required to diagnose and fix failed agentic attempts.
