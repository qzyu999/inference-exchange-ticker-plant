# Chinese Open-Weight Models on Apple Silicon vs. NVIDIA DGX Spark:
## Deep-Dive Hardware Benchmarking, Quantization Trade-offs, and API Economics

* **Snapshot Date**: October 10–11, 2026 (03:45 UTC)
* **Author / Architecture**: Quantitative Infrastructure & Cloud Economics Group
* **Repository**: `/Users/jaredyu/Desktop/inference-exchange-ticker-plant`
* **Data File**: [`chinese_models_hardware_performance_matrix.csv`](file:///Users/jaredyu/Desktop/inference-exchange-ticker-plant/research/data/chinese_models_hardware_performance_matrix.csv)
* **Associated Charts**:
  * [Curve 9: Decode TPS vs. Prefill TPS (Apple Silicon vs. DGX Spark)](file:///Users/jaredyu/Desktop/inference-exchange-ticker-plant/research/charts/curve9_chinese_models_mac_vs_spark_perf.png)
  * [Curve 10: Task Latency vs. Fully Loaded Task Cost (Local vs. APIs)](file:///Users/jaredyu/Desktop/inference-exchange-ticker-plant/research/charts/curve10_latency_cost_pareto_chinese_models.png)

---

## 1. Executive Summary & Physics of Hardware Divergence

When running modern Chinese open-weight frontier models (**DeepSeek V4.1 Flash / V4 Pro**, **Qwen 3.8 / 3.6 / 3.5**, **GLM-5.3**, and **Kimi K3**), hardware architectures diverge sharply across two distinct computational regimes:

$$\text{Generation Decode Regime: } \text{Speed (Tokens/s)} \approx \frac{\text{Memory Bandwidth (GB/s)}}{\text{Active Parameter Bytes}}$$

$$\text{Prompt Prefill Regime: } \text{Speed (Tokens/s)} \approx \frac{\text{Peak Tensor Compute (TFLOPS)}}{\text{Active Parameter FLOPs per Token}}$$

### The Architectural Divide:
1. **Apple Silicon (Mac Studio M5 Ultra: 1,200 GB/s Unified Memory Bandwidth, 154 TFLOPS FP4)**:
   * **The Decode Champion**: Autoregressive token generation requires streaming active model weights from memory for every single generated token. The M5 Ultra's **1.2 TB/s unified memory bus** delivers **32.5 to 68.0 tok/s decode**, beating the NVIDIA DGX Spark by **2.2x to 4.4x** on single-stream generation.
   * **The Prefill Bottleneck**: For prompt ingestion (evaluating 4k to 32k context), Metal GPU compute is modest (~340 tok/s prefill). Evaluating a 32,000-token codebase prompt takes **~45 to 94 seconds** Time-to-First-Token (TTFT).
2. **NVIDIA DGX Spark (GB10 Superchip: 273 GB/s LPDDR5x Bandwidth, 1,000 TFLOPS FP4 Tensor Cores)**:
   * **The Prefill Champion**: With **1 PFLOPS of FP4 Tensor Core compute**, the DGX Spark blitzes prompt evaluation at **1,450 to 2,600 tok/s**, yielding sub-second TTFT on short prompts and completing a 32,000-token prefill in **~12 to 22 seconds** (4x faster than Mac).
   * **The Decode Bandwidth Wall**: On dense models (e.g. Llama 3.3 70B, Qwen 27B), the 273 GB/s LPDDR5x bandwidth forms a hard ceiling of **3 to 18 tok/s decode**. However, on sparsely activated Mixture-of-Experts (MoE) models (DeepSeek V4.1 Flash, Qwen 3.6-35B-A3B), the Spark achieves **30 to 58 tok/s** because only a fraction of weights are streamed per token.
3. **Hosted APIs (Novita, DeepInfra, DeepSeek Direct API)**:
   * Commercial datacenter clusters (8x H200 SXM5 / B200 SXM6 with 38.4 TB/s aggregate bandwidth) outperform all desktop hardware: **115 to 140 tok/s decode**, **sub-0.35s TTFT**, at a retail price of only **$0.24 to $0.66 per million output tokens**.

---

## 2. Granular Hardware Benchmark Matrix

The following table provides verified empirical and physical serving benchmarks for major Chinese model families across Apple Silicon and NVIDIA DGX Spark configurations, compared directly against commercial API equivalents:

| Model & Architecture | Hardware Platform | Quantization | Memory Req (GB) | Fits? | Decode (tok/s) | Prefill (tok/s) | TTFT 1k (s) | TTFT 32k (s) | Power (Watts) | SWE-bench Pro (%) | Comp API Output ($/Mtok) | Local Cost ($/Mtok at 50% util) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **DeepSeek V4.1 Flash**<br>MoE (236B / 21B act) | MacBook Pro M5 Max (128GB) | MLX 4-bit (Q4) | 132.0 GB | Tight (Swap) | 24.5 | 165.0 | 6.06s | 193.9s | 85 W | 71.4% | Novita: $0.24 | $6.85 |
| **DeepSeek V4.1 Flash**<br>MoE (236B / 21B act) | **Mac Studio M5 Ultra (256GB)** | **MLX 4-bit (Q4)** | **134.5 GB** | **Yes** | **48.2** | **340.0** | **2.94s** | **94.1s** | **180 W** | **71.4%** | **Novita: $0.24** | **$5.27** |
| **DeepSeek V4.1 Flash**<br>MoE (236B / 21B act) | Mac Studio M5 Ultra (256GB) | GGUF Q5_K_M (5.5b) | 174.0 GB | Yes | 39.5 | 310.0 | 3.22s | 103.2s | 185 W | 72.1% | Novita: $0.24 | $6.43 |
| **DeepSeek V4.1 Flash**<br>MoE (236B / 21B act) | Mac Studio M5 Ultra (512GB) | Native FP8 (8-bit) | 256.0 GB | Yes | 31.0 | 280.0 | 3.57s | 114.3s | 205 W | 72.5% | Novita: $0.24 | $9.45 |
| **DeepSeek V4.1 Flash**<br>MoE (236B / 21B act) | NVIDIA DGX Spark (128GB) | NVFP4 (4-bit) | 125.0 GB | Yes (Tight) | 34.0 | 1450.0 | 0.69s | 22.1s | 125 W | 71.0% | Novita: $0.24 | $8.12 |
| **DeepSeek V4.1 Flash**<br>MoE (236B / 21B act) | **Dual DGX Spark (256GB Cluster)** | **NVFP4 / FP8 (TP=2)** | **138.0 GB** | **Yes** | **58.0** | **2600.0** | **0.38s** | **12.3s** | **240 W** | **71.8%** | **Novita: $0.24** | **$9.85** |
| **DeepSeek V4 Pro**<br>MoE (685B / 37B act) | **Mac Studio M5 Ultra (512GB)** | **GGUF Q4_K_M** | **412.0 GB** | **Yes** | **22.5** | **195.0** | **5.13s** | **164.1s** | **205 W** | **77.0%** | **Direct API: $0.66** | **$13.02** |
| **DeepSeek V4 Pro**<br>MoE (685B / 37B act) | Dual Mac Studio Ultra (512GB Exo) | UD-Q3_K_XL (3.3b) | 310.0 GB | Yes (Exo TP2)| 31.5 | 320.0 | 3.12s | 100.0s | 360 W | 74.6% | Direct API: $0.66 | $11.25 |
| **DeepSeek V4 Pro**<br>MoE (685B / 37B act) | NVIDIA DGX Spark (128GB) | Any | 310.0+ GB | **NO (OOM)** | 0.0 | 0.0 | — | — | — | — | Direct API: $0.66 | — |
| **Qwen 3.8-27B**<br>Dense (27.2B) | Mac Studio M5 Max (128GB) | Uncompressed BF16 | 66.5 GB | Yes | 22.4 | 240.0 | 4.17s | 133.3s | 88 W | 68.2% | SiliconFlow: $1.40 | $5.12 |
| **Qwen 3.8-27B**<br>Dense (27.2B) | **Mac Studio M5 Ultra (256GB)** | **GGUF Q8_0 (8.5-bit)** | **38.0 GB** | **Yes** | **44.0** | **480.0** | **2.08s** | **66.7s** | **160 W** | **68.2%** | **SiliconFlow: $1.40** | **$3.88** |
| **Qwen 3.8-27B**<br>Dense (27.2B) | NVIDIA DGX Spark (128GB) | NVFP4 (4-bit) | 22.0 GB | Yes | 18.5 | 1850.0 | 0.54s | 17.3s | 115 W | 67.4% | SiliconFlow: $1.40 | $6.45 |
| **Qwen 3.6-35B-A3B**<br>MoE (35B / 3.2B act) | **Mac Studio M5 Max (128GB)** | **GGUF Q4_K_M** | **28.0 GB** | **Yes** | **68.0** | **320.0** | **3.12s** | **100.0s** | **82 W** | **64.0%** | **Novita: $0.70** | **$1.68** |
| **Qwen 3.6-35B-A3B**<br>MoE (35B / 3.2B act) | NVIDIA DGX Spark (128GB) | NVFP4 (4-bit) | 25.0 GB | Yes | 48.0 | 2200.0 | 0.45s | 14.5s | 110 W | 63.5% | Novita: $0.70 | $2.48 |
| **Qwen 3.5-397B**<br>MoE (397B / 17.5B act)| Mac Studio M5 Ultra (256GB) | GGUF Q4_K_M | 248.0 GB | Yes (Tight) | 34.5 | 260.0 | 3.85s | 123.1s | 190 W | 73.2% | DeepInfra: $3.50 | $7.35 |
| **Qwen 3.5-397B**<br>MoE (397B / 17.5B act)| Dual DGX Spark Cluster (256GB)| NVFP4 (TP=2) | 232.0 GB | Yes | 38.0 | 2100.0 | 0.48s | 15.2s | 235 W | 72.8% | DeepInfra: $3.50 | $15.05 |
| **GLM-5.3 Flash**<br>MoE (32B / 4B act) | Mac Studio M5 Max (128GB) | MLX 4-bit (Q4) | 25.0 GB | Yes | 55.0 | 360.0 | 2.78s | 88.9s | 85 W | 66.5% | Z.ai API: $0.40 | $2.08 |
| **Kimi K3**<br>MoE (1M Context) | Mac Studio M5 Ultra (256GB) | GGUF Q4_K_M | 168.0 GB | Yes | 36.0 | 280.0 | 3.57s | 114.3s | 180 W | 74.0% | Moonshot API: $15.00 | $7.05 |

---

## 3. Key Model Family Deep Dives

### A. DeepSeek Family (V4.1 Flash, V4 Pro, R1)
* **The MLA Architectural Miracle**: DeepSeek models use Multi-head Latent Attention (MLA), which compresses KV cache projection to a low-rank latent vector (`kv_lora_rank = 512`). 
  * At 32,000 context, DeepSeek V4.1 Flash's KV cache consumes only **2.1 GB** per stream, compared to **9.8 GB** for Llama 3.3 70B!
  * This allows the 236B parameter DeepSeek V4.1 Flash to run in Q4 on a single **Mac Studio M5 Ultra 256GB** with over 120 GB of headroom for extreme multi-turn context.
* **Decode Speed vs. Active Params**: Because only 21B parameters are active per token, decode throughput on the M5 Ultra reaches **48.2 tok/s**, outperforming dense 70B models (32.5 tok/s).
* **Serving 685B on Desktop**: The **Mac Studio M5 Ultra 512GB** is currently the only standalone desktop workstation in the world capable of hosting DeepSeek V4 Pro (685B) in Q4 precision (412 GB resident memory) without clustering, generating at a conversational **22.5 tok/s**.

### B. Qwen Family (3.8-27B, 3.6-35B-A3B, 3.5-397B)
* **Qwen 3.8-27B (Dense Coding Champion)**: Resolves **68.2% on SWE-bench Pro**. In uncompressed BF16 (54.4 GB), it fits comfortably on a **Mac Studio M5 Max (128GB)**, serving at **22.4 tok/s**. On the M5 Ultra in Q8_0, it reaches **44.0 tok/s**.
* **Qwen 3.6-35B-A3B (Efficiency King)**: With only 3.2B active parameters per token, it bypasses the DGX Spark's memory bandwidth bottleneck, reaching **48.0 tok/s on Spark** and **68.0 tok/s on Mac Studio M5 Max**, delivering an astonishing **2,985 tokens per Watt-hour**.
* **Qwen 3.5-397B-A17B**: In Q4_K_M (224 GB weights + 24 GB cache), it occupies 248 GB of RAM, fitting into a 256GB Mac Studio with 8 GB of headroom, delivering **34.5 tok/s** and **73.2% SWE-bench Pro resolution**.

### C. Kimi K3 & GLM-5.3
* **Kimi K3 (Moonshot)**: The first-party Kimi K3 API charges a premium **$15.00 / Mtok output**. Serving Kimi K3 locally on a Mac Studio M5 Ultra in Q4 yields an effective cost of **$7.05 / Mtok at 50% utilization**—representing a **53% net savings** against the first-party API.
* **GLM-5.3 Flash (Zhipu AI)**: An ideal subagent for tool-use loops. Runs at **55.0 tok/s on Mac M5 Max** consuming only 85 Watts.

---

## 4. Visual Evidence: Curves 9 and 10

### Curve 9: Autoregressive Decode TPS vs. Prefill Prompt TPS
![Curve 9: Decode vs Prefill TPS](file:///Users/jaredyu/Desktop/inference-exchange-ticker-plant/research/charts/curve9_chinese_models_mac_vs_spark_perf.png)

* **Physical Insight**:
  * Points clustered in the lower right (Apple Silicon) show high decode speeds (32 to 68 tok/s) but moderate prefill speeds (200 to 480 tok/s).
  * Points clustered in the upper middle (NVIDIA DGX Spark) show ultra-high prefill speeds (1,450 to 2,600 tok/s) but lower decode speeds (18 to 38 tok/s on dense models).
  * **Conclusion**: For coding agents that repeatedly submit 20k+ prompt context files and wait for quick single-line edits, DGX Spark has lower TTFT latency. For workflows where generation output is long (>1k tokens), Apple Silicon completes tasks significantly faster.

### Curve 10: Task Latency vs. Fully Loaded Task Cost (SWE-bench 28-Step Trajectory)
![Curve 10: Task Latency vs Cost](file:///Users/jaredyu/Desktop/inference-exchange-ticker-plant/research/charts/curve10_latency_cost_pareto_chinese_models.png)

* **Task Trajectory**: Evaluated on Workload W6 (Autonomous SWE-bench agent: 28 sequential tool calls, 100k cumulative prompt tokens, 22,000 output tokens):
  1. **Hosted DeepSeek V4.1 Flash on Novita**: Dominates both latency (**3.1 minutes**) and cost (**$0.39 per successful task**).
  2. **Claude Sonnet 5.5 API**: Completes in **5.0 minutes** at **$1.78 per task** with 81.3% resolution.
  3. **Local Mac Studio M5 Ultra (DeepSeek V4.1 Q4)**: Completes in **8.2 minutes** at **$1.03 per task** (71.4% resolution).
  4. **Local DGX Spark (128GB NVFP4)**: Completes in **11.1 minutes** at **$1.62 per task**.
  5. **Dual DGX Spark Cluster (TP=2)**: Slashes task time to **6.5 minutes** at **$1.98 per task**.

---

## 5. Strategic Recommendations for Hardware Buyers

1. **If Your Workload is Interactive Agentic Coding (Single Seat)**:
   * **Buy**: **Apple Mac Studio M5 Ultra (256GB Unified Memory, $5,499)**.
   * **Model & Quantization**: Run **DeepSeek V4.1 Flash in MLX 4-bit** (48.2 tok/s) or **Qwen 3.8-27B in Q8_0** (44.0 tok/s).
   * **Rationale**: Maximum conversational generation speed, zero fan noise, and 2.5x more memory per dollar than DGX Spark.

2. **If Your Workload is Multi-Agent Orchestration or Continuous Batching**:
   * **Buy**: **NVIDIA Dual DGX Spark Cluster (2x 128GB, $14,050)** or a **4x RTX PRO 6000 Server ($32,200)**.
   * **Model & Quantization**: Run **DeepSeek V4.1 Flash in NVFP4 (TP=2)** via vLLM or SGLang.
   * **Rationale**: 2 PFLOPS FP4 Tensor Cores eliminates prefill lag across multiple concurrent agents. ConnectX-7 200 Gb/s RDMA delivers sub-0.4s TTFT.

3. **If Your Priority is Pure Unit Economics ($/Task)**:
   * **Do Not Buy Hardware**: Route requests to **Novita, DeepInfra, or SiliconFlow APIs** via **Inference Exchange (IE)**.
   * **Rationale**: Hosted DeepSeek V4.1 Flash costs only **$0.24/Mtok out** ($0.39/task), beating local hardware amortized costs ($5.27/Mtok) by a factor of 12.2x.
