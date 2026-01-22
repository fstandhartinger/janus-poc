"""Command-line interface for janus-bench."""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from . import __version__
from .config import Settings
from .models import BenchmarkReport, Suite
from .runner import BenchmarkRunner

console = Console()


def print_report_summary(report: BenchmarkReport) -> None:
    """Print a summary table of the benchmark report."""
    # Header
    console.print()
    console.print(f"[bold green]Janus Benchmark Report[/bold green]")
    console.print(f"Run ID: {report.run_id}")
    console.print(f"Suite: {report.suite}")
    console.print(f"Target: {report.target_url}")
    console.print(f"Model: {report.model}")
    console.print()

    # Scores table
    scores_table = Table(title="Scores (0-100)")
    scores_table.add_column("Component", style="cyan")
    scores_table.add_column("Score", justify="right", style="green")
    scores_table.add_column("Weight", justify="right", style="dim")

    scores_table.add_row(
        "[bold]Composite[/bold]",
        f"[bold]{report.composite_score:.1f}[/bold]",
        "-",
    )
    scores_table.add_row(
        "Quality",
        f"{report.quality_score:.1f}",
        f"{report.weights['quality']}%",
    )
    scores_table.add_row(
        "Speed",
        f"{report.speed_score:.1f}",
        f"{report.weights['speed']}%",
    )
    scores_table.add_row(
        "Cost",
        f"{report.cost_score:.1f}",
        f"{report.weights['cost']}%",
    )
    scores_table.add_row(
        "Streaming",
        f"{report.streaming_score:.1f}",
        f"{report.weights['streaming']}%",
    )
    scores_table.add_row(
        "Multimodal",
        f"{report.multimodal_score:.1f}",
        f"{report.weights['multimodal']}%",
    )

    console.print(scores_table)
    console.print()

    # Metrics table
    metrics_table = Table(title="Metrics")
    metrics_table.add_column("Metric", style="cyan")
    metrics_table.add_column("Value", justify="right")

    metrics_table.add_row("Total Tasks", str(report.total_tasks))
    metrics_table.add_row("Passed", f"[green]{report.passed_tasks}[/green]")
    metrics_table.add_row("Failed", f"[red]{report.failed_tasks}[/red]")
    metrics_table.add_row("Avg Latency", f"{report.avg_latency_seconds:.2f}s")
    metrics_table.add_row("P50 Latency", f"{report.p50_latency_seconds:.2f}s")

    if report.avg_ttft_seconds:
        metrics_table.add_row("Avg TTFT", f"{report.avg_ttft_seconds:.2f}s")
    if report.max_gap_seconds:
        metrics_table.add_row("Max Gap", f"{report.max_gap_seconds:.2f}s")

    metrics_table.add_row("Total Tokens", str(report.total_tokens))
    metrics_table.add_row("Total Cost", f"${report.total_cost_usd:.4f}")

    console.print(metrics_table)
    console.print()

    # Task results
    results_table = Table(title="Task Results")
    results_table.add_column("Task ID", style="cyan")
    results_table.add_column("Type")
    results_table.add_column("Status", justify="center")
    results_table.add_column("Latency", justify="right")
    results_table.add_column("Quality", justify="right")

    for result in report.results:
        status = "[green]PASS[/green]" if result.success else "[red]FAIL[/red]"
        results_table.add_row(
            result.task_id,
            result.task_type.value,
            status,
            f"{result.latency_seconds:.2f}s",
            f"{result.quality_score * 100:.0f}%",
        )

    console.print(results_table)


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """Janus Benchmark Runner - Evaluate competitors against the Janus Gateway."""
    pass


@main.command()
@click.option(
    "--target",
    "-t",
    default="http://localhost:8000",
    help="Target gateway URL",
)
@click.option(
    "--suite",
    "-s",
    default="public/dev",
    type=click.Choice(["public/train", "public/dev", "private/test"]),
    help="Benchmark suite to run",
)
@click.option(
    "--model",
    "-m",
    default="janus-baseline",
    help="Model name to use in requests",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file for JSON results",
)
@click.option(
    "--timeout",
    default=300,
    help="Request timeout in seconds",
)
def run(
    target: str,
    suite: str,
    model: str,
    output: Optional[str],
    timeout: int,
) -> None:
    """Run benchmark suite against a target gateway."""
    console.print(f"[bold]Janus Benchmark Runner v{__version__}[/bold]")
    console.print(f"Target: {target}")
    console.print(f"Suite: {suite}")
    console.print(f"Model: {model}")
    console.print()

    # Create settings override
    settings = Settings(
        target_url=target,
        model=model,
        request_timeout=timeout,
    )

    # Run the benchmark
    async def run_benchmark() -> BenchmarkReport:
        runner = BenchmarkRunner(settings)
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Running benchmark...", total=None)

                def update_progress(current: int, total: int, result) -> None:
                    status = "PASS" if result.success else "FAIL"
                    progress.update(
                        task,
                        description=f"[{current}/{total}] {result.task_id}: {status}",
                    )

                report = await runner.run_suite(suite, progress_callback=update_progress)
                return report
        finally:
            await runner.close()

    try:
        report = asyncio.run(run_benchmark())
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

    # Print summary
    print_report_summary(report)

    # Save results to file
    if output:
        output_path = Path(output)
    else:
        output_path = Path(f"bench_results_{report.run_id}.json")

    with open(output_path, "w") as f:
        json.dump(report.model_dump(mode="json"), f, indent=2, default=str)

    console.print(f"[dim]Results saved to: {output_path}[/dim]")


@main.command()
def list_suites() -> None:
    """List available benchmark suites."""
    console.print("[bold]Available Benchmark Suites[/bold]")
    console.print()

    for suite in Suite:
        console.print(f"  - {suite.value}")


@main.command()
@click.argument("report_file", type=click.Path(exists=True))
def show(report_file: str) -> None:
    """Display a saved benchmark report."""
    with open(report_file, "r") as f:
        data = json.load(f)

    report = BenchmarkReport(**data)
    print_report_summary(report)


if __name__ == "__main__":
    main()
