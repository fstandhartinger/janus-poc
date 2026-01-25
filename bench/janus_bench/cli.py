"""Command-line interface for janus-bench."""

import asyncio
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from . import __version__
from .analysis.compare_baselines import compare_baselines_report
from .analysis.performance_report import PerformanceMetrics, analyze_benchmark_results
from .benchmarks import get_janus_benchmarks, get_janus_benchmark_names
from .config import Settings
from .models import BenchmarkReport, Suite, TaskResult
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


def print_performance_metrics(metrics: PerformanceMetrics) -> None:
    """Print a summary table of derived performance metrics."""
    console.print()
    metrics_table = Table(title="Performance Metrics")
    metrics_table.add_column("Metric", style="cyan")
    metrics_table.add_column("Value", justify="right")

    metrics_table.add_row("Composite Score", f"{metrics.composite_score:.2f}")
    metrics_table.add_row("Quality Score", f"{metrics.quality_score:.2f}")
    metrics_table.add_row("Speed Score", f"{metrics.speed_score:.2f}")
    metrics_table.add_row("Cost Score", f"{metrics.cost_score:.2f}")
    metrics_table.add_row("Streaming Score", f"{metrics.streaming_score:.2f}")
    metrics_table.add_row("Multimodal Score", f"{metrics.multimodal_score:.2f}")
    metrics_table.add_row("Avg TTFT", f"{metrics.avg_ttft_ms:.1f} ms")
    metrics_table.add_row("P50 TTFT", f"{metrics.p50_ttft_ms:.1f} ms")
    metrics_table.add_row("P95 TTFT", f"{metrics.p95_ttft_ms:.1f} ms")
    metrics_table.add_row("Avg TPS", f"{metrics.avg_tps:.2f}")
    metrics_table.add_row("P50 TPS", f"{metrics.p50_tps:.2f}")
    metrics_table.add_row("P95 TPS", f"{metrics.p95_tps:.2f}")
    metrics_table.add_row("Avg Latency", f"{metrics.avg_latency_seconds:.2f}s")
    metrics_table.add_row("P50 Latency", f"{metrics.p50_latency_seconds:.2f}s")
    metrics_table.add_row("P95 Latency", f"{metrics.p95_latency_seconds:.2f}s")
    metrics_table.add_row("Continuity Score", f"{metrics.continuity_score:.2f}")
    metrics_table.add_row("Continuity Gaps", str(metrics.continuity_gap_count))
    metrics_table.add_row("Total Tokens", str(metrics.total_tokens))
    metrics_table.add_row("Avg Tokens/Task", f"{metrics.avg_tokens_per_task:.1f}")
    metrics_table.add_row("Total Cost", f"${metrics.total_cost_usd:.4f}")
    metrics_table.add_row("Avg Cost/Task", f"${metrics.avg_cost_per_task:.4f}")

    console.print(metrics_table)

    if metrics.tasks_by_benchmark:
        breakdown = Table(title="Benchmark Breakdown")
        breakdown.add_column("Benchmark", style="cyan")
        breakdown.add_column("Total", justify="right")
        breakdown.add_column("Passed", justify="right")
        breakdown.add_column("Failed", justify="right")
        breakdown.add_column("Avg Latency", justify="right")
        breakdown.add_column("Avg Quality", justify="right")
        for name, details in metrics.tasks_by_benchmark.items():
            breakdown.add_row(
                name,
                str(details.get("total", 0)),
                str(details.get("passed", 0)),
                str(details.get("failed", 0)),
                f"{details.get('avg_latency_seconds', 0.0):.2f}s",
                f"{details.get('avg_quality_score', 0.0):.2f}",
            )
        console.print()
        console.print(breakdown)


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
    type=click.Choice(["public/train", "public/dev", "private/test", "janus/intelligence"]),
    help="Benchmark suite to run",
)
@click.option(
    "--benchmark",
    "-b",
    type=click.Choice(get_janus_benchmark_names()),
    help="Optional Janus benchmark to run",
)
@click.option(
    "--model",
    "-m",
    default="janus-baseline-agent-cli",
    help="Model name to use in requests",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file for JSON results",
)
@click.option(
    "--subset",
    default=100,
    type=click.IntRange(1, 100),
    help="Subset percentage of tasks to run (1-100)",
)
@click.option(
    "--seed",
    default=42,
    type=int,
    help="Random seed for deterministic sampling",
)
@click.option(
    "--timeout",
    default=300,
    help="Request timeout in seconds",
)
def run(
    target: str,
    suite: str,
    benchmark: Optional[str],
    model: str,
    output: Optional[str],
    subset: int,
    seed: int,
    timeout: int,
) -> None:
    """Run benchmark suite against a target gateway."""
    console.print(f"[bold]Janus Benchmark Runner v{__version__}[/bold]")
    console.print(f"Target: {target}")
    console.print(f"Suite: {suite}")
    if benchmark:
        console.print(f"Benchmark: {benchmark}")
    console.print(f"Model: {model}")
    console.print(f"Subset: {subset}% (seed={seed})")
    console.print()

    # Create settings override
    settings = Settings(
        target_url=target,
        model=model,
        request_timeout=timeout,
        subset_percent=subset,
        seed=seed,
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

                def update_progress(current: int, total: int, result: TaskResult) -> None:
                    status = "PASS" if result.success else "FAIL"
                    progress.update(
                        task,
                        description=f"[{current}/{total}] {result.task_id}: {status}",
                    )

                report = await runner.run_suite(
                    suite,
                    benchmark=benchmark,
                    progress_callback=update_progress,
                )
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
def list_benchmarks() -> None:
    """List available Janus benchmarks."""
    console.print("[bold]Janus Benchmarks[/bold]")
    console.print()

    for benchmark in get_janus_benchmarks():
        console.print(f"  - {benchmark.display_name} ({benchmark.name})")
        console.print(f"    Category: {benchmark.category}")
        console.print(f"    Items: {benchmark.total_items}")
        console.print(f"    Description: {benchmark.description}")
        console.print()


@main.command()
@click.argument("report_file", type=click.Path(exists=True))
def show(report_file: str) -> None:
    """Display a saved benchmark report."""
    with open(report_file, "r") as f:
        data = json.load(f)

    report = BenchmarkReport(**data)
    print_report_summary(report)


@main.command()
@click.argument("report_file", type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output JSON file for performance metrics",
)
def analyze(report_file: str, output: Optional[str]) -> None:
    """Analyze a benchmark report for performance metrics."""
    metrics = analyze_benchmark_results(report_file)
    print_performance_metrics(metrics)

    if output:
        output_path = Path(output)
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(asdict(metrics), handle, indent=2)
        console.print(f"[dim]Analysis saved to: {output_path}[/dim]")


@main.command()
@click.argument("cli_report", type=click.Path(exists=True))
@click.argument("langchain_report", type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output JSON file for comparison results",
)
def compare(cli_report: str, langchain_report: str, output: Optional[str]) -> None:
    """Compare two benchmark reports (CLI vs LangChain)."""
    comparison = compare_baselines_report(cli_report, langchain_report)

    winners = Table(title="Baseline Winners")
    winners.add_column("Category", style="cyan")
    winners.add_column("Winner", justify="right", style="green")
    for category, winner in comparison["winner_by_category"].items():
        winners.add_row(category, str(winner))

    deltas = Table(title="Score Deltas (CLI - LangChain)")
    deltas.add_column("Category", style="cyan")
    deltas.add_column("Delta", justify="right")
    for category, delta in comparison["deltas"].items():
        deltas.add_row(category, f"{delta:+.2f}")

    console.print()
    console.print(winners)
    console.print()
    console.print(deltas)

    if output:
        output_path = Path(output)
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(comparison, handle, indent=2)
        console.print(f"[dim]Comparison saved to: {output_path}[/dim]")


if __name__ == "__main__":
    main()
