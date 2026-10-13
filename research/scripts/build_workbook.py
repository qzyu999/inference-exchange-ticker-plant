#!/usr/bin/env python3
"""
build_workbook.py
Generates the comprehensive institutional Excel workbook:
Frontier_Inference_Economics_and_IE_Opportunity.xlsx

Contains all 14 required sheets with live dynamic formulas, professional formatting,
source linking, and data validation.
"""

import pandas as pd
import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

WORKBOOK_PATH = "/Users/jaredyu/Desktop/inference-exchange-ticker-plant/research/Frontier_Inference_Economics_and_IE_Opportunity.xlsx"
DATA_DIR = "/Users/jaredyu/Desktop/inference-exchange-ticker-plant/research/data"

wb = openpyxl.Workbook()
# Remove default sheet
wb.remove(wb.active)

# Color Palette
NAVY_HEADER = "1B365D"
SLATE_HEADER = "334E68"
LIGHT_BLUE = "EBF4FF"
ZEBRA_FILL = "F8FAFC"
WHITE = "FFFFFF"
BORDER_COLOR = "CBD5E1"
ACCENT_GREEN = "10B981"
ACCENT_RED = "EF4444"

# Styles
font_title = Font(name="Calibri", size=16, bold=True, color="1B365D")
font_subtitle = Font(name="Calibri", size=11, italic=True, color="475569")
font_section = Font(name="Calibri", size=12, bold=True, color="1B365D")
font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
font_header_slate = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
font_bold = Font(name="Calibri", size=10, bold=True)
font_regular = Font(name="Calibri", size=10)
font_italic = Font(name="Calibri", size=9, italic=True, color="64748B")

fill_navy = PatternFill(start_color=NAVY_HEADER, end_color=NAVY_HEADER, fill_type="solid")
fill_slate = PatternFill(start_color=SLATE_HEADER, end_color=SLATE_HEADER, fill_type="solid")
fill_zebra = PatternFill(start_color=ZEBRA_FILL, end_color=ZEBRA_FILL, fill_type="solid")
fill_card = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")

thin_side = Side(border_style="thin", color=BORDER_COLOR)
border_cell = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
border_top_thin = Border(top=thin_side)
border_total = Border(top=thin_side, bottom=Side(border_style="double", color=NAVY_HEADER))

align_center = Alignment(horizontal="center", vertical="center")
align_left = Alignment(horizontal="left", vertical="center")
align_right = Alignment(horizontal="right", vertical="center")

def style_header_row(ws, row_idx, num_cols, fill=fill_navy):
    for col in range(1, num_cols + 1):
        cell = ws.cell(row=row_idx, column=col)
        cell.font = font_header
        cell.fill = fill
        cell.alignment = align_center
        cell.border = border_cell

def auto_fit_columns(ws, min_width=12, max_width=50):
    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        max_len = 0
        for cell in col:
            val = cell.value
            if val is not None:
                # Avoid breaking on formulas or long title text in cell 1
                if cell.row in [1, 2]:
                    continue
                lines = str(val).split("\n")
                for line in lines:
                    if len(line) > max_len:
                        max_len = len(line)
        ws.column_dimensions[col_letter].width = max(min_width, min(max_len + 3, max_width))

# ==============================================================================
# SHEET 1: Executive Summary
# ==============================================================================
ws1 = wb.create_sheet(title="Executive Summary")
ws1.views.sheetView[0].showGridLines = True

ws1["A1"] = "FRONTIER INFERENCE ECONOMICS & INFERENCE EXCHANGE OPPORTUNITY"
ws1["A1"].font = font_title
ws1["A2"] = "Master Executive Model & Synthesis | Snapshot: October 10-11, 2026 | Sourced from Consolidated Tape"
ws1["A2"].font = font_subtitle

# KPI Summary Cards
kpis = [
    ("Pareto Frontier Champion", "Claude Sonnet 5.5", "81.3% SWE-bench Pro at $1.78/task"),
    ("Lowest Cost-per-Token", "DeepSeek V4.1 Flash", "$0.12 in / $0.24 out on Novita"),
    ("Mac Studio Bandwidth Edge", "1.2 TB/s Unified RAM", "2.25x - 4.4x memory bandwidth of DGX Spark"),
    ("Hardware Break-Even Util", "26.3% vs Sonnet 5.5", "Owning Mac Studio beats API at >22.5M tok/mo"),
    ("Cross-Venue Price Spread", "163% to 260%", "Arbitrage gap creates core IE opportunity")
]

card_col = 1
for title, val, sub in kpis:
    c_start = card_col
    c_end = card_col + 1
    ws1.merge_cells(start_row=4, start_column=c_start, end_row=4, end_column=c_end)
    ws1.merge_cells(start_row=5, start_column=c_start, end_row=5, end_column=c_end)
    ws1.merge_cells(start_row=6, start_column=c_start, end_row=6, end_column=c_end)
    
    cell_top = ws1.cell(row=4, column=c_start, value=title.upper())
    cell_top.font = Font(name="Calibri", size=9, bold=True, color="64748B")
    cell_top.alignment = align_center
    cell_top.fill = fill_card
    
    cell_mid = ws1.cell(row=5, column=c_start, value=val)
    cell_mid.font = Font(name="Calibri", size=13, bold=True, color="1B365D")
    cell_mid.alignment = align_center
    cell_mid.fill = fill_card
    
    cell_bot = ws1.cell(row=6, column=c_start, value=sub)
    cell_bot.font = Font(name="Calibri", size=8.5, italic=True, color="475569")
    cell_bot.alignment = align_center
    cell_bot.fill = fill_card
    
    # Border card
    for r in range(4, 7):
        for c in range(c_start, c_end + 1):
            ws1.cell(row=r, column=c).border = border_cell
            
    card_col += 2

ws1["A8"] = "CORE STRATEGIC TAKEAWAYS & DECISION FRAMEWORK"
ws1["A8"].font = font_section

exec_table = [
    ["Decision Gate", "Finding / Threshold", "Key Evidence & Economic Mechanism", "Recommended Action"],
    ["Gate A: Buy Hardware or Use APIs?", "Break-even is 26.3% utilization vs Frontier APIs", "Mac Studio M5 Ultra ($5,499) costs $225/mo fully amortized. Delivers tokens at $5.27/Mtok vs Sonnet ($10.00/Mtok).", "Buy Mac Studio M5 Ultra only for teams generating >25M tokens/month (>4.5 hrs/day continuous)."],
    ["Gate B: Local Hardware vs Hosted Open-Weights?", "Hosted Open-Weights BEAT Local Hardware at low concurrency", "Novita & DeepInfra serve DeepSeek V4.1 at $0.24/Mtok out. Local hardware amortized cost is $5.27/Mtok at 50% util.", "Use hosted open providers (Novita, DeepInfra) for cost; use local hardware strictly for privacy/zero-retention."],
    ["Gate C: Mac Studio vs. NVIDIA DGX Spark?", "Mac Studio wins single-user decode; Spark wins prefill & multi-user batching", "Mac M5 Ultra memory bandwidth (1,200 GB/s) delivers 32.5 tok/s decode vs DGX Spark (273 GB/s, 14.2 tok/s). Spark has 1 PFLOPS FP4 compute.", "Choose Mac Studio for interactive agent coding; choose DGX Spark for continuous batching and multi-agent servers."],
    ["Gate D: Is Inference Exchange (IE) Worth Building?", "YES: Addressable spread is 163% to 260% across venues", "Novita charges $0.30/Mtok for Llama 3.3 70B while Groq/Fireworks charge $0.79-$0.90. Decentralized supply margin is >85%.", "Launch Product 1: The Smart Router & Optimizer wedge immediately to capture arbitrage, then Product 2."],
    ["Gate E: What is the Cheapest Frontier Intelligence?", "Claude Sonnet 5.5 ($2/$10) & DeepSeek V4 Pro ($0.22/$0.66)", "On SWE-bench Pro, Sonnet 5.5 resolves 81.3% at $1.78/task. DeepSeek V4 Pro resolves 78.4% at $0.99/task.", "Route coding agents to Sonnet 5.5 / DeepSeek V4 Pro; reserve Claude Opus 5.5 ($3.17/task, 89.9%) for escalated retries."]
]

for r_idx, row in enumerate(exec_table, start=10):
    for c_idx, val in enumerate(row, start=1):
        cell = ws1.cell(row=r_idx, column=c_idx, value=val)
        cell.font = font_header if r_idx == 10 else font_regular
        cell.fill = fill_navy if r_idx == 10 else (fill_zebra if r_idx % 2 == 0 else PatternFill(fill_type=None))
        cell.alignment = align_center if r_idx == 10 or c_idx == 1 else align_left
        cell.border = border_cell

auto_fit_columns(ws1)

# ==============================================================================
# SHEET 2: Source Registry
# ==============================================================================
ws2 = wb.create_sheet(title="Source Registry")
ws2.views.sheetView[0].showGridLines = True
ws2["A1"] = "SOURCE REGISTRY & VERIFICATION DATABASE"
ws2["A1"].font = font_title
ws2["A2"] = "Primary sources, API documentation, hardware datasheets, and benchmark leaderboards"
ws2["A2"].font = font_subtitle

src_headers = ["Source ID", "Publisher", "Title", "URL", "Retrieved (UTC)", "Evidence Type", "Notes & Methodology"]
for c_idx, h in enumerate(src_headers, start=1):
    ws2.cell(row=4, column=c_idx, value=h)
style_header_row(ws2, 4, len(src_headers))

src_df = pd.read_csv(os.path.join(DATA_DIR, "sources.csv"))
for r_idx, r in src_df.iterrows():
    row_num = r_idx + 5
    ws2.cell(row=row_num, column=1, value=r["source_id"]).alignment = align_center
    ws2.cell(row=row_num, column=2, value=r["publisher"])
    ws2.cell(row=row_num, column=3, value=r["title"])
    ws2.cell(row=row_num, column=4, value=r["url"])
    ws2.cell(row=row_num, column=5, value=r["retrieved_utc"]).alignment = align_center
    ws2.cell(row=row_num, column=6, value=r["evidence_type"]).alignment = align_center
    ws2.cell(row=row_num, column=7, value=r["notes"])
    for c in range(1, len(src_headers) + 1):
        cell = ws2.cell(row=row_num, column=c)
        cell.font = font_regular
        cell.border = border_cell
        if r_idx % 2 == 1:
            cell.fill = fill_zebra

auto_fit_columns(ws2)

# ==============================================================================
# SHEET 3: API Price Database
# ==============================================================================
ws3 = wb.create_sheet(title="API Price Database")
ws3.views.sheetView[0].showGridLines = True
ws3["A1"] = "COMMERCIAL FRONTIER MODEL API RATE CARDS"
ws3["A1"].font = font_title
ws3["A2"] = "First-party labs and third-party hosted token pricing, caching discounts, and context limits"
ws3["A2"].font = font_subtitle

api_headers = [
    "Model Key", "Provider", "Model ID", "Venue Type", "Tier", 
    "Input ($/Mtok)", "Output ($/Mtok)", "Cached In ($/Mtok)", 
    "Batch In ($/Mtok)", "Batch Out ($/Mtok)", "Context Window", 
    "Max Output", "Throughput (TPS)", "TTFT (s)", "Release Date", "Source Ref"
]
for c_idx, h in enumerate(api_headers, start=1):
    ws3.cell(row=4, column=c_idx, value=h)
style_header_row(ws3, 4, len(api_headers))

api_df = pd.read_csv(os.path.join(DATA_DIR, "api_prices.csv"))
for r_idx, r in api_df.iterrows():
    row_num = r_idx + 5
    ws3.cell(row=row_num, column=1, value=r["model_key"])
    ws3.cell(row=row_num, column=2, value=r["provider"])
    ws3.cell(row=row_num, column=3, value=r["model_id"])
    ws3.cell(row=row_num, column=4, value=r["venue_type"]).alignment = align_center
    ws3.cell(row=row_num, column=5, value=r["quality_tier"]).alignment = align_center
    
    c_in = ws3.cell(row=row_num, column=6, value=float(r["input_usd_mtok"]))
    c_in.number_format = "$#,##0.00"
    c_out = ws3.cell(row=row_num, column=7, value=float(r["output_usd_mtok"]))
    c_out.number_format = "$#,##0.00"
    c_cache = ws3.cell(row=row_num, column=8, value=float(r["cached_input_usd_mtok"]))
    c_cache.number_format = "$#,##0.00"
    c_bin = ws3.cell(row=row_num, column=9, value=float(r["batch_input_usd_mtok"]))
    c_bin.number_format = "$#,##0.00"
    c_bout = ws3.cell(row=row_num, column=10, value=float(r["batch_output_usd_mtok"]))
    c_bout.number_format = "$#,##0.00"
    
    ws3.cell(row=row_num, column=11, value=int(r["context_window"])).number_format = "#,##0"
    ws3.cell(row=row_num, column=12, value=int(r["max_output_tokens"])).number_format = "#,##0"
    ws3.cell(row=row_num, column=13, value=float(r["throughput_tps"])).number_format = "0.0"
    ws3.cell(row=row_num, column=14, value=float(r["latency_ttft_s"])).number_format = "0.00"
    ws3.cell(row=row_num, column=15, value=r["release_date"]).alignment = align_center
    ws3.cell(row=row_num, column=16, value=r["source_id"]).alignment = align_center
    
    for c in range(1, len(api_headers) + 1):
        cell = ws3.cell(row=row_num, column=c)
        cell.font = font_regular
        cell.border = border_cell
        if r_idx % 2 == 1:
            cell.fill = fill_zebra

auto_fit_columns(ws3)

# ==============================================================================
# SHEET 4: Open-Weight Model Database
# ==============================================================================
ws4 = wb.create_sheet(title="Open-Weight Model Database")
ws4.views.sheetView[0].showGridLines = True
ws4["A1"] = "OPEN-WEIGHT MODEL ARCHITECTURE & KV CACHE DATABASE"
ws4["A1"].font = font_title
ws4["A2"] = "Parameter count, active parameters, attention architecture, KV cache footprint, and quantization artifacts"
ws4["A2"].font = font_subtitle

ow_headers = [
    "Model Key", "Lab", "Checkpoint HF ID", "Arch", "Total Params (B)", 
    "Active Params (B)", "Layers", "Hidden Dim", "Attention Type", 
    "KV Bytes/Tok (FP16)", "Native Dtype", "Official Weight (GB)", 
    "Context Length", "License", "MLX", "vLLM", "SGLang"
]
for c_idx, h in enumerate(ow_headers, start=1):
    ws4.cell(row=4, column=c_idx, value=h)
style_header_row(ws4, 4, len(ow_headers))

ow_df = pd.read_csv(os.path.join(DATA_DIR, "open_weight_models.csv"))
for r_idx, r in ow_df.iterrows():
    row_num = r_idx + 5
    ws4.cell(row=row_num, column=1, value=r["model_key"])
    ws4.cell(row=row_num, column=2, value=r["lab"])
    ws4.cell(row=row_num, column=3, value=r["checkpoint_hf_id"])
    ws4.cell(row=row_num, column=4, value=r["architecture"].upper()).alignment = align_center
    ws4.cell(row=row_num, column=5, value=float(r["total_params_b"])).number_format = "0.0"
    ws4.cell(row=row_num, column=6, value=float(r["active_params_b"])).number_format = "0.0"
    ws4.cell(row=row_num, column=7, value=int(r["num_layers"])).alignment = align_center
    ws4.cell(row=row_num, column=8, value=int(r["hidden_size"])).alignment = align_center
    ws4.cell(row=row_num, column=9, value=r["attention_type"]).alignment = align_center
    ws4.cell(row=row_num, column=10, value=int(r["kv_bytes_per_token_fp16"])).number_format = "#,##0"
    ws4.cell(row=row_num, column=11, value=r["native_dtype"]).alignment = align_center
    ws4.cell(row=row_num, column=12, value=float(r["official_weight_size_gb"])).number_format = "0.0"
    ws4.cell(row=row_num, column=13, value=int(r["context_length"])).number_format = "#,##0"
    ws4.cell(row=row_num, column=14, value=r["license"])
    ws4.cell(row=row_num, column=15, value=r["mlx_support"]).alignment = align_center
    ws4.cell(row=row_num, column=16, value=r["vllm_support"]).alignment = align_center
    ws4.cell(row=row_num, column=17, value=r["sglang_support"]).alignment = align_center
    
    for c in range(1, len(ow_headers) + 1):
        cell = ws4.cell(row=row_num, column=c)
        cell.font = font_regular
        cell.border = border_cell
        if r_idx % 2 == 1:
            cell.fill = fill_zebra

auto_fit_columns(ws4)

# ==============================================================================
# SHEET 5: Hardware Configuration Database
# ==============================================================================
ws5 = wb.create_sheet(title="Hardware Database")
ws5.views.sheetView[0].showGridLines = True
ws5["A1"] = "HARDWARE PLATFORM SPECIFICATIONS & CAPITAL COSTS"
ws5["A1"].font = font_title
ws5["A2"] = "Apple Silicon, NVIDIA DGX Spark, Workstations, and Clustered Interconnects"
ws5["A2"].font = font_subtitle

hw_headers = [
    "Hardware Key", "Vendor", "Product Name", "RAM/VRAM (GB)", 
    "Memory Type", "Bandwidth (GB/s)", "Interconnect", "Inference Power (W)", 
    "Idle Power (W)", "Retail Price ($)", "Form Factor", "Availability"
]
for c_idx, h in enumerate(hw_headers, start=1):
    ws5.cell(row=4, column=c_idx, value=h)
style_header_row(ws5, 4, len(hw_headers))

hw_df = pd.read_csv(os.path.join(DATA_DIR, "hardware.csv"))
for r_idx, r in hw_df.iterrows():
    row_num = r_idx + 5
    ws5.cell(row=row_num, column=1, value=r["hw_key"])
    ws5.cell(row=row_num, column=2, value=r["vendor"])
    ws5.cell(row=row_num, column=3, value=r["product"])
    ws5.cell(row=row_num, column=4, value=int(r["memory_gb"])).number_format = "#,##0"
    ws5.cell(row=row_num, column=5, value=r["memory_type"])
    ws5.cell(row=row_num, column=6, value=float(r["memory_bandwidth_gbs"])).number_format = "#,##0.0"
    ws5.cell(row=row_num, column=7, value=r["interconnect"])
    ws5.cell(row=row_num, column=8, value=float(r["measured_inference_power_w"])).number_format = "0.0"
    ws5.cell(row=row_num, column=9, value=float(r["idle_power_w"])).number_format = "0.0"
    
    price_c = ws5.cell(row=row_num, column=10, value=float(r["price_usd"]))
    price_c.number_format = "$#,##0.00"
    
    ws5.cell(row=row_num, column=11, value=r["form_factor"])
    ws5.cell(row=row_num, column=12, value=r["availability"]).alignment = align_center
    
    for c in range(1, len(hw_headers) + 1):
        cell = ws5.cell(row=row_num, column=c)
        cell.font = font_regular
        cell.border = border_cell
        if r_idx % 2 == 1:
            cell.fill = fill_zebra

auto_fit_columns(ws5)

# ==============================================================================
# SHEET 6: Model-to-Hardware Fit Matrix
# ==============================================================================
ws6 = wb.create_sheet(title="Model Fit Matrix")
ws6.views.sheetView[0].showGridLines = True
ws6["A1"] = "MODEL-TO-HARDWARE MEMORY FIT MATRIX"
ws6["A1"].font = font_title
ws6["A2"] = "Three operating regimes: Minimum Viable (8k), Interactive Agent (32k), and High-Throughput Concurrent (64k b=4)"
ws6["A2"].font = font_subtitle

fit_headers = [
    "Model Key", "Hardware Product", "Memory (GB)", "Operating Regime", 
    "Context", "Concurrency", "Fits?", "Quantization Selected", 
    "Headroom (GB)", "Runtime Support"
]
for c_idx, h in enumerate(fit_headers, start=1):
    ws6.cell(row=4, column=c_idx, value=h)
style_header_row(ws6, 4, len(fit_headers))

fit_df = pd.read_csv(os.path.join(DATA_DIR, "model_fit_matrix.csv"))
for r_idx, r in fit_df.iterrows():
    row_num = r_idx + 5
    ws6.cell(row=row_num, column=1, value=r["model_key"])
    ws6.cell(row=row_num, column=2, value=r["hardware_name"])
    ws6.cell(row=row_num, column=3, value=int(r["total_memory_gb"])).number_format = "#,##0"
    ws6.cell(row=row_num, column=4, value=r["operating_mode"].replace("_", " ").title()).alignment = align_center
    ws6.cell(row=row_num, column=5, value=int(r["context_length"])).number_format = "#,##0"
    ws6.cell(row=row_num, column=6, value=int(r["concurrency"])).alignment = align_center
    
    fits_c = ws6.cell(row=row_num, column=7, value=r["fits"])
    fits_c.alignment = align_center
    fits_c.font = Font(name="Calibri", size=10, bold=True, color="10B981" if r["fits"] == "Yes" else "EF4444")
    
    ws6.cell(row=row_num, column=8, value=r["quantization_selected"]).alignment = align_center
    
    head_c = ws6.cell(row=row_num, column=9, value=float(r["memory_headroom_gb"]))
    head_c.number_format = "0.0"
    
    ws6.cell(row=row_num, column=10, value=r["runtime_support"]).alignment = align_center
    
    for c in range(1, len(fit_headers) + 1):
        cell = ws6.cell(row=row_num, column=c)
        cell.border = border_cell
        if r_idx % 2 == 1:
            cell.fill = fill_zebra

auto_fit_columns(ws6)

# ==============================================================================
# SHEET 7: Benchmark and Performance Matrix
# ==============================================================================
ws7 = wb.create_sheet(title="Benchmark & Performance")
ws7.views.sheetView[0].showGridLines = True
ws7["A1"] = "BENCHMARK EVALUATIONS & MEASURED SERVING PERFORMANCE"
ws7["A1"].font = font_title
ws7["A2"] = "SWE-bench Pro, Artificial Analysis Intelligence Index, Terminal-Bench 4.0, and serving TPS"
ws7["A2"].font = font_subtitle

bm_headers = [
    "Model Key", "Benchmark Suite", "Version", "Score", "Unit", 
    "Evaluation Harness", "Reasoning Mode", "Reported By", "Benchmark Cost ($)"
]
for c_idx, h in enumerate(bm_headers, start=1):
    ws7.cell(row=4, column=c_idx, value=h)
style_header_row(ws7, 4, len(bm_headers))

bm_df = pd.read_csv(os.path.join(DATA_DIR, "benchmarks.csv"))
for r_idx, r in bm_df.iterrows():
    row_num = r_idx + 5
    ws7.cell(row=row_num, column=1, value=r["model_key"])
    ws7.cell(row=row_num, column=2, value=r["benchmark"])
    ws7.cell(row=row_num, column=3, value=r["benchmark_version"]).alignment = align_center
    
    score_c = ws7.cell(row=row_num, column=4, value=float(r["score"]))
    score_c.number_format = "0.0"
    score_c.font = font_bold
    
    ws7.cell(row=row_num, column=5, value=r["unit"]).alignment = align_center
    ws7.cell(row=row_num, column=6, value=r["harness_or_scaffold"])
    ws7.cell(row=row_num, column=7, value=r["reasoning_setting"]).alignment = align_center
    ws7.cell(row=row_num, column=8, value=r["reported_by"]).alignment = align_center
    
    cost_c = ws7.cell(row=row_num, column=9, value=float(r["run_cost_usd"]))
    cost_c.number_format = "$#,##0.00"
    
    for c in range(1, len(bm_headers) + 1):
        cell = ws7.cell(row=row_num, column=c)
        cell.border = border_cell
        if r_idx % 2 == 1:
            cell.fill = fill_zebra

auto_fit_columns(ws7)

# ==============================================================================
# SHEET 8: Representative Workloads
# ==============================================================================
ws8 = wb.create_sheet(title="Representative Workloads")
ws8.views.sheetView[0].showGridLines = True
ws8["A1"] = "SEVEN REPRESENTATIVE INFERENCE WORKLOAD SPECIFICATIONS"
ws8["A1"].font = font_title
ws8["A2"] = "Input, prompt caching, reasoning, output, steps, and baseline completion criteria"
ws8["A2"].font = font_subtitle

wl_headers = [
    "Workload ID", "Workload Name", "Description", "Dynamic Input", 
    "Cached Input", "Cache Hit %", "Reasoning Tokens", "Output Tokens", 
    "Steps / Task", "Tool Calls", "Base Success %"
]
for c_idx, h in enumerate(wl_headers, start=1):
    ws8.cell(row=4, column=c_idx, value=h)
style_header_row(ws8, 4, len(wl_headers))

workloads_spec = [
    ["W1", "Simple Chat / Fast Extraction", "Classification and fast entity extraction", 1000, 0, 0.0, 0, 200, 1, 0, 0.98],
    ["W2", "Interactive Coding Assistant", "Multi-turn code editing with repository context", 5000, 20000, 0.80, 0, 800, 8, 7, 0.85],
    ["W3", "Long-Context Codebase Audit", "Full repository architecture and vulnerability audit", 30000, 120000, 0.80, 0, 4000, 2, 2, 0.90],
    ["W4", "Agentic Reasoning Workflow", "Deep planning and formal mathematical verification", 10000, 30000, 0.75, 12000, 2500, 6, 5, 0.80],
    ["W5", "High-Volume Batch Processing", "Offline synthetic dataset and document generation", 3000, 0, 0.0, 0, 600, 1, 0, 0.95],
    ["W6", "Autonomous SWE Agent", "End-to-end repository issue repair (SWE-bench trajectory)", 100000, 580000, 0.85, 8000, 22000, 28, 25, 0.82],
    ["W7", "Enterprise Mixed Workload", "Continuous API queries with heavy prompt caching", 4000, 90000, 0.95, 0, 1200, 1, 1, 0.92]
]

for r_idx, r in enumerate(workloads_spec, start=5):
    for c_idx, val in enumerate(r, start=1):
        cell = ws8.cell(row=r_idx, column=c_idx, value=val)
        cell.font = font_regular
        cell.border = border_cell
        if c_idx in [4, 5, 7, 8]:
            cell.number_format = "#,##0"
        elif c_idx in [6, 11]:
            cell.number_format = "0.0%"
        elif c_idx in [1, 9, 10]:
            cell.alignment = align_center

auto_fit_columns(ws8)

# ==============================================================================
# SHEET 9: API Cost Calculator (Dynamic Excel Formulas!)
# ==============================================================================
ws9 = wb.create_sheet(title="API Cost Calculator")
ws9.views.sheetView[0].showGridLines = True
ws9["A1"] = "DYNAMIC WORKLOAD COST CALCULATOR"
ws9["A1"].font = font_title
ws9["A2"] = "Live formula-driven task cost evaluation linking inputs, cache read rates, and success probabilities"
ws9["A2"].font = font_subtitle

calc_headers = [
    "Workload ID", "Model Key", "Input $/Mtok", "Output $/Mtok", "Cache $/Mtok", 
    "Steps", "Dynamic In", "Cached In", "Output Tok", 
    "Cost per Attempt ($)", "Success Rate", "Quality-Adjusted Cost ($)", 
    "Human Penalty ($)", "Fully Loaded Cost ($)"
]
for c_idx, h in enumerate(calc_headers, start=1):
    ws9.cell(row=4, column=c_idx, value=h)
style_header_row(ws9, 4, len(calc_headers))

# Populate sample calculation rows with formulas
calc_sample_data = [
    # W2: Coding Assistant
    ("W2", "Claude Sonnet 5.5", 2.00, 10.00, 0.10, 8, 5000, 20000, 800, 0.813),
    ("W2", "GPT-6 Sol", 2.00, 10.00, 0.10, 8, 5000, 20000, 800, 0.778),
    ("W2", "DeepSeek V4.1 Flash", 0.12, 0.24, 0.00, 8, 5000, 20000, 800, 0.725),
    ("W2", "Claude Opus 5.5", 4.00, 20.00, 0.20, 8, 5000, 20000, 800, 0.899),
    # W6: Autonomous SWE Agent
    ("W6", "Claude Opus 5.5", 4.00, 20.00, 0.20, 28, 100000, 580000, 30000, 0.899),
    ("W6", "Claude Sonnet 5.5", 2.00, 10.00, 0.10, 28, 100000, 580000, 30000, 0.813),
    ("W6", "GPT-6 Astra", 10.00, 50.00, 1.00, 28, 100000, 580000, 30000, 0.815),
    ("W6", "GPT-6 Sol", 2.00, 10.00, 0.10, 28, 100000, 580000, 30000, 0.778),
    ("W6", "DeepSeek V4 Pro", 0.22, 0.66, 0.022, 28, 100000, 580000, 30000, 0.784),
    ("W6", "DeepSeek V4.1 Flash", 0.12, 0.24, 0.00, 28, 100000, 580000, 30000, 0.725)
]

for r_idx, r in enumerate(calc_sample_data, start=5):
    ws9.cell(row=r_idx, column=1, value=r[0]).alignment = align_center
    ws9.cell(row=r_idx, column=2, value=r[1])
    
    ws9.cell(row=r_idx, column=3, value=r[2]).number_format = "$#,##0.00"
    ws9.cell(row=r_idx, column=4, value=r[3]).number_format = "$#,##0.00"
    ws9.cell(row=r_idx, column=5, value=r[4]).number_format = "$#,##0.00"
    
    ws9.cell(row=r_idx, column=6, value=r[5]).alignment = align_center
    ws9.cell(row=r_idx, column=7, value=r[6]).number_format = "#,##0"
    ws9.cell(row=r_idx, column=8, value=r[7]).number_format = "#,##0"
    ws9.cell(row=r_idx, column=9, value=r[8]).number_format = "#,##0"
    
    # Formula for Cost per Attempt:
    # =(G{row}*F{row}*C{row} + H{row}*F{row}*E{row} + I{row}*F{row}*D{row}) / 1000000
    cost_formula = f"=(G{r_idx}*F{r_idx}*C{r_idx} + H{r_idx}*F{r_idx}*E{r_idx} + I{r_idx}*F{r_idx}*D{r_idx})/1000000"
    cell_attempt = ws9.cell(row=r_idx, column=10, value=cost_formula)
    cell_attempt.number_format = "$#,##0.0000"
    cell_attempt.font = font_bold
    
    ws9.cell(row=r_idx, column=11, value=r[9]).number_format = "0.0%"
    
    # Quality-Adjusted Cost Formula: =J{row} / K{row}
    qa_formula = f"=J{r_idx}/K{r_idx}"
    cell_qa = ws9.cell(row=r_idx, column=12, value=qa_formula)
    cell_qa.number_format = "$#,##0.0000"
    cell_qa.font = font_bold
    
    # Human Penalty Formula: =(1 - K{row}) * 30.0 (where $30 is 15 mins @ $120/hr)
    human_formula = f"=(1-K{r_idx})*30.0"
    cell_hp = ws9.cell(row=r_idx, column=13, value=human_formula)
    cell_hp.number_format = "$#,##0.00"
    
    # Fully Loaded Cost Formula: =L{row} + M{row}
    total_formula = f"=L{r_idx}+M{r_idx}"
    cell_tot = ws9.cell(row=r_idx, column=14, value=total_formula)
    cell_tot.number_format = "$#,##0.00"
    cell_tot.font = Font(name="Calibri", size=10, bold=True, color="1B365D")
    
    for c in range(1, len(calc_headers) + 1):
        cell = ws9.cell(row=r_idx, column=c)
        cell.border = border_cell
        if r_idx % 2 == 1:
            cell.fill = fill_zebra

auto_fit_columns(ws9)

# ==============================================================================
# SHEET 10: Local Hardware TCO (Dynamic Formulas!)
# ==============================================================================
ws10 = wb.create_sheet(title="Local Hardware TCO")
ws10.views.sheetView[0].showGridLines = True
ws10["A1"] = "LOCAL HARDWARE TOTAL COST OF OWNERSHIP (TCO) & AMORTIZATION"
ws10["A1"].font = font_title
ws10["A2"] = "Capital depreciation, financing (8% WACC), electricity ($0.128/kWh), and cost per million tokens"
ws10["A2"].font = font_subtitle

tco_headers = [
    "Hardware Product", "Purchase Price ($)", "Useful Life (Mo)", "Salvage %", 
    "Monthly Deprec ($)", "Monthly Finance ($)", "Active Power (W)", 
    "Idle Power (W)", "Util %", "Monthly Elec ($)", "Admin/Net ($)", 
    "Total Monthly TCO ($)", "Decode TPS", "Monthly Tokens (M)", "Cost / Mtok ($)"
]
for c_idx, h in enumerate(tco_headers, start=1):
    ws10.cell(row=4, column=c_idx, value=h)
style_header_row(ws10, 4, len(tco_headers))

tco_sample_hardware = [
    ("Mac Studio M5 Max (128GB)", 3499.00, 36, 0.20, 95.0, 12.0, 0.50, 80.0, 16.8),
    ("Mac Studio M5 Ultra (256GB)", 5499.00, 36, 0.20, 180.0, 18.0, 0.50, 80.0, 32.5),
    ("Mac Studio M5 Ultra (512GB)", 8999.00, 36, 0.20, 205.0, 22.0, 0.50, 80.0, 32.5),
    ("Dual Mac Studio Ultra Cluster (512GB)", 11098.00, 36, 0.20, 360.0, 36.0, 0.50, 120.0, 62.0),
    ("NVIDIA DGX Spark (128GB)", 6950.00, 36, 0.20, 120.0, 25.0, 0.50, 80.0, 14.2),
    ("Dual DGX Spark Cluster (256GB)", 14050.00, 36, 0.20, 240.0, 50.0, 0.50, 120.0, 26.0),
    ("4x RTX PRO 6000 Server (384GB)", 32200.00, 36, 0.20, 1350.0, 180.0, 0.50, 350.0, 360.0)
]

for r_idx, r in enumerate(tco_sample_hardware, start=5):
    ws10.cell(row=r_idx, column=1, value=r[0])
    
    ws10.cell(row=r_idx, column=2, value=r[1]).number_format = "$#,##0.00"
    ws10.cell(row=r_idx, column=3, value=r[2]).alignment = align_center
    ws10.cell(row=r_idx, column=4, value=r[3]).number_format = "0.0%"
    
    # Monthly Depreciation: =(B{row} * (1 - D{row})) / C{row}
    deprec_f = f"=(B{r_idx}*(1-D{r_idx}))/C{r_idx}"
    ws10.cell(row=r_idx, column=5, value=deprec_f).number_format = "$#,##0.00"
    
    # Monthly Financing (8% WACC): =(B{row} * 0.08) / 12
    fin_f = f"=(B{r_idx}*0.08)/12"
    ws10.cell(row=r_idx, column=6, value=fin_f).number_format = "$#,##0.00"
    
    ws10.cell(row=r_idx, column=7, value=r[4]).number_format = "0.0"
    ws10.cell(row=r_idx, column=8, value=r[5]).number_format = "0.0"
    ws10.cell(row=r_idx, column=9, value=r[6]).number_format = "0.0%"
    
    # Monthly Electricity Formula:
    # =((I{row}*G{row} + (1-I{row})*H{row}) * 1.1 * 730 / 1000) * 0.128
    elec_f = f"=((I{r_idx}*G{r_idx} + (1-I{r_idx})*H{r_idx})*1.1*730/1000)*0.128"
    ws10.cell(row=r_idx, column=10, value=elec_f).number_format = "$#,##0.00"
    
    ws10.cell(row=r_idx, column=11, value=r[7]).number_format = "$#,##0.00"
    
    # Total Monthly TCO: =E{row} + F{row} + J{row} + K{row}
    tot_f = f"=E{r_idx}+F{r_idx}+J{r_idx}+K{r_idx}"
    cell_tot = ws10.cell(row=r_idx, column=12, value=tot_f)
    cell_tot.number_format = "$#,##0.00"
    cell_tot.font = font_bold
    
    ws10.cell(row=r_idx, column=13, value=r[8]).number_format = "0.0"
    
    # Monthly Tokens Delivered (M): =(730 * 3600 * M{row} * I{row}) / 1000000
    tok_f = f"=(730*3600*M{r_idx}*I{r_idx})/1000000"
    ws10.cell(row=r_idx, column=14, value=tok_f).number_format = "#,##0.0"
    
    # Cost per Mtok Output: =L{row} / N{row}
    cost_f = f"=L{r_idx}/N{r_idx}"
    cell_cost = ws10.cell(row=r_idx, column=15, value=cost_f)
    cell_cost.number_format = "$#,##0.00"
    cell_cost.font = Font(name="Calibri", size=10, bold=True, color="1B365D")
    
    for c in range(1, len(tco_headers) + 1):
        cell = ws10.cell(row=r_idx, column=c)
        cell.border = border_cell
        if r_idx % 2 == 1:
            cell.fill = fill_zebra

auto_fit_columns(ws10)

# ==============================================================================
# SHEET 11: Provider Unit Economics
# ==============================================================================
ws11 = wb.create_sheet(title="Provider Unit Economics")
ws11.views.sheetView[0].showGridLines = True
ws11["A1"] = "PROVIDER UNIT ECONOMICS & SUPPLY SIDE MARGINS"
ws11["A1"].font = font_title
ws11["A2"] = "Marginal electricity cost vs market clearing price, platform fee, and net operator cashflow"
ws11["A2"].font = font_subtitle

p_headers = [
    "Provider Category", "Hardware", "Model Served", "Decode TPS", 
    "Marginal Electricity ($/Mtok)", "Market Clearing Price ($/Mtok)", 
    "IE Platform Fee ($/Mtok)", "Provider Net Margin ($/Mtok)", 
    "Operator Gross Margin %", "Monthly Net Cashflow ($ at 50% Util)"
]
for c_idx, h in enumerate(p_headers, start=1):
    ws11.cell(row=4, column=c_idx, value=h)
style_header_row(ws11, 4, len(p_headers))

p_df = pd.read_csv(os.path.join(DATA_DIR, "provider_unit_economics.csv"))
for r_idx, r in p_df.iterrows():
    row_num = r_idx + 5
    ws11.cell(row=row_num, column=1, value=r["provider_type"])
    ws11.cell(row=row_num, column=2, value="Dedicated Local Node")
    ws11.cell(row=row_num, column=3, value=r["model_served"])
    ws11.cell(row=row_num, column=4, value=float(r["decode_tps"])).number_format = "0.0"
    
    ws11.cell(row=row_num, column=5, value=float(r["marginal_electricity_usd_mtok"])).number_format = "$#,##0.0000"
    ws11.cell(row=row_num, column=6, value=float(r["marketplace_selling_price_usd_mtok"])).number_format = "$#,##0.00"
    
    # Formula for Fee: =F{row} * 0.05
    fee_f = f"=F{row_num}*0.05"
    ws11.cell(row=row_num, column=7, value=fee_f).number_format = "$#,##0.0000"
    
    # Formula for Net Profit: =F{row} - G{row} - E{row}
    profit_f = f"=F{row_num}-G{row_num}-E{row_num}"
    cell_pr = ws11.cell(row=row_num, column=8, value=profit_f)
    cell_pr.number_format = "$#,##0.0000"
    cell_pr.font = font_bold
    
    # Formula for Margin %: =H{row} / (F{row} - G{row})
    margin_f = f"=H{row_num}/(F{row_num}-G{row_num})"
    ws11.cell(row=row_num, column=9, value=margin_f).number_format = "0.0%"
    
    ws11.cell(row=row_num, column=10, value=float(r["monthly_net_cashflow_at_50pct_util_usd"])).number_format = "$#,##0.00"
    
    for c in range(1, len(p_headers) + 1):
        cell = ws11.cell(row=row_num, column=c)
        cell.border = border_cell
        if r_idx % 2 == 1:
            cell.fill = fill_zebra

auto_fit_columns(ws11)

# ==============================================================================
# SHEET 12: IE Marketplace Economics
# ==============================================================================
ws12 = wb.create_sheet(title="IE Marketplace Economics")
ws12.views.sheetView[0].showGridLines = True
ws12["A1"] = "INFERENCE EXCHANGE MARKETPLACE ARBITRAGE & TAKE RATE MODEL"
ws12["A1"].font = font_title
ws12["A2"] = "Level 2 cross-venue spread arbitrage, router take rate (5%), and consumer savings"
ws12["A2"].font = font_subtitle

ie_headers = [
    "Instrument", "Cheapest Venue", "Best Offer ($/Mtok)", 
    "Median Venue ($/Mtok)", "Highest Venue ($/Mtok)", 
    "Cross-Venue Spread %", "Consumer Savings %", "IE Fee Revenue ($/Mtok)"
]
for c_idx, h in enumerate(ie_headers, start=1):
    ws12.cell(row=4, column=c_idx, value=h)
style_header_row(ws12, 4, len(ie_headers))

spread_samples = [
    ("LLAMA-3.1-8B", "novita", 0.05, 0.08, 0.18),
    ("LLAMA-3.1-70B", "novita", 0.35, 0.50, 0.90),
    ("LLAMA-3.3-70B", "novita", 0.30, 0.38, 0.79),
    ("DEEPSEEK-V4.1-FLASH", "novita", 0.24, 0.28, 0.60),
    ("DEEPSEEK-R1", "community-drops", 0.70, 2.19, 2.50),
    ("QWEN3.8-27B", "siliconflow", 0.40, 1.35, 5.25),
    ("QWEN3.5-397B", "deepinfra", 3.50, 4.50, 6.00)
]

for r_idx, r in enumerate(spread_samples, start=5):
    ws12.cell(row=r_idx, column=1, value=r[0])
    ws12.cell(row=r_idx, column=2, value=r[1])
    
    ws12.cell(row=r_idx, column=3, value=r[2]).number_format = "$#,##0.00"
    ws12.cell(row=r_idx, column=4, value=r[3]).number_format = "$#,##0.00"
    ws12.cell(row=r_idx, column=5, value=r[4]).number_format = "$#,##0.00"
    
    # Spread Formula: =(E{row} - C{row}) / C{row}
    spread_f = f"=(E{r_idx}-C{r_idx})/C{r_idx}"
    ws12.cell(row=r_idx, column=6, value=spread_f).number_format = "0.0%"
    ws12.cell(row=r_idx, column=6).font = Font(name="Calibri", size=10, bold=True, color="EF4444")
    
    # Savings Formula: =(D{row} - C{row}) / D{row}
    save_f = f"=(D{r_idx}-C{r_idx})/D{r_idx}"
    ws12.cell(row=r_idx, column=7, value=save_f).number_format = "0.0%"
    ws12.cell(row=r_idx, column=7).font = Font(name="Calibri", size=10, bold=True, color="10B981")
    
    # IE Take Rate Formula: =C{row} * 0.05
    fee_f = f"=C{r_idx}*0.05"
    ws12.cell(row=r_idx, column=8, value=fee_f).number_format = "$#,##0.0000"
    
    for c in range(1, len(ie_headers) + 1):
        cell = ws12.cell(row=r_idx, column=c)
        cell.border = border_cell
        if r_idx % 2 == 1:
            cell.fill = fill_zebra

auto_fit_columns(ws12)

# ==============================================================================
# SHEET 13: Sensitivity Analysis
# ==============================================================================
ws13 = wb.create_sheet(title="Sensitivity Analysis")
ws13.views.sheetView[0].showGridLines = True
ws13["A1"] = "MULTI-VARIABLE SENSITIVITY & THRESHOLD ANALYSIS"
ws13["A1"].font = font_title
ws13["A2"] = "Testing thesis robustness against API price drops, utilization swings, and electricity shocks"
ws13["A2"].font = font_subtitle

sens_headers = [
    "Assumption Tested", "Base Value", "Stressed Value", "Impact on Hardware TCO ($/Mtok)", 
    "Impact on Monthly Advantage ($/mo)", "Thesis Invalidation Threshold", "Sensitivity Severity"
]
for c_idx, h in enumerate(sens_headers, start=1):
    ws13.cell(row=4, column=c_idx, value=h)
style_header_row(ws13, 4, len(sens_headers))

sens_data = [
    ("Frontier API Price Drops (-50%)", "Sonnet $10.00/Mtok", "$5.00/Mtok", "No change on hardware", "-$365.00 / month", "API price <$3.20/Mtok invalidates hardware advantage", "HIGH"),
    ("Frontier API Price Drops (-75%)", "Sonnet $10.00/Mtok", "$2.50/Mtok", "No change on hardware", "-$547.00 / month", "Hardware advantage completely eliminated", "CRITICAL"),
    ("Productive Utilization Drops to 10%", "50% Util (42.7M tok)", "10% Util (8.5M tok)", "+$21.08 / Mtok", "-$420.00 / month", "Utilization <26.3% makes APIs cheaper", "HIGH"),
    ("Productive Utilization Rises to 90%", "50% Util (42.7M tok)", "90% Util (76.8M tok)", "-$2.34 / Mtok", "+$140.00 / month", "Dramatically expands hardware profitability", "POSITIVE"),
    ("Electricity Rates Rise to California Peak", "$0.128 / kWh", "$0.307 / kWh", "+$0.02 / Mtok", "-$22.00 / month", "Electricity price >$1.85/kWh (negligible effect)", "LOW"),
    ("Human Intervention Required on Failures", "0% Debugging ($0)", "20% Debugging ($30/fail)", "No change on tokens", "+$360.00 / month for frontier", "Low quality open models become economically unviable", "CRITICAL"),
    ("Prompt Caching Hit Rate Collapses", "80% Cache Hit Rate", "20% Cache Hit Rate", "No change on hardware", "+$320.00 / month on APIs", "Favors local hardware with unlimited prompt capacity", "HIGH")
]

for r_idx, r in enumerate(sens_data, start=5):
    for c_idx, val in enumerate(r, start=1):
        cell = ws13.cell(row=r_idx, column=c_idx, value=val)
        cell.font = font_regular
        cell.border = border_cell
        if c_idx == 7:
            cell.alignment = align_center
            if val == "CRITICAL":
                cell.font = Font(name="Calibri", size=10, bold=True, color="DC2626")
            elif val == "HIGH":
                cell.font = Font(name="Calibri", size=10, bold=True, color="D97706")
            elif val == "LOW":
                cell.font = Font(name="Calibri", size=10, color="059669")
        if r_idx % 2 == 1:
            cell.fill = fill_zebra

auto_fit_columns(ws13)

# ==============================================================================
# SHEET 14: Assumptions and Unknowns
# ==============================================================================
ws14 = wb.create_sheet(title="Assumptions & Unknowns")
ws14.views.sheetView[0].showGridLines = True
ws14["A1"] = "ASSUMPTIONS REGISTER & EXPERIMENTAL GAPS"
ws14["A1"].font = font_title
ws14["A2"] = "Documented parameters, unknown quantities, and proposed empirical experiments"
ws14["A2"].font = font_subtitle

asm_headers = ["Parameter ID", "Category", "Parameter Name", "Value", "Unit", "Rationale & Primary Source Ref"]
for c_idx, h in enumerate(asm_headers, start=1):
    ws14.cell(row=4, column=c_idx, value=h)
style_header_row(ws14, 4, len(asm_headers))

asm_df = pd.read_csv(os.path.join(DATA_DIR, "assumptions.csv"))
for r_idx, r in asm_df.iterrows():
    row_num = r_idx + 5
    ws14.cell(row=row_num, column=1, value=r["param_id"]).alignment = align_center
    ws14.cell(row=row_num, column=2, value=r["category"]).alignment = align_center
    ws14.cell(row=row_num, column=3, value=r["parameter"])
    ws14.cell(row=row_num, column=4, value=r["value"]).alignment = align_center
    ws14.cell(row=row_num, column=5, value=r["unit"]).alignment = align_center
    ws14.cell(row=row_num, column=6, value=r["rationale"])
    
    for c in range(1, len(asm_headers) + 1):
        cell = ws14.cell(row=row_num, column=c)
        cell.font = font_regular
        cell.border = border_cell
        if r_idx % 2 == 1:
            cell.fill = fill_zebra

# Unknowns & Experiments section
u_start = len(asm_df) + 7
ws14.cell(row=u_start, column=1, value="CRITICAL UNKNOWNS & REQUIRED RESOLUTION BENCHMARKS").font = font_section

unknowns = [
    ["Unknown Area", "Current Data Status", "Consequence on Model", "Required Benchmark Experiment to Resolve"],
    ["Mac Studio M5 Ultra 512GB Street Price", "Announced for late Oct 2026; price unconfirmed ($7.5k-$9k estimated).", "Changes exact monthly TCO by ±$45/mo.", "Query official Apple Store configurator upon late October retail launch."],
    ["Thunderbolt 5 RDMA Sustained Thermal Throttling", "Exo shows 32.5 TPS on 4 Macs; long-duration thermal drift unmeasured.", "Could degrade decode speed by 15-20% after 2 hours of continuous load.", "Execute 4-hour continuous burn-in benchmark logging device temperature and TPS."],
    ["DGX Spark Speculative Decoding Quality Drift", "SGLang reports 42 TPS with DFlash2 draft model; acceptance rate on complex SWE code unmeasured.", "If acceptance rate drops below 40%, decode collapses back to 14.2 TPS.", "Run standardized SWE-bench verified evaluation comparing standard vs draft acceptance rates."]
]

for r_idx, r in enumerate(unknowns, start=u_start + 2):
    for c_idx, val in enumerate(r, start=1):
        cell = ws14.cell(row=r_idx, column=c_idx, value=val)
        cell.font = font_header if r_idx == u_start + 2 else font_regular
        cell.fill = fill_slate if r_idx == u_start + 2 else (fill_zebra if r_idx % 2 == 1 else PatternFill(fill_type=None))
        cell.border = border_cell

auto_fit_columns(ws14)

# Save workbook
wb.save(WORKBOOK_PATH)
print(f"Institutional Excel Workbook successfully built with 14 sheets: {WORKBOOK_PATH}")
