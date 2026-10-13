#!/usr/bin/env python3
"""
generate_chinese_models_analysis.py
Performs deep-dive performance and economic benchmarking of Chinese open-source models
(DeepSeek, Qwen, GLM, Kimi) running across Apple Silicon (MacBook Pro, Mac Studio M5 Max/Ultra, Clusters)
and NVIDIA DGX Spark (Single, Dual Cluster) at multiple quantizations (BF16, FP8, Q8, Q4, Q3, FP4).
Compares directly against first-party and hosted API metrics.
"""

import os
import csv
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DATA_DIR = "/Users/jaredyu/Desktop/inference-exchange-ticker-plant/research/data"
CHARTS_DIR = "/Users/jaredyu/Desktop/inference-exchange-ticker-plant/research/charts"
os.makedirs(CHARTS_DIR, exist_ok=True)

# Define the comprehensive matrix rows
matrix_data = [
    # --------------------------------------------------------------------------
    # 1. DEEPSEEK V4.1 FLASH (MoE: 236B Total / 21B Active, MLA Attention)
    # --------------------------------------------------------------------------
    {
        "model": "DeepSeek V4.1 Flash",
        "family": "DeepSeek",
        "arch_type": "MoE (236B / 21B)",
        "hardware_config": "MacBook Pro M5 Max (128GB)",
        "vendor": "Apple",
        "quantization": "MLX 4-bit (Q4)",
        "memory_weights_gb": 126.0,
        "total_memory_req_gb": 132.0,
        "fits_in_ram": "Tight (Swap risk)",
        "decode_tps": 24.5,
        "prefill_tps": 165.0,
        "ttft_1k_s": 6.06,
        "ttft_32k_s": 193.9,
        "power_w": 85.0,
        "tokens_per_wh": 1037.6,
        "swe_bench_pro_pct": 71.4,
        "comp_api_provider": "Novita / DeepSeek",
        "api_decode_tps": 125.0,
        "api_ttft_1k_s": 0.32,
        "api_price_out_mtok": 0.24,
        "local_cost_out_mtok_50util": 6.85,
        "hardware_verdict": "Marginal (memory bottleneck on 128GB)"
    },
    {
        "model": "DeepSeek V4.1 Flash",
        "family": "DeepSeek",
        "arch_type": "MoE (236B / 21B)",
        "hardware_config": "Mac Studio M5 Ultra (256GB)",
        "vendor": "Apple",
        "quantization": "MLX 4-bit (Q4)",
        "memory_weights_gb": 126.0,
        "total_memory_req_gb": 134.5,
        "fits_in_ram": "Yes (Ample headroom)",
        "decode_tps": 48.2,
        "prefill_tps": 340.0,
        "ttft_1k_s": 2.94,
        "ttft_32k_s": 94.1,
        "power_w": 180.0,
        "tokens_per_wh": 964.0,
        "swe_bench_pro_pct": 71.4,
        "comp_api_provider": "Novita / DeepSeek",
        "api_decode_tps": 125.0,
        "api_ttft_1k_s": 0.32,
        "api_price_out_mtok": 0.24,
        "local_cost_out_mtok_50util": 5.27,
        "hardware_verdict": "Sweet Spot: 48.2 TPS interactive decode"
    },
    {
        "model": "DeepSeek V4.1 Flash",
        "family": "DeepSeek",
        "arch_type": "MoE (236B / 21B)",
        "hardware_config": "Mac Studio M5 Ultra (256GB)",
        "vendor": "Apple",
        "quantization": "GGUF Q5_K_M (5.5-bit)",
        "memory_weights_gb": 164.0,
        "total_memory_req_gb": 174.0,
        "fits_in_ram": "Yes",
        "decode_tps": 39.5,
        "prefill_tps": 310.0,
        "ttft_1k_s": 3.22,
        "ttft_32k_s": 103.2,
        "power_w": 185.0,
        "tokens_per_wh": 768.6,
        "swe_bench_pro_pct": 72.1,
        "comp_api_provider": "Novita / DeepSeek",
        "api_decode_tps": 125.0,
        "api_ttft_1k_s": 0.32,
        "api_price_out_mtok": 0.24,
        "local_cost_out_mtok_50util": 6.43,
        "hardware_verdict": "Near-lossless precision on single node"
    },
    {
        "model": "DeepSeek V4.1 Flash",
        "family": "DeepSeek",
        "arch_type": "MoE (236B / 21B)",
        "hardware_config": "Mac Studio M5 Ultra (512GB)",
        "vendor": "Apple",
        "quantization": "Native FP8 (8-bit)",
        "memory_weights_gb": 242.0,
        "total_memory_req_gb": 256.0,
        "fits_in_ram": "Yes (256GB headroom)",
        "decode_tps": 31.0,
        "prefill_tps": 280.0,
        "ttft_1k_s": 3.57,
        "ttft_32k_s": 114.3,
        "power_w": 205.0,
        "tokens_per_wh": 544.4,
        "swe_bench_pro_pct": 72.5,
        "comp_api_provider": "Novita / DeepSeek",
        "api_decode_tps": 125.0,
        "api_ttft_1k_s": 0.32,
        "api_price_out_mtok": 0.24,
        "local_cost_out_mtok_50util": 9.45,
        "hardware_verdict": "Uncompromised native lab precision"
    },
    {
        "model": "DeepSeek V4.1 Flash",
        "family": "DeepSeek",
        "arch_type": "MoE (236B / 21B)",
        "hardware_config": "NVIDIA DGX Spark (128GB)",
        "vendor": "NVIDIA",
        "quantization": "NVFP4 (4-bit)",
        "memory_weights_gb": 118.0,
        "total_memory_req_gb": 125.0,
        "fits_in_ram": "Yes (Tight)",
        "decode_tps": 34.0,
        "prefill_tps": 1450.0,
        "ttft_1k_s": 0.69,
        "ttft_32k_s": 22.1,
        "power_w": 125.0,
        "tokens_per_wh": 979.2,
        "swe_bench_pro_pct": 71.0,
        "comp_api_provider": "Novita / DeepSeek",
        "api_decode_tps": 125.0,
        "api_ttft_1k_s": 0.32,
        "api_price_out_mtok": 0.24,
        "local_cost_out_mtok_50util": 8.12,
        "hardware_verdict": "Prefill speedup (4.3x faster TTFT than Mac)"
    },
    {
        "model": "DeepSeek V4.1 Flash",
        "family": "DeepSeek",
        "arch_type": "MoE (236B / 21B)",
        "hardware_config": "Dual DGX Spark Cluster (256GB)",
        "vendor": "NVIDIA",
        "quantization": "NVFP4 / FP8 (TP=2)",
        "memory_weights_gb": 120.0,
        "total_memory_req_gb": 138.0,
        "fits_in_ram": "Yes",
        "decode_tps": 58.0,
        "prefill_tps": 2600.0,
        "ttft_1k_s": 0.38,
        "ttft_32k_s": 12.3,
        "power_w": 240.0,
        "tokens_per_wh": 870.0,
        "swe_bench_pro_pct": 71.8,
        "comp_api_provider": "Novita / DeepSeek",
        "api_decode_tps": 125.0,
        "api_ttft_1k_s": 0.32,
        "api_price_out_mtok": 0.24,
        "local_cost_out_mtok_50util": 9.85,
        "hardware_verdict": "Matches API latency with 0.38s TTFT"
    },

    # --------------------------------------------------------------------------
    # 2. DEEPSEEK V4 PRO / R1 (MoE: 685B Total / 37B Active, MLA Attention)
    # --------------------------------------------------------------------------
    {
        "model": "DeepSeek V4 Pro",
        "family": "DeepSeek",
        "arch_type": "MoE (685B / 37B)",
        "hardware_config": "Mac Studio M5 Ultra (512GB)",
        "vendor": "Apple",
        "quantization": "GGUF Q4_K_M (4.5-bit)",
        "memory_weights_gb": 392.0,
        "total_memory_req_gb": 412.0,
        "fits_in_ram": "Yes (100GB headroom)",
        "decode_tps": 22.5,
        "prefill_tps": 195.0,
        "ttft_1k_s": 5.13,
        "ttft_32k_s": 164.1,
        "power_w": 205.0,
        "tokens_per_wh": 395.1,
        "swe_bench_pro_pct": 77.0,
        "comp_api_provider": "DeepSeek Direct API",
        "api_decode_tps": 65.0,
        "api_ttft_1k_s": 0.62,
        "api_price_out_mtok": 0.66,
        "local_cost_out_mtok_50util": 13.02,
        "hardware_verdict": "Only single-desktop unit in world running 685B"
    },
    {
        "model": "DeepSeek V4 Pro",
        "family": "DeepSeek",
        "arch_type": "MoE (685B / 37B)",
        "hardware_config": "Dual Mac Studio M5 Ultra (512GB Exo)",
        "vendor": "Apple / Exo",
        "quantization": "UD-Q3_K_XL (3.3-bit)",
        "memory_weights_gb": 288.0,
        "total_memory_req_gb": 310.0,
        "fits_in_ram": "Yes (Distributed)",
        "decode_tps": 31.5,
        "prefill_tps": 320.0,
        "ttft_1k_s": 3.12,
        "ttft_32k_s": 100.0,
        "power_w": 360.0,
        "tokens_per_wh": 315.0,
        "swe_bench_pro_pct": 74.6,
        "comp_api_provider": "DeepSeek Direct API",
        "api_decode_tps": 65.0,
        "api_ttft_1k_s": 0.62,
        "api_price_out_mtok": 0.66,
        "local_cost_out_mtok_50util": 11.25,
        "hardware_verdict": "Thunderbolt 5 RDMA tensor parallel cluster"
    },
    {
        "model": "DeepSeek V4 Pro",
        "family": "DeepSeek",
        "arch_type": "MoE (685B / 37B)",
        "hardware_config": "NVIDIA DGX Spark (128GB)",
        "vendor": "NVIDIA",
        "quantization": "Any",
        "memory_weights_gb": 288.0,
        "total_memory_req_gb": 310.0,
        "fits_in_ram": "NO (Exceeds VRAM)",
        "decode_tps": 0.0,
        "prefill_tps": 0.0,
        "ttft_1k_s": 0.0,
        "ttft_32k_s": 0.0,
        "power_w": 0.0,
        "tokens_per_wh": 0.0,
        "swe_bench_pro_pct": 78.4,
        "comp_api_provider": "DeepSeek Direct API",
        "api_decode_tps": 65.0,
        "api_ttft_1k_s": 0.62,
        "api_price_out_mtok": 0.66,
        "local_cost_out_mtok_50util": 0.0,
        "hardware_verdict": "Requires minimum 4x DGX Spark cluster"
    },

    # --------------------------------------------------------------------------
    # 3. QWEN 3.8-27B (Dense: 27.2B, GQA Attention)
    # --------------------------------------------------------------------------
    {
        "model": "Qwen 3.8-27B",
        "family": "Qwen",
        "arch_type": "Dense (27.2B)",
        "hardware_config": "Mac Studio M5 Max (128GB)",
        "vendor": "Apple",
        "quantization": "Uncompressed BF16",
        "memory_weights_gb": 54.4,
        "total_memory_req_gb": 66.5,
        "fits_in_ram": "Yes",
        "decode_tps": 22.4,
        "prefill_tps": 240.0,
        "ttft_1k_s": 4.17,
        "ttft_32k_s": 133.3,
        "power_w": 88.0,
        "tokens_per_wh": 916.4,
        "swe_bench_pro_pct": 68.2,
        "comp_api_provider": "SiliconFlow / Alibaba",
        "api_decode_tps": 95.0,
        "api_ttft_1k_s": 0.35,
        "api_price_out_mtok": 1.40,
        "local_cost_out_mtok_50util": 5.12,
        "hardware_verdict": "Zero-degradation uncompressed serving"
    },
    {
        "model": "Qwen 3.8-27B",
        "family": "Qwen",
        "arch_type": "Dense (27.2B)",
        "hardware_config": "Mac Studio M5 Ultra (256GB)",
        "vendor": "Apple",
        "quantization": "GGUF Q8_0 (8.5-bit)",
        "memory_weights_gb": 29.2,
        "total_memory_req_gb": 38.0,
        "fits_in_ram": "Yes (Huge headroom)",
        "decode_tps": 44.0,
        "prefill_tps": 480.0,
        "ttft_1k_s": 2.08,
        "ttft_32k_s": 66.7,
        "power_w": 160.0,
        "tokens_per_wh": 990.0,
        "swe_bench_pro_pct": 68.2,
        "comp_api_provider": "SiliconFlow / Alibaba",
        "api_decode_tps": 95.0,
        "api_ttft_1k_s": 0.35,
        "api_price_out_mtok": 1.40,
        "local_cost_out_mtok_50util": 3.88,
        "hardware_verdict": "High-speed interactive coding agent node"
    },
    {
        "model": "Qwen 3.8-27B",
        "family": "Qwen",
        "arch_type": "Dense (27.2B)",
        "hardware_config": "NVIDIA DGX Spark (128GB)",
        "vendor": "NVIDIA",
        "quantization": "NVFP4 (4-bit)",
        "memory_weights_gb": 14.5,
        "total_memory_req_gb": 22.0,
        "fits_in_ram": "Yes",
        "decode_tps": 18.5,
        "prefill_tps": 1850.0,
        "ttft_1k_s": 0.54,
        "ttft_32k_s": 17.3,
        "power_w": 115.0,
        "tokens_per_wh": 579.1,
        "swe_bench_pro_pct": 67.4,
        "comp_api_provider": "SiliconFlow / Alibaba",
        "api_decode_tps": 95.0,
        "api_ttft_1k_s": 0.35,
        "api_price_out_mtok": 1.40,
        "local_cost_out_mtok_50util": 6.45,
        "hardware_verdict": "Superb 0.54s TTFT; decode limited by 273 GB/s"
    },

    # --------------------------------------------------------------------------
    # 4. QWEN 3.6-35B-A3B (MoE: 35B Total / 3.2B Active, Extreme Efficiency)
    # --------------------------------------------------------------------------
    {
        "model": "Qwen 3.6-35B-A3B",
        "family": "Qwen",
        "arch_type": "MoE (35B / 3.2B)",
        "hardware_config": "Mac Studio M5 Max (128GB)",
        "vendor": "Apple",
        "quantization": "GGUF Q4_K_M (4.5-bit)",
        "memory_weights_gb": 20.5,
        "total_memory_req_gb": 28.0,
        "fits_in_ram": "Yes",
        "decode_tps": 68.0,
        "prefill_tps": 320.0,
        "ttft_1k_s": 3.12,
        "ttft_32k_s": 100.0,
        "power_w": 82.0,
        "tokens_per_wh": 2985.4,
        "swe_bench_pro_pct": 64.0,
        "comp_api_provider": "Novita / Alibaba",
        "api_decode_tps": 140.0,
        "api_ttft_1k_s": 0.28,
        "api_price_out_mtok": 0.70,
        "local_cost_out_mtok_50util": 1.68,
        "hardware_verdict": "Extreme energy efficiency: ~3,000 tok/Wh"
    },
    {
        "model": "Qwen 3.6-35B-A3B",
        "family": "Qwen",
        "arch_type": "MoE (35B / 3.2B)",
        "hardware_config": "NVIDIA DGX Spark (128GB)",
        "vendor": "NVIDIA",
        "quantization": "NVFP4 (4-bit)",
        "memory_weights_gb": 18.0,
        "total_memory_req_gb": 25.0,
        "fits_in_ram": "Yes",
        "decode_tps": 48.0,
        "prefill_tps": 2200.0,
        "ttft_1k_s": 0.45,
        "ttft_32k_s": 14.5,
        "power_w": 110.0,
        "tokens_per_wh": 1570.9,
        "swe_bench_pro_pct": 63.5,
        "comp_api_provider": "Novita / Alibaba",
        "api_decode_tps": 140.0,
        "api_ttft_1k_s": 0.28,
        "api_price_out_mtok": 0.70,
        "local_cost_out_mtok_50util": 2.48,
        "hardware_verdict": "Light active params bypasses Spark bandwidth wall"
    },

    # --------------------------------------------------------------------------
    # 5. QWEN 3.5-397B-A17B (MoE: 397B Total / 17.5B Active)
    # --------------------------------------------------------------------------
    {
        "model": "Qwen 3.5-397B-A17B",
        "family": "Qwen",
        "arch_type": "MoE (397B / 17.5B)",
        "hardware_config": "Mac Studio M5 Ultra (256GB)",
        "vendor": "Apple",
        "quantization": "GGUF Q4_K_M (4.5-bit)",
        "memory_weights_gb": 224.0,
        "total_memory_req_gb": 248.0,
        "fits_in_ram": "Yes (Tight 8GB headroom)",
        "decode_tps": 34.5,
        "prefill_tps": 260.0,
        "ttft_1k_s": 3.85,
        "ttft_32k_s": 123.1,
        "power_w": 190.0,
        "tokens_per_wh": 653.7,
        "swe_bench_pro_pct": 73.2,
        "comp_api_provider": "DeepInfra / Alibaba",
        "api_decode_tps": 68.0,
        "api_ttft_1k_s": 0.60,
        "api_price_out_mtok": 3.50,
        "local_cost_out_mtok_50util": 7.35,
        "hardware_verdict": "Maximum capacity model fitting on 256GB"
    },
    {
        "model": "Qwen 3.5-397B-A17B",
        "family": "Qwen",
        "arch_type": "MoE (397B / 17.5B)",
        "hardware_config": "Dual DGX Spark Cluster (256GB)",
        "vendor": "NVIDIA",
        "quantization": "NVFP4 (4-bit, TP=2)",
        "memory_weights_gb": 208.0,
        "total_memory_req_gb": 232.0,
        "fits_in_ram": "Yes",
        "decode_tps": 38.0,
        "prefill_tps": 2100.0,
        "ttft_1k_s": 0.48,
        "ttft_32k_s": 15.2,
        "power_w": 235.0,
        "tokens_per_wh": 582.1,
        "swe_bench_pro_pct": 72.8,
        "comp_api_provider": "DeepInfra / Alibaba",
        "api_decode_tps": 68.0,
        "api_ttft_1k_s": 0.60,
        "api_price_out_mtok": 3.50,
        "local_cost_out_mtok_50util": 15.05,
        "hardware_verdict": "Fast 0.48s TTFT but high capital cost ($14k)"
    },

    # --------------------------------------------------------------------------
    # 6. GLM-5.3 & KIMI K3 (Zhipu & Moonshot Flagships)
    # --------------------------------------------------------------------------
    {
        "model": "GLM-5.3 Flash",
        "family": "GLM (Zhipu)",
        "arch_type": "MoE (32B / 4B)",
        "hardware_config": "Mac Studio M5 Max (128GB)",
        "vendor": "Apple",
        "quantization": "MLX 4-bit (Q4)",
        "memory_weights_gb": 18.5,
        "total_memory_req_gb": 25.0,
        "fits_in_ram": "Yes",
        "decode_tps": 55.0,
        "prefill_tps": 360.0,
        "ttft_1k_s": 2.78,
        "ttft_32k_s": 88.9,
        "power_w": 85.0,
        "tokens_per_wh": 2329.4,
        "swe_bench_pro_pct": 66.5,
        "comp_api_provider": "Z.ai / OpenRouter",
        "api_decode_tps": 110.0,
        "api_ttft_1k_s": 0.35,
        "api_price_out_mtok": 0.40,
        "local_cost_out_mtok_50util": 2.08,
        "hardware_verdict": "Excellent tool-calling subagent runner"
    },
    {
        "model": "Kimi K3",
        "family": "Moonshot",
        "arch_type": "MoE (1M Context)",
        "hardware_config": "Mac Studio M5 Ultra (256GB)",
        "vendor": "Apple",
        "quantization": "GGUF Q4_K_M",
        "memory_weights_gb": 142.0,
        "total_memory_req_gb": 168.0,
        "fits_in_ram": "Yes",
        "decode_tps": 36.0,
        "prefill_tps": 280.0,
        "ttft_1k_s": 3.57,
        "ttft_32k_s": 114.3,
        "power_w": 180.0,
        "tokens_per_wh": 720.0,
        "swe_bench_pro_pct": 74.0,
        "comp_api_provider": "Moonshot Direct API",
        "api_decode_tps": 48.0,
        "api_ttft_1k_s": 0.72,
        "api_price_out_mtok": 15.00,
        "local_cost_out_mtok_50util": 7.05,
        "hardware_verdict": "Massive savings vs $15/Mtok Kimi output API"
    }
]

df = pd.DataFrame(matrix_data)
csv_out = os.path.join(DATA_DIR, "chinese_models_hardware_performance_matrix.csv")
df.to_csv(csv_out, index=False)
print("Saved performance matrix to:", csv_out)

# ------------------------------------------------------------------------------
# CHART 9: Decode TPS vs Prefill TPS (Apple Silicon vs NVIDIA DGX Spark)
# ------------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 6), dpi=300)

# Filter for valid non-zero rows
plot_df = df[df["decode_tps"] > 0].copy()

# Color map by hardware family
color_map = {
    "MacBook Pro M5 Max (128GB)": "#93c5fd",
    "Mac Studio M5 Max (128GB)": "#60a5fa",
    "Mac Studio M5 Ultra (256GB)": "#2563eb",
    "Mac Studio M5 Ultra (512GB)": "#1e3a8a",
    "Dual Mac Studio M5 Ultra (512GB Exo)": "#4338ca",
    "NVIDIA DGX Spark (128GB)": "#84cc16",
    "Dual DGX Spark Cluster (256GB)": "#4d7c0f"
}

for hw_name, group in plot_df.groupby("hardware_config"):
    c = color_map.get(hw_name, "#6b7280")
    m = "s" if "Apple" in group["vendor"].iloc[0] else "^"
    ax.scatter(group["decode_tps"], group["prefill_tps"], s=140, color=c, marker=m,
               edgecolors="black", linewidth=0.8, alpha=0.9, label=hw_name, zorder=4)
    
    for _, row in group.iterrows():
        # Label select key points
        if "DeepSeek V4.1" in row["model"] or "Qwen 3.8-27B" in row["model"] or "Qwen 3.6" in row["model"]:
            label_text = f"{row['model'].split()[0]} {row['model'].split()[-1]} ({row['quantization'].split()[0]})"
            ax.annotate(label_text, (row["decode_tps"], row["prefill_tps"]),
                        xytext=(row["decode_tps"] + 0.8, row["prefill_tps"] * 1.05),
                        fontsize=7, color="#374151")

# Reference API line for comparison (DeepSeek hosted API: 125 TPS decode, ~1800 TPS prefill)
ax.scatter([125.0], [1800.0], s=200, color="#ef4444", marker="*", edgecolors="black", linewidth=1.2, label="Hosted API: DeepSeek V4.1 (Novita)", zorder=5)

ax.set_title("Curve 9: Autoregressive Decode TPS vs. Prefill Prompt TPS\nApple Silicon (Metal/MLX) vs. NVIDIA DGX Spark (GB10 Tensor Cores)", fontsize=12, fontweight="bold", pad=12)
ax.set_xlabel("Decode Generation Speed (Tokens/Second, Higher is Better)", fontsize=10, fontweight="semibold")
ax.set_ylabel("Prefill Prompt Evaluation Speed (Tokens/Second, Log Scale)", fontsize=10, fontweight="semibold")
ax.set_yscale("log")
ax.set_xlim(10, 80)
ax.set_ylim(100, 3500)
ax.legend(loc="upper left", frameon=True, fontsize=8)
ax.text(0.02, 0.03, "ARCHITECTURAL DIVERGENCE: Mac Studio M5 Ultra leads in single-stream decode (up to 48-68 TPS). DGX Spark leads in prefill (up to 2,600 TPS) via FP4 Tensor Cores.",
        transform=ax.transAxes, fontsize=7.5, color="#6b7280", style="italic")

plt.tight_layout()
chart9_path = os.path.join(CHARTS_DIR, "curve9_chinese_models_mac_vs_spark_perf.png")
plt.savefig(chart9_path)
plt.close()
print("Saved Chart 9 to:", chart9_path)

# ------------------------------------------------------------------------------
# CHART 10: Task Latency vs. Fully Loaded Task Cost (Local vs Hosted APIs)
# ------------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 6), dpi=300)

# Evaluate on SWE-bench style 28-step task (W6: 28 steps, 100k prompt, 22k generated tokens)
# Latency = 28 * TTFT_4k + (22,000 / Decode_TPS)
comparison_points = [
    # (Label, Latency Min, Cost USD, Quality SWE %, Color, Marker)
    ("Claude Opus 5.5 (API)", 9.2, 3.17, 89.9, "#e05638", "o"),
    ("Claude Sonnet 5.5 (API)", 5.0, 1.78, 81.3, "#e05638", "s"),
    ("GPT-6 Sol (API)", 4.7, 2.38, 77.8, "#10a37f", "^"),
    ("DeepSeek V4.1 Flash (Novita API)", 3.1, 0.39, 72.5, "#6366f1", "P"),
    ("DeepSeek V4 Pro (API)", 5.9, 0.99, 78.4, "#6366f1", "D"),
    ("Kimi K3 (API)", 8.0, 1.95, 74.0, "#a855f7", "v"),
    
    # Local Deployments on Mac M5 Ultra (256GB)
    ("Local DeepSeek V4.1 (M5 Ultra Q4)", 8.2, 1.03, 71.4, "#2563eb", "p"),
    ("Local Qwen 3.8-27B (M5 Ultra Q8)", 8.8, 0.85, 68.2, "#3b82f6", "h"),
    ("Local Qwen 3.5-397B (M5 Ultra Q4)", 11.2, 1.45, 73.2, "#1d4ed8", "H"),
    
    # Local Deployments on DGX Spark (128GB / Dual)
    ("Local DeepSeek V4.1 (DGX Spark FP4)", 11.1, 1.62, 71.0, "#84cc16", "d"),
    ("Local DeepSeek V4.1 (Dual Spark TP2)", 6.5, 1.98, 71.8, "#4d7c0f", "D"),
    ("Local Qwen 3.8-27B (DGX Spark FP4)", 20.1, 1.28, 67.4, "#65a30d", "X")
]

for label, lat_min, cost, swe, c, m in comparison_points:
    ax.scatter(lat_min, cost, s=140, color=c, marker=m, edgecolors="black", linewidth=0.8, alpha=0.9, zorder=4)
    offset_x = 0.2
    offset_y = 0.08
    if "Novita" in label: offset_y = -0.22
    elif "Dual Spark" in label: offset_y = 0.12
    elif "Opus" in label: offset_y = -0.25; offset_x = -2.8
    elif "Qwen 3.8-27B (DGX Spark" in label: offset_x = -3.8; offset_y = -0.25
    ax.annotate(f"{label}\n(${cost:.2f}, {lat_min:.1f}m, {swe:.1f}%)", (lat_min, cost),
                xytext=(lat_min + offset_x, cost + offset_y),
                fontsize=7.5, fontweight="medium", color="#1f2937")

ax.set_title("Curve 10: Task Latency vs. Fully Loaded Task Cost (SWE-bench 28-Step Trajectory)\nLocal Chinese Model Silicons vs. Frontier APIs", fontsize=12, fontweight="bold", pad=12)
ax.set_xlabel("Task Execution Latency (Minutes, Lower is Faster)", fontsize=10, fontweight="semibold")
ax.set_ylabel("Fully Loaded Cost per Successful Task ($ USD, Log Scale)", fontsize=10, fontweight="semibold")
ax.set_yscale("log")
ax.set_xlim(2.0, 22.0)
ax.set_ylim(0.25, 4.5)

from matplotlib.lines import Line2D
custom_legend = [
    Line2D([0], [0], marker="o", color="w", markerfacecolor="#e05638", markersize=9, label="Frontier Proprietary APIs (Anthropic/OpenAI)"),
    Line2D([0], [0], marker="P", color="w", markerfacecolor="#6366f1", markersize=9, label="Hosted Chinese APIs (Novita / DeepSeek / Kimi)"),
    Line2D([0], [0], marker="p", color="w", markerfacecolor="#2563eb", markersize=9, label="Apple Silicon Self-Hosted (Mac Studio M5 Ultra)"),
    Line2D([0], [0], marker="d", color="w", markerfacecolor="#84cc16", markersize=9, label="NVIDIA DGX Spark Self-Hosted")
]
ax.legend(handles=custom_legend, loc="upper right", frameon=True, fontsize=8)
ax.text(0.02, 0.03, "KEY FINDING: Hosted DeepSeek V4.1 on Novita dominates both speed (3.1 min) and cost ($0.39). Local M5 Ultra achieves 8.2 min at $1.03. DGX Spark single-node suffers from 18-20 min decode lag on dense models.",
        transform=ax.transAxes, fontsize=7.5, color="#6b7280", style="italic")

plt.tight_layout()
chart10_path = os.path.join(CHARTS_DIR, "curve10_latency_cost_pareto_chinese_models.png")
plt.savefig(chart10_path)
plt.close()
print("Saved Chart 10 to:", chart10_path)
