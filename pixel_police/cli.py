"""CLI for pixel-police: visual regression testing."""

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .config import Config, PageConfig, Viewport, VIEWPORTS, load_config, save_config
from .capturer import capture_screenshots
from .baseline import BaselineManager
from .reporter import generate_html_report, generate_summary

console = Console()


@click.group()
def cli():
    """pixel-police: Visual regression testing with screenshot comparison."""
    pass


@cli.command()
@click.argument("base_url")
@click.option("--pages", "-p", default="/", help="Comma-separated page paths")
@click.option("--viewports", "-v", default="desktop",
              help="Comma-separated viewports: desktop, tablet, mobile")
@click.option("--output", "-o", default=None, help="Output directory")
@click.option("--wait", "-w", default=500, help="Wait time after page load (ms)")
@click.option("--config", "-c", "config_path", default=".pixel-police.json",
              help="Config file path")
def capture(base_url, pages, viewports, output, wait, config_path):
    """Capture screenshots of pages at specified viewports."""
    # Build config
    config = Config(base_url=base_url, wait_before_capture=wait)

    # Parse pages
    page_paths = [p.strip() for p in pages.split(",")]
    config.pages = [PageConfig(path=p) for p in page_paths]

    # Parse viewports
    vp_names = [v.strip() for v in viewports.split(",")]
    config.viewports = []
    for name in vp_names:
        if name in VIEWPORTS:
            config.viewports.append(VIEWPORTS[name])
        else:
            console.print(f"[yellow]Unknown viewport: {name}. Using desktop.[/yellow]")

    if not config.viewports:
        config.viewports = [VIEWPORTS["desktop"]]

    total = len(config.pages) * len(config.viewports)
    console.print(f"\n[bold]Capturing {total} screenshot(s)...[/bold]")
    console.print(f"  URL:       {base_url}")
    console.print(f"  Pages:     {', '.join(page_paths)}")
    console.print(f"  Viewports: {', '.join(v.label for v in config.viewports)}")
    console.print()

    results = capture_screenshots(config, output_dir=output)

    # Results table
    table = Table(title="Capture Results")
    table.add_column("Page", style="cyan")
    table.add_column("Viewport")
    table.add_column("Status")
    table.add_column("File")

    for r in results:
        status = "[green]OK[/green]" if r.success else f"[red]FAIL: {r.error}[/red]"
        table.add_row(r.page_path, r.viewport, status, Path(r.filepath).name)

    console.print(table)

    succeeded = sum(1 for r in results if r.success)
    console.print(f"\n[green]{succeeded}/{total} captured successfully[/green]")


@cli.command()
@click.option("--config", "-c", "config_path", default=".pixel-police.json",
              help="Config file path")
@click.option("--threshold", "-t", default=None, type=float, help="Override diff threshold (%)")
@click.option("--capture-dir", default=None, help="Captures directory")
@click.option("--report", "-r", default=None, help="Report output path")
def compare(config_path, threshold, capture_dir, report):
    """Compare current captures against baselines."""
    config = load_config(config_path)
    if threshold is not None:
        config.threshold = threshold

    manager = BaselineManager(config)
    cap_dir = capture_dir or config.capture_dir

    if not Path(cap_dir).exists():
        console.print(f"[red]No captures found at {cap_dir}. Run 'capture' first.[/red]")
        sys.exit(1)

    console.print(f"\n[bold]Comparing captures against baselines...[/bold]")
    console.print(f"  Threshold: {config.threshold}%")
    console.print()

    results = manager.compare_all(cap_dir, threshold=threshold)

    if not results:
        console.print("[yellow]No captures found to compare.[/yellow]")
        return

    # Results table
    table = Table(title="Comparison Results")
    table.add_column("Page", style="cyan")
    table.add_column("Status")
    table.add_column("Diff %", justify="right")
    table.add_column("Diff Pixels", justify="right")
    table.add_column("Details")

    for r in results:
        if r.error:
            status = "[yellow]ERROR[/yellow]"
        elif r.passed:
            status = "[green]PASS[/green]"
        else:
            status = "[red]FAIL[/red]"

        name = Path(r.current_path).stem if r.current_path else "unknown"
        details = r.error or ""
        if not r.dimensions_match:
            details = f"Size: {r.baseline_size} vs {r.current_size}"

        table.add_row(name, status, f"{r.diff_percent:.2f}%",
                       f"{r.diff_pixels:,}", details)

    console.print(table)

    # Generate report
    report_path = report or str(Path(config.report_dir) / "report.html")
    generate_html_report(results, output_path=report_path)
    console.print(f"\n[green]Report:[/green] {report_path}")

    # Summary
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)

    if failed > 0:
        console.print(f"\n[red]{failed} comparison(s) failed[/red]")
        sys.exit(1)
    else:
        console.print(f"\n[green]All {passed} comparison(s) passed[/green]")


@cli.command()
@click.option("--capture-dir", default=None, help="Captures directory to approve")
@click.option("--config", "-c", "config_path", default=".pixel-police.json")
@click.option("--page", "-p", default=None, help="Approve only specific page name")
def approve(capture_dir, config_path, page):
    """Approve current captures as new baselines."""
    config = load_config(config_path)
    manager = BaselineManager(config)
    cap_dir = capture_dir or config.capture_dir

    if not Path(cap_dir).exists():
        console.print(f"[red]No captures found at {cap_dir}.[/red]")
        sys.exit(1)

    if page:
        # Approve specific page
        matches = list(Path(cap_dir).glob(f"{page}*.png"))
        matches = [m for m in matches if ".meta." not in m.name]
        if not matches:
            console.print(f"[red]No captures found matching '{page}'.[/red]")
            sys.exit(1)
        for m in matches:
            stem = m.stem
            parts = stem.rsplit("_", 2)
            page_name = parts[0]
            viewport = "_".join(parts[1:]) if len(parts) > 1 else "default"
            manager.approve(str(m), page_name, viewport)
            console.print(f"  [green]Approved:[/green] {m.name}")
    else:
        approved = manager.approve_all(cap_dir)
        console.print(f"\n[green]Approved {len(approved)} baseline(s)[/green]")
        for path in approved:
            console.print(f"  {Path(path).name}")


@cli.command()
@click.option("--config", "-c", "config_path", default=".pixel-police.json")
@click.option("--capture-dir", default=None, help="Captures directory")
@click.option("--output", "-o", default=None, help="Report output path")
def report(config_path, capture_dir, output):
    """Generate HTML comparison report."""
    config = load_config(config_path)
    manager = BaselineManager(config)
    cap_dir = capture_dir or config.capture_dir

    if not Path(cap_dir).exists():
        console.print(f"[red]No captures found at {cap_dir}.[/red]")
        sys.exit(1)

    results = manager.compare_all(cap_dir)
    report_path = output or str(Path(config.report_dir) / "report.html")

    generate_html_report(results, output_path=report_path)

    summary = generate_summary(results)
    summary_path = report_path.replace(".html", ".json")
    Path(summary_path).write_text(json.dumps(summary, indent=2))

    console.print(f"\n[green]HTML Report:[/green] {report_path}")
    console.print(f"[green]JSON Summary:[/green] {summary_path}")
    console.print(f"\n  Total: {summary['total']}, "
                  f"Passed: {summary['passed']}, "
                  f"Failed: {summary['failed']}")


@cli.command()
@click.argument("base_url")
@click.option("--pages", "-p", default="/", help="Comma-separated page paths")
@click.option("--viewports", "-v", default="desktop", help="Comma-separated viewports")
@click.option("--threshold", "-t", default=0.1, help="Diff threshold percentage")
def init(base_url, pages, viewports, threshold):
    """Initialize pixel-police configuration file."""
    page_paths = [p.strip() for p in pages.split(",")]
    vp_names = [v.strip() for v in viewports.split(",")]

    config = Config(
        base_url=base_url,
        pages=[PageConfig(path=p) for p in page_paths],
        viewports=[VIEWPORTS[v] for v in vp_names if v in VIEWPORTS],
        threshold=threshold,
    )

    save_config(config)
    console.print(f"\n[green]Created .pixel-police.json[/green]")
    console.print(f"  URL:       {base_url}")
    console.print(f"  Pages:     {', '.join(page_paths)}")
    console.print(f"  Viewports: {', '.join(vp_names)}")
    console.print(f"  Threshold: {threshold}%")
    console.print(f"\nNext steps:")
    console.print(f"  1. pixel-police capture {base_url}")
    console.print(f"  2. pixel-police approve")
    console.print(f"  3. (make changes)")
    console.print(f"  4. pixel-police capture {base_url}")
    console.print(f"  5. pixel-police compare")


if __name__ == "__main__":
    cli()
