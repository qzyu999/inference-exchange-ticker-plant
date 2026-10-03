"""Command-line interface for the Inference Exchange Ticker Plant.

Provides Wall Street-style terminal views: Best Bid/Offer (BBO),
Level 2 Depth of Market, Historical Tape Queries, and scheduled ingest.
"""

from __future__ import annotations

import asyncio
import re
import sys
import time
from pathlib import Path
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from ticker_plant.engine import TickerPlant
from ticker_plant.config import ManifestRegistry
from ticker_plant.tape.analytics import get_bbo, get_depth, get_history_summary
from ticker_plant.tape.export import export_tape_json, export_tape_csv, export_tape_js

console = Console()


def _parse_interval(interval_str: str) -> int:
    """Parse time string like '30m', '1h', '45s' to seconds."""
    match = re.match(r"^(\d+)([smhd]?)$", interval_str.strip().lower())
    if not match:
        raise click.BadParameter(f"Invalid interval: {interval_str}. Use e.g. 30s, 30m, 1h")
    val, unit = match.groups()
    num = int(val)
    if unit in ("", "s"):
        return num
    elif unit == "m":
        return num * 60
    elif unit == "h":
        return num * 3600
    elif unit == "d":
        return num * 86400
    return num


def _default_db_path() -> str:
    """Resolve default DB path, preferring data/tape.db."""
    if Path("data/tape.db").exists():
        return "data/tape.db"
    return "data/tape.db"


@click.group()
def cli():
    """Inference Exchange Ticker Plant — Market Data Engine & Consolidated Tape."""
    pass


# ─── Collect Command ───────────────────────────────────────────

@cli.command()
@click.option("--manifests", "-m", default="manifests", help="Path to manifests directory.")
@click.option("--db", "-d", default=_default_db_path, help="Path to SQLite tape database.")
@click.option("--venues", "-v", default="", help="Comma-separated venue names to poll.")
@click.option("--dry-run", is_flag=True, help="Fetch without committing ticks to tape.")
def collect(manifests: str, db: str, venues: str, dry_run: bool):
    """Run a single collection cycle across active venue feed handlers."""
    plant = TickerPlant(manifests_dir=manifests, db_path=db)
    venue_list = [v.strip() for v in venues.split(",") if v.strip()] or None

    console.print(Panel(
        f"[bold cyan]Ingesting Market Data[/bold cyan]\n"
        f"Manifests: [yellow]{manifests}[/yellow] | Tape DB: [yellow]{db}[/yellow]",
        box=box.ROUNDED,
    ))

    with console.status("[bold green]Polling venue feed handlers..."):
        report = asyncio.run(plant.run_cycle(selected_venues=venue_list))

    table = Table(title="Feed Handlers Status", box=box.SIMPLE_HEAVY)
    table.add_column("Venue", style="cyan", no_wrap=True)
    table.add_column("Status", style="bold")
    table.add_column("Quotes Extracted", justify="right")

    for v, count in report.venue_breakdown.items():
        status = "[green]OK[/green]" if count > 0 else "[yellow]0 quotes[/yellow]"
        table.add_row(v, status, str(count))

    console.print(table)
    console.print(
        f"\n[bold green]✓ Cycle complete[/bold green] in {report.duration_seconds}s: "
        f"[cyan]{report.quotes_received}[/cyan] quotes received, "
        f"[bold]{report.ticks_committed}[/bold] ticks committed to tape.\n"
    )


# ─── Watch / Daemon Command ───────────────────────────────────

@cli.command()
@click.option("--manifests", "-m", default="manifests", help="Path to manifests directory.")
@click.option("--db", "-d", default=_default_db_path, help="Path to SQLite tape database.")
@click.option("--interval", "-i", default="30m", help="Poll interval (e.g. 30s, 30m, 1h).")
def watch(manifests: str, db: str, interval: str):
    """Run continuous collection daemon with a live terminal countdown."""
    seconds = _parse_interval(interval)
    plant = TickerPlant(manifests_dir=manifests, db_path=db)

    console.print(Panel(
        f"[bold green]Starting Ticker Plant Ingestion Loop[/bold green]\n"
        f"Poll interval: [cyan]{interval}[/cyan] ({seconds}s) | Press [bold red]Ctrl+C[/bold red] to stop.",
        box=box.ROUNDED,
    ))

    cycle = 1
    try:
        while True:
            console.rule(f"[bold cyan]Cycle #{cycle} — {time.strftime('%Y-%m-%d %H:%M:%SZ')}[/bold cyan]")
            report = asyncio.run(plant.run_cycle())
            console.print(
                f"[green]✓[/green] Ingested {report.venues_succeeded}/{report.venues_polled} venues. "
                f"Committed [bold]{report.ticks_committed}[/bold] ticks to tape in {report.duration_seconds}s."
            )

            console.print(f"[dim]Next cycle in {interval}...[/dim]\n")
            time.sleep(seconds)
            cycle += 1
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Ticker Plant daemon stopped cleanly.[/bold yellow]")


# ─── Tape Subcommands ──────────────────────────────────────────

@cli.group()
def tape():
    """Query the Consolidated Tape (BBO, Market Depth, History)."""
    pass


@tape.command("bbo")
@click.option("--db", "-d", default=_default_db_path, help="Path to SQLite tape database.")
@click.option("--instrument", "-i", default="", help="Filter by canonical instrument.")
def tape_bbo(db: str, instrument: str):
    """Display National Best Bid & Offer (top of book) across venues."""
    plant = TickerPlant(db_path=db)
    inst_param = instrument if instrument else None
    results = get_bbo(plant.store, inst_param)

    if not results:
        console.print("[yellow]No market ticks found in tape. Run 'ticker-plant collect' first.[/yellow]")
        return

    table = Table(title="Consolidated Tape — Best Available Offers (BBO)", box=box.ROUNDED)
    table.add_column("Instrument", style="bold cyan")
    table.add_column("Best Venue", style="green")
    table.add_column("Best Out ($/M)", justify="right", style="bold green")
    table.add_column("Best In ($/M)", justify="right")
    table.add_column("Median Out", justify="right")
    table.add_column("Highest Out", justify="right", style="red")
    table.add_column("Spread %", justify="right", style="yellow")
    table.add_column("Venues", justify="center")

    for r in results:
        table.add_row(
            r.instrument,
            r.cheapest_output_venue,
            f"${r.cheapest_output_price:.2f}",
            f"${r.cheapest_input_price:.2f}",
            f"${r.median_output_price:.2f}",
            f"${r.highest_output_price:.2f}",
            f"+{r.spread_pct:.0f}%",
            str(r.venue_count),
        )

    console.print(table)


@tape.command("depth")
@click.argument("instrument")
@click.option("--db", "-d", default=_default_db_path, help="Path to SQLite tape database.")
def tape_depth(instrument: str, db: str):
    """Show Level 2 order book / market depth across all venues for an instrument."""
    plant = TickerPlant(db_path=db)
    depth = get_depth(plant.store, instrument.upper())

    if not depth:
        console.print(f"[yellow]No active offers found for {instrument.upper()}.[/yellow]")
        return

    table = Table(title=f"Level 2 Market Depth — {instrument.upper()}", box=box.ROUNDED)
    table.add_column("Venue", style="cyan")
    table.add_column("Type", style="dim")
    table.add_column("Raw Model ID")
    table.add_column("Input ($/M)", justify="right")
    table.add_column("Cache Read", justify="right")
    table.add_column("Output ($/M)", justify="right", style="bold green")
    table.add_column("Context", justify="right")
    table.add_column("Age (hrs)", justify="right", style="dim")

    for d in depth:
        cache_str = f"${d.cache_read_usd_mtok:.2f}" if d.cache_read_usd_mtok > 0 else "—"
        table.add_row(
            d.venue,
            d.venue_type,
            d.raw_model_id,
            f"${d.input_usd_mtok:.2f}",
            cache_str,
            f"${d.output_usd_mtok:.2f}",
            f"{d.context_length:,}" if d.context_length else "—",
            f"{d.age_hours}h",
        )

    console.print(table)


@tape.command("history")
@click.argument("instrument")
@click.option("--db", "-d", default=_default_db_path, help="Path to SQLite tape database.")
@click.option("--days", default=30, help="Days of history.")
def tape_history(instrument: str, db: str, days: int):
    """Show daily price trajectory and spread history for an instrument."""
    plant = TickerPlant(db_path=db)
    history = get_history_summary(plant.store, instrument.upper(), days=days)

    if not history:
        console.print(f"[yellow]No history found for {instrument.upper()} in past {days} days.[/yellow]")
        return

    table = Table(title=f"Historical Price Trajectory — {instrument.upper()} ({days}d)", box=box.ROUNDED)
    table.add_column("Date", style="bold")
    table.add_column("Min Out ($/M)", justify="right", style="green")
    table.add_column("Median Out", justify="right")
    table.add_column("Max Out ($/M)", justify="right", style="red")
    table.add_column("Spread %", justify="right", style="yellow")
    table.add_column("Venues", justify="center")

    for h in history:
        spread = ((h["max_output"] - h["min_output"]) / h["min_output"] * 100.0) if h["min_output"] > 0 else 0
        table.add_row(
            h["date"],
            f"${h['min_output']:.2f}",
            f"${h['median_output']:.2f}",
            f"${h['max_output']:.2f}",
            f"+{spread:.0f}%",
            str(h["venue_count"]),
        )

    console.print(table)


@tape.command("export")
@click.option("--db", "-d", default=_default_db_path, help="Path to SQLite tape database.")
@click.option("--format", "-f", type=click.Choice(["json", "csv", "js"]), default="json")
@click.option("--output", "-o", required=True, help="Destination file path.")
@click.option("--latest-only", is_flag=True, help="Export only latest quote per venue.")
def tape_export(db: str, format: str, output: str, latest_only: bool):
    """Export the Consolidated Tape ticks to JSON, CSV, or JS."""
    plant = TickerPlant(db_path=db)
    if format == "json":
        export_tape_json(plant.store, output, latest_only=latest_only)
    elif format == "csv":
        export_tape_csv(plant.store, output, latest_only=latest_only)
    elif format == "js":
        export_tape_js(plant.store, output, latest_only=latest_only)
    console.print(f"[green]✓ Exported tape to [bold]{output}[/bold] ({format.upper()})[/green]")


# ─── Manifest Validation ───────────────────────────────────────

@cli.command("validate")
@click.argument("manifests_dir", default="manifests")
def validate(manifests_dir: str):
    """Validate all Kubernetes-style YAML manifests in the directory."""
    registry = ManifestRegistry()
    count = registry.load_directory(manifests_dir)
    console.print(f"[bold green]✓ Validated {count} manifests in '{manifests_dir}':[/bold green]")
    console.print(f"  • Feed Handlers: [cyan]{len(registry.feed_handlers)}[/cyan]")
    console.print(f"  • Canonical Instruments: [cyan]{len(registry.instruments)}[/cyan]")


# ─── Bootstrap Command ─────────────────────────────────────────

@cli.command("bootstrap")
@click.option("--db", "-d", default=_default_db_path, help="Path to SQLite tape database.")
def bootstrap(db: str):
    """Backfill initial historical rate cards from community price archives."""
    from ticker_plant.config import FeedHandlerManifest
    plant = TickerPlant(db_path=db)

    console.print("[bold cyan]Bootstrapping historical rate cards from LiteLLM community archive...[/bold cyan]")
    manifest_dict = {
        "apiVersion": "tickerplant.inference.exchange/v1alpha1",
        "kind": "FeedHandler",
        "metadata": {
            "name": "litellm-archive",
            "venue_type": "aggregator",
        },
        "spec": {
            "driver": "litellm-archive",
        },
    }
    manifest = FeedHandlerManifest.model_validate(manifest_dict)
    from ticker_plant.feed_handlers.litellm_archive import LiteLLMArchiveFeedHandler

    handler = LiteLLMArchiveFeedHandler(manifest)
    with console.status("[bold green]Downloading and parsing price database..."):
        quotes = asyncio.run(handler.fetch_quotes())

    ticks = [
        plant.registry.resolve_instrument(q.raw_model_id)
        for q in quotes
    ]
    from ticker_plant.models import TapeTick
    tape_ticks = [
        TapeTick.from_quote(q, instrument=inst)
        for q, inst in zip(quotes, ticks)
    ]
    committed = plant.store.append_ticks(tape_ticks)
    console.print(f"[bold green]✓ Bootstrapped {committed} rate-card ticks into {db}![/bold green]")


# ─── View / Web Dashboard Command ──────────────────────────────

@cli.command("view")
@click.option("--port", "-p", default=8765, help="Port to serve dashboard on.")
@click.option("--no-browser", is_flag=True, help="Do not open browser automatically.")
def view(port: int, no_browser: bool):
    """Launch the interactive Consolidated Tape web dashboard in your browser."""
    import http.server
    import socketserver
    import webbrowser
    import os

    web_dir = Path(__file__).parent.parent
    os.chdir(str(web_dir))

    url = f"http://localhost:{port}/index.html"
    console.print(Panel(
        f"[bold green]Starting Ticker Plant Web Dashboard[/bold green]\n"
        f"URL: [cyan]{url}[/cyan]\n"
        f"Serving from: [yellow]{web_dir}[/yellow]\n"
        f"Press [bold red]Ctrl+C[/bold red] to stop.",
        box=box.ROUNDED,
    ))

    if not no_browser:
        webbrowser.open(url)

    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            console.print("\n[bold yellow]Web dashboard stopped.[/bold yellow]")


def main():
    cli()


if __name__ == "__main__":
    main()
