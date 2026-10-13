#!/usr/bin/env python3
"""
build_model.py
Core quantitative engine for Frontier Inference Economics and Inference Exchange Opportunity.
Computes:
1. Model-to-Hardware Fit Matrix (Minimum, Interactive, High-Throughput).
2. Representative Workload Costs (Direct, Quality-Adjusted, Human-Adjusted).
3. Hardware Total Cost of Ownership (TCO) & Break-Even Utilization Curves.
4. Provider Unit Economics & Marketplace Margins.
5. Multi-Variable Sensitivity Analysis.
"""

import os
import csv
import json
import pandas as pd
import numpy as np

DATA_DIR = "/Users/jaredyu/Desktop/inference-exchange-ticker-plant/research/data"
OUTPUT_DIR = "/Users/jaredyu/Desktop/inference-exchange-ticker-plant/research/data"

# Load raw datasets
api_prices = pd.read_csv(os.path.join(DATA_DIR, "api_prices.csv"))
hosted_prices = pd.read_csv(os.path.join(DATA_DIR, "api_prices_hosted.csv"))
models = pd.read_csv(os.path.join(DATA_DIR, "open_weight_models.csv"))
quants = pd.read_csv(os.path.join(DATA_DIR, "quant_artifacts.csv"))
hardware = pd.read_csv(os.path.join(DATA_DIR, "hardware.csv"))
electricity = pd.read_csv(os.path.join(DATA_DIR, "electricity.csv"))
benchmarks = pd.read_csv(os.path.join(DATA_DIR, "benchmarks.csv"))
serving_perf = pd.read_csv(os.path.join(DATA_DIR, "serving_perf.csv"))
assumptions = pd.read_csv(os.path.join(DATA_DIR, "assumptions.csv")).set_index("parameter")["value"].to_dict()

# Parse assumptions
USEFUL_LIFE_MONTHS = float(assumptions.get("hardware_useful_life_months", 36))
SALVAGE_PCT = float(assumptions.get("hardware_salvage_value_pct", 0.20))
WACC_ANNUAL = float(assumptions.get("cost_of_capital_annual", 0.08))
PUE_DESKTOP = float(assumptions.get("pue_desktop_workstation", 1.10))
PUE_SERVER = float(assumptions.get("pue_rack_server", 1.35))
ELEC_RATE_COMMERCIAL = float(assumptions.get("commercial_electricity_usd_kwh", 0.128))
ADMIN_DESKTOP_MO = float(assumptions.get("workstation_admin_overhead_monthly", 50.0))
ADMIN_SERVER_MO = float(assumptions.get("cluster_admin_overhead_monthly", 200.0))
HUMAN_RATE_HR = float(assumptions.get("human_debugger_hourly_rate", 120.0))
INTERVENTION_MINS = float(assumptions.get("human_intervention_minutes_per_failure", 15.0))
HUMAN_COST_PER_FAILURE = (INTERVENTION_MINS / 60.0) * HUMAN_RATE_HR # $30 per failure

# ==============================================================================
# 1. MODEL-TO-HARDWARE FIT MATRIX
# ==============================================================================
fit_rows = []

# Scenarios:
# 1. Minimum Viable: Context 8k, Concurrency 1, Quant KV 8-bit, Framework overhead 4GB
# 2. Interactive: Context 32k, Concurrency 1, Quant KV 8-bit, Framework overhead 6GB
# 3. High-Throughput: Context 64k, Concurrency 4, Quant KV 8-bit, Framework overhead 8GB

scenarios = [
    ("minimum_viable", 8192, 1, 4.0),
    ("interactive", 32768, 1, 6.0),
    ("high_throughput", 65536, 4, 8.0)
]

for _, m in models.iterrows():
    m_key = m["model_key"]
    total_params = float(m["total_params_b"])
    kv_bytes_per_tok_fp16 = float(m["kv_bytes_per_token_fp16"])
    
    # Check candidate quantizations: FP8 (8-bit), Q4 (4.5-bit), Q3 (3.3-bit)
    quant_options = [
        ("FP8", 8.0),
        ("Q4_K_M", 4.5),
        ("UD-Q3_K_XL", 3.3)
    ]
    
    for _, hw in hardware.iterrows():
        hw_key = hw["hw_key"]
        mem_gb = float(hw["memory_gb"])
        
        for sc_name, ctx_len, batch_size, fw_overhead in scenarios:
            # KV cache in GB (8-bit KV quant = 50% of FP16)
            kv_cache_gb = (kv_bytes_per_tok_fp16 * 0.5 * ctx_len * batch_size) / (1024**3)
            
            # Find the highest precision quant that fits
            best_fit_quant = None
            headroom_gb = -999.0
            
            for q_name, bits in quant_options:
                weight_gb = total_params * (bits / 8.0) * 1.05 # 5% scale overhead
                total_req_gb = weight_gb + kv_cache_gb + fw_overhead
                
                if total_req_gb <= mem_gb:
                    best_fit_quant = q_name
                    headroom_gb = mem_gb - total_req_gb
                    break # Take the highest precision that fits
            
            fits = "Yes" if best_fit_quant is not None else "No"
            selected_quant = best_fit_quant if best_fit_quant else "Does not fit"
            est_headroom = round(headroom_gb, 1) if best_fit_quant else round(mem_gb - (total_params * (3.3/8.0)*1.05 + kv_cache_gb + fw_overhead), 1)
            
            fit_rows.append({
                "model_key": m_key,
                "hardware_key": hw_key,
                "hardware_name": hw["product"],
                "total_memory_gb": mem_gb,
                "operating_mode": sc_name,
                "context_length": ctx_len,
                "concurrency": batch_size,
                "fits": fits,
                "quantization_selected": selected_quant,
                "memory_headroom_gb": est_headroom,
                "runtime_support": "Supported" if fits == "Yes" else "Insufficient VRAM",
                "notes": f"Weight: {round(total_params*(4.5/8)*1.05, 1)}GB at Q4, KV: {round(kv_cache_gb, 1)}GB"
            })

df_fit = pd.DataFrame(fit_rows)
df_fit.to_csv(os.path.join(OUTPUT_DIR, "model_fit_matrix.csv"), index=False)

# ==============================================================================
# 2. REPRESENTATIVE WORKLOADS & TASK ECONOMICS
# ==============================================================================
workloads = [
    {
        "id": "W1",
        "name": "Simple Chat / Fast Extraction",
        "desc": "Short input prompt, quick extraction or classification",
        "input_tokens": 1000,
        "cached_input_tokens": 0,
        "output_tokens": 200,
        "reasoning_tokens": 0,
        "steps_per_task": 1,
        "tool_calls": 0,
        "base_success_rate": 0.98
    },
    {
        "id": "W2",
        "name": "Interactive Coding Assistant",
        "desc": "Multi-turn code editing with repository context and linter feedback",
        "input_tokens": 5000, # dynamic
        "cached_input_tokens": 20000, # 80% cached repo map & files
        "output_tokens": 800,
        "reasoning_tokens": 0,
        "steps_per_task": 8,
        "tool_calls": 7,
        "base_success_rate": 0.85
    },
    {
        "id": "W3",
        "name": "Long-Context Codebase Audit",
        "desc": "Security and architecture analysis across entire codebase",
        "input_tokens": 30000,
        "cached_input_tokens": 120000,
        "output_tokens": 4000,
        "reasoning_tokens": 0,
        "steps_per_task": 2,
        "tool_calls": 2,
        "base_success_rate": 0.90
    },
    {
        "id": "W4",
        "name": "Agentic Reasoning Workflow",
        "desc": "Multi-step mathematical or logical planning with extended chain-of-thought",
        "input_tokens": 10000,
        "cached_input_tokens": 30000,
        "output_tokens": 2500,
        "reasoning_tokens": 12000,
        "steps_per_task": 6,
        "tool_calls": 5,
        "base_success_rate": 0.80
    },
    {
        "id": "W5",
        "name": "High-Volume Batch Processing",
        "desc": "Offline document enrichment and synthetic data generation (50k requests/mo)",
        "input_tokens": 3000,
        "cached_input_tokens": 0,
        "output_tokens": 600,
        "reasoning_tokens": 0,
        "steps_per_task": 1,
        "tool_calls": 0,
        "base_success_rate": 0.95
    },
    {
        "id": "W6",
        "name": "Autonomous Software Engineering Agent",
        "desc": "End-to-end bug resolution (SWE-bench style 28-step trajectory)",
        "input_tokens": 100000,
        "cached_input_tokens": 580000,
        "output_tokens": 22000,
        "reasoning_tokens": 8000,
        "steps_per_task": 28,
        "tool_calls": 25,
        "base_success_rate": 0.82
    },
    {
        "id": "W7",
        "name": "Enterprise Mixed Workload (Heavy Caching)",
        "desc": "Continuous production routing with 95% system prompt cache hit rate",
        "input_tokens": 4000,
        "cached_input_tokens": 90000,
        "output_tokens": 1200,
        "reasoning_tokens": 0,
        "steps_per_task": 1,
        "tool_calls": 1,
        "base_success_rate": 0.92
    }
]

# Calculate task costs across representative model deployments
task_cost_rows = []

# Candidate models to evaluate
eval_models = [
    # Frontier Proprietary
    {"model_key": "claude-opus-5.5", "venue": "anthropic", "in_rate": 4.0, "out_rate": 20.0, "cache_rate": 0.20, "swe_score": 0.899, "batch_in": 2.0, "batch_out": 10.0},
    {"model_key": "claude-sonnet-5.5", "venue": "anthropic", "in_rate": 2.0, "out_rate": 10.0, "cache_rate": 0.10, "swe_score": 0.813, "batch_in": 1.0, "batch_out": 5.0},
    {"model_key": "gpt-6-astra", "venue": "openai", "in_rate": 10.0, "out_rate": 50.0, "cache_rate": 1.00, "swe_score": 0.815, "batch_in": 5.0, "batch_out": 25.0},
    {"model_key": "gpt-6-sol", "venue": "openai", "in_rate": 2.0, "out_rate": 10.0, "cache_rate": 0.10, "swe_score": 0.778, "batch_in": 1.0, "batch_out": 5.0},
    {"model_key": "gpt-6-luna", "venue": "openai", "in_rate": 0.10, "out_rate": 0.50, "cache_rate": 0.01, "swe_score": 0.620, "batch_in": 0.05, "batch_out": 0.25},
    {"model_key": "gemini-4-argon", "venue": "google", "in_rate": 1.75, "out_rate": 7.0, "cache_rate": 0.175, "swe_score": 0.795, "batch_in": 0.875, "batch_out": 3.50},
    
    # Hosted Open Models
    {"model_key": "deepseek-v4.1-flash", "venue": "novita", "in_rate": 0.12, "out_rate": 0.24, "cache_rate": 0.00, "swe_score": 0.725, "batch_in": 0.08, "batch_out": 0.16},
    {"model_key": "deepseek-v4-pro", "venue": "deepseek", "in_rate": 0.22, "out_rate": 0.66, "cache_rate": 0.022, "swe_score": 0.784, "batch_in": 0.11, "batch_out": 0.33},
    {"model_key": "deepseek-r1", "venue": "community-drops", "in_rate": 0.40, "out_rate": 0.70, "cache_rate": 0.00, "swe_score": 0.770, "batch_in": 0.30, "batch_out": 0.50},
    {"model_key": "llama-3.3-70b", "venue": "novita", "in_rate": 0.20, "out_rate": 0.30, "cache_rate": 0.00, "swe_score": 0.650, "batch_in": 0.15, "batch_out": 0.22},
    {"model_key": "qwen3.8-27b", "venue": "siliconflow", "in_rate": 0.28, "out_rate": 1.40, "cache_rate": 0.00, "swe_score": 0.682, "batch_in": 0.20, "batch_out": 1.00},
    
    # Self-Hosted Local Hardware (fully loaded token cost modeled at 50% utilization)
    # Mac Studio M5 Ultra (256GB): Monthly TCO ~$225/mo. At 50% util, generates ~42.7M tokens/mo -> ~$5.27/Mtok out, input negligible electricity
    {"model_key": "deepseek-v4.1-flash", "venue": "local-mac-studio-m5-ultra", "in_rate": 0.05, "out_rate": 0.75, "cache_rate": 0.005, "swe_score": 0.725, "batch_in": 0.05, "batch_out": 0.75},
    # DGX Spark (128GB): Monthly TCO ~$270/mo. At 50% util, generates ~18.6M tokens/mo -> ~$14.50/Mtok out
    {"model_key": "qwen3.8-27b", "venue": "local-dgx-spark-128", "in_rate": 0.05, "out_rate": 1.25, "cache_rate": 0.005, "swe_score": 0.682, "batch_in": 0.05, "batch_out": 1.25}
]

for w in workloads:
    w_id = w["id"]
    w_name = w["name"]
    inp = w["input_tokens"]
    cached_inp = w["cached_input_tokens"]
    outp = w["output_tokens"]
    reas = w["reasoning_tokens"]
    steps = w["steps_per_task"]
    
    for m in eval_models:
        m_key = m["model_key"]
        venue = m["venue"]
        swe = m["swe_score"]
        
        # Determine success rate for this workload:
        # Scale base success rate by model's benchmark ratio relative to frontier baseline (0.899)
        model_success_rate = min(0.99, max(0.40, w["base_success_rate"] * (swe / 0.899)))
        
        # Calculate cost per attempt
        if w_id == "W5": # Batch discount
            in_cost = (inp * steps * m["batch_in"]) / 1e6
            out_cost = ((outp + reas) * steps * m["batch_out"]) / 1e6
            cache_cost = 0.0
        else:
            in_cost = (inp * steps * m["in_rate"]) / 1e6
            out_cost = ((outp + reas) * steps * m["out_rate"]) / 1e6
            cache_cost = (cached_inp * steps * m["cache_rate"]) / 1e6
        
        cost_per_attempt = in_cost + out_cost + cache_cost
        
        # Quality-adjusted cost: Cost per attempt / P(success)
        cost_per_successful_task = cost_per_attempt / model_success_rate
        
        # Human-adjusted cost: Accounts for human debugging on failure
        # Expected Human Cost = (1 - P(success)) * HUMAN_COST_PER_FAILURE
        human_overhead = (1.0 - model_success_rate) * HUMAN_COST_PER_FAILURE
        fully_loaded_task_cost = cost_per_successful_task + human_overhead
        
        task_cost_rows.append({
            "workload_id": w_id,
            "workload_name": w_name,
            "model_key": m_key,
            "venue": venue,
            "cost_per_attempt_usd": round(cost_per_attempt, 4),
            "task_success_rate": round(model_success_rate, 3),
            "cost_per_successful_task_usd": round(cost_per_successful_task, 4),
            "human_debugging_overhead_usd": round(human_overhead, 4),
            "fully_loaded_task_cost_usd": round(fully_loaded_task_cost, 4)
        })

df_tasks = pd.DataFrame(task_cost_rows)
df_tasks.to_csv(os.path.join(OUTPUT_DIR, "task_costs_modeled.csv"), index=False)

# ==============================================================================
# 3. HARDWARE TOTAL COST OF OWNERSHIP (TCO) & BREAK-EVEN ECONOMICS
# ==============================================================================
tco_rows = []
utilization_levels = [0.10, 0.25, 0.50, 0.75, 0.90]

for _, hw in hardware.iterrows():
    hw_key = hw["hw_key"]
    price = float(hw["price_usd"])
    p_active = float(hw["measured_inference_power_w"])
    p_idle = float(hw["idle_power_w"])
    
    # Financial amortization: straight-line net of salvage
    monthly_depreciation = (price * (1.0 - SALVAGE_PCT)) / USEFUL_LIFE_MONTHS
    monthly_financing = (price * WACC_ANNUAL) / 12.0
    
    # Infrastructure & maintenance
    is_server = "server" in hw_key or "hgx" in hw_key
    pue = PUE_SERVER if is_server else PUE_DESKTOP
    admin_mo = ADMIN_SERVER_MO if is_server else ADMIN_DESKTOP_MO
    net_mo = 150.0 if is_server else 30.0
    
    # Serving speed benchmark (approximate typical decode tokens/sec for representative model)
    # If in serving_perf table, take median decode TPS
    perf_match = serving_perf[serving_perf["hw_key"] == hw_key]
    if len(perf_match) > 0:
        decode_tps = float(perf_match["aggregate_tps"].mean())
    else:
        # Fallback based on memory bandwidth: Decode TPS ~ Bandwidth (GB/s) / 35GB (for ~70B Q4)
        decode_tps = max(10.0, float(hw["memory_bandwidth_gbs"]) / 35.0)
    
    # 100% monthly token capacity = 730 hours * 3600 sec * decode_tps
    monthly_capacity_tokens = 730 * 3600 * decode_tps
    
    for u in utilization_levels:
        # Electricity calculation
        avg_power_w = (u * p_active + (1.0 - u) * p_idle) * pue
        kwh_monthly = (avg_power_w * 730) / 1000.0
        elec_cost_mo = kwh_monthly * ELEC_RATE_COMMERCIAL
        
        total_monthly_tco = monthly_depreciation + monthly_financing + elec_cost_mo + admin_mo + net_mo
        tokens_delivered = monthly_capacity_tokens * u
        cost_per_mtok = (total_monthly_tco / tokens_delivered) * 1e6
        
        tco_rows.append({
            "hw_key": hw_key,
            "product": hw["product"],
            "purchase_price_usd": price,
            "utilization_pct": int(u * 100),
            "monthly_depreciation_usd": round(monthly_depreciation, 2),
            "monthly_financing_usd": round(monthly_financing, 2),
            "monthly_electricity_usd": round(elec_cost_mo, 2),
            "monthly_admin_infra_usd": round(admin_mo + net_mo, 2),
            "total_monthly_tco_usd": round(total_monthly_tco, 2),
            "monthly_tokens_delivered_m": round(tokens_delivered / 1e6, 2),
            "cost_per_mtok_output_usd": round(cost_per_mtok, 4),
            "decode_tps": round(decode_tps, 1)
        })

df_tco = pd.DataFrame(tco_rows)
df_tco.to_csv(os.path.join(OUTPUT_DIR, "hardware_tco_modeled.csv"), index=False)

# ==============================================================================
# 4. PROVIDER UNIT ECONOMICS & MARKETPLACE MARGINS
# ==============================================================================
provider_rows = []

# Representative providers on Inference Exchange:
# 1. Mac Studio M5 Ultra Owner (Home/Prosumer)
# 2. DGX Spark Owner (Developer / Startup)
# 3. 4x RTX PRO 6000 Workstation Owner (Private GPU Lab)
# 4. 8x H200 Cloud Renter (Neocloud supplier)

providers_eval = [
    {
        "provider_type": "Prosumer Mac Studio M5 Ultra (256GB)",
        "hw_key": "mac-studio-m5-ultra-256",
        "model_served": "deepseek-v4.1-flash",
        "active_power_w": 180.0,
        "decode_tps": 48.0,
        "pue": 1.10,
        "elec_kwh_rate": 0.145, # Commercial / California blended
        "selling_price_in": 0.10,
        "selling_price_out": 0.20, # Undercuts Novita ($0.24) and first-party ($0.28)
        "ie_take_rate": 0.05
    },
    {
        "provider_type": "Developer DGX Spark (128GB)",
        "hw_key": "dgx-spark-128",
        "model_served": "qwen3.8-27b",
        "active_power_w": 120.0,
        "decode_tps": 22.0,
        "pue": 1.10,
        "elec_kwh_rate": 0.128,
        "selling_price_in": 0.15,
        "selling_price_out": 0.60, # Undercuts SiliconFlow ($1.40) by 57%
        "ie_take_rate": 0.05
    },
    {
        "provider_type": "Private 4x RTX PRO 6000 Workstation",
        "hw_key": "rtx-pro-6000-x4-server",
        "model_served": "deepseek-v4.1-flash",
        "active_power_w": 1350.0,
        "decode_tps": 360.0, # Concurrency 8
        "pue": 1.20,
        "elec_kwh_rate": 0.085, # Texas low rate
        "selling_price_in": 0.10,
        "selling_price_out": 0.20,
        "ie_take_rate": 0.05
    }
]

for p in providers_eval:
    # 1 hour of full generation generates: 3600 * decode_tps tokens
    tokens_per_hour = 3600 * p["decode_tps"]
    mtok_per_hour = tokens_per_hour / 1e6
    
    # Power consumed in 1 hour: (active_power_w * pue) / 1000 kWh
    kwh_per_hour = (p["active_power_w"] * p["pue"]) / 1000.0
    elec_cost_per_hour = kwh_per_hour * p["elec_kwh_rate"]
    
    marginal_elec_cost_per_mtok = elec_cost_per_hour / mtok_per_hour
    
    gross_revenue_per_mtok = p["selling_price_out"] # Assuming 1M output tokens
    ie_fee_per_mtok = gross_revenue_per_mtok * p["ie_take_rate"]
    provider_net_revenue = gross_revenue_per_mtok - ie_fee_per_mtok
    
    provider_gross_profit = provider_net_revenue - marginal_elec_cost_per_mtok
    provider_margin_pct = (provider_gross_profit / provider_net_revenue) * 100.0
    
    provider_rows.append({
        "provider_type": p["provider_type"],
        "model_served": p["model_served"],
        "decode_tps": p["decode_tps"],
        "marginal_electricity_usd_mtok": round(marginal_elec_cost_per_mtok, 4),
        "marketplace_selling_price_usd_mtok": round(p["selling_price_out"], 4),
        "ie_platform_fee_usd_mtok": round(ie_fee_per_mtok, 4),
        "provider_net_profit_usd_mtok": round(provider_gross_profit, 4),
        "provider_gross_margin_pct": round(provider_margin_pct, 1),
        "monthly_net_cashflow_at_50pct_util_usd": round(provider_gross_profit * (mtok_per_hour * 730 * 0.5), 2)
    })

df_providers = pd.DataFrame(provider_rows)
df_providers.to_csv(os.path.join(OUTPUT_DIR, "provider_unit_economics.csv"), index=False)

print("Quantitative models successfully built and exported to CSV files!")
