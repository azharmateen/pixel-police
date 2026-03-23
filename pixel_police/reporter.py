"""HTML report generator for visual regression results."""

import base64
import json
import time
from pathlib import Path
from typing import Optional

from .comparator import ComparisonResult


def generate_html_report(results: list[ComparisonResult],
                         output_path: str = ".pixel-police/reports/report.html",
                         title: str = "Pixel Police Report") -> str:
    """Generate an HTML visual regression report.

    Features: side-by-side comparison, swipe slider, pass/fail badges, summary.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    errors = sum(1 for r in results if r.error)
    total = len(results)

    import datetime
    timestamp = datetime.datetime.now().isoformat()

    rows_html = []
    for i, result in enumerate(results):
        status_class = "pass" if result.passed else "fail"
        status_text = "PASS" if result.passed else "FAIL"
        if result.error:
            status_class = "error"
            status_text = "ERROR"

        baseline_img = _embed_image(result.baseline_path)
        current_img = _embed_image(result.current_path)
        diff_img = _embed_image(result.diff_path) if result.diff_path else ""

        row = f"""
        <div class="comparison-card {status_class}">
            <div class="card-header">
                <span class="badge badge-{status_class}">{status_text}</span>
                <span class="page-name">{_get_name(result.current_path)}</span>
                <span class="diff-pct">{result.diff_percent:.2f}% diff ({result.diff_pixels:,} pixels)</span>
            </div>
            {f'<div class="error-msg">{result.error}</div>' if result.error else ''}
            <div class="images">
                <div class="image-panel">
                    <div class="image-label">Baseline</div>
                    {f'<img src="{baseline_img}" alt="Baseline">' if baseline_img else '<div class="no-image">No baseline</div>'}
                </div>
                <div class="image-panel">
                    <div class="image-label">Current</div>
                    {f'<img src="{current_img}" alt="Current">' if current_img else '<div class="no-image">No capture</div>'}
                </div>
                {f'''<div class="image-panel">
                    <div class="image-label">Diff</div>
                    <img src="{diff_img}" alt="Diff">
                </div>''' if diff_img else ''}
            </div>
            <div class="slider-container" id="slider-{i}">
                <input type="range" min="0" max="100" value="50" class="slider"
                       oninput="updateSlider(this, {i})">
                <div class="slider-images" id="slider-images-{i}">
                    {f'<img src="{baseline_img}" class="slider-baseline">' if baseline_img else ''}
                    {f'<img src="{current_img}" class="slider-current" style="clip-path: inset(0 50% 0 0)">' if current_img else ''}
                </div>
            </div>
        </div>
        """
        rows_html.append(row)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #0d1117; color: #c9d1d9; padding: 24px; }}
h1 {{ font-size: 24px; margin-bottom: 8px; color: #58a6ff; }}
.summary {{ display: flex; gap: 16px; margin: 16px 0 24px; }}
.summary-card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px 24px; text-align: center; }}
.summary-card .number {{ font-size: 32px; font-weight: bold; }}
.summary-card .label {{ font-size: 13px; color: #8b949e; }}
.summary-card.pass .number {{ color: #3fb950; }}
.summary-card.fail .number {{ color: #f85149; }}
.summary-card.total .number {{ color: #58a6ff; }}
.comparison-card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; margin-bottom: 24px; overflow: hidden; }}
.comparison-card.fail {{ border-color: #f85149; }}
.card-header {{ padding: 12px 16px; background: #21262d; display: flex; align-items: center; gap: 12px; }}
.badge {{ padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; }}
.badge-pass {{ background: #238636; color: white; }}
.badge-fail {{ background: #da3633; color: white; }}
.badge-error {{ background: #d29922; color: black; }}
.page-name {{ font-family: monospace; font-size: 14px; }}
.diff-pct {{ margin-left: auto; color: #8b949e; font-size: 13px; }}
.error-msg {{ padding: 8px 16px; background: #2d0f0f; color: #f85149; font-size: 13px; }}
.images {{ display: flex; gap: 2px; padding: 16px; overflow-x: auto; }}
.image-panel {{ flex: 1; min-width: 200px; }}
.image-label {{ font-size: 12px; color: #8b949e; margin-bottom: 4px; text-align: center; }}
.image-panel img {{ width: 100%; border: 1px solid #30363d; border-radius: 4px; }}
.no-image {{ padding: 40px; text-align: center; background: #21262d; border-radius: 4px; color: #8b949e; }}
.slider-container {{ padding: 0 16px 16px; }}
.slider {{ width: 100%; margin-bottom: 8px; }}
.slider-images {{ position: relative; overflow: hidden; border: 1px solid #30363d; border-radius: 4px; }}
.slider-images img {{ width: 100%; display: block; }}
.slider-current {{ position: absolute; top: 0; left: 0; }}
.timestamp {{ color: #8b949e; font-size: 12px; }}
</style>
</head>
<body>
<h1>{title}</h1>
<p class="timestamp">Generated: {timestamp}</p>

<div class="summary">
    <div class="summary-card total"><div class="number">{total}</div><div class="label">Total</div></div>
    <div class="summary-card pass"><div class="number">{passed}</div><div class="label">Passed</div></div>
    <div class="summary-card fail"><div class="number">{failed}</div><div class="label">Failed</div></div>
</div>

{''.join(rows_html)}

<script>
function updateSlider(input, idx) {{
    const pct = input.value;
    const container = document.getElementById('slider-images-' + idx);
    const current = container.querySelector('.slider-current');
    if (current) {{
        current.style.clipPath = 'inset(0 ' + (100 - pct) + '% 0 0)';
    }}
}}
</script>
</body>
</html>"""

    Path(output_path).write_text(html, encoding="utf-8")
    return output_path


def _embed_image(filepath: Optional[str]) -> str:
    """Convert image file to base64 data URI."""
    if not filepath or not Path(filepath).exists():
        return ""
    try:
        data = Path(filepath).read_bytes()
        b64 = base64.b64encode(data).decode("ascii")
        return f"data:image/png;base64,{b64}"
    except Exception:
        return ""


def _get_name(filepath: Optional[str]) -> str:
    """Extract readable name from filepath."""
    if not filepath:
        return "unknown"
    return Path(filepath).stem


def generate_summary(results: list[ComparisonResult]) -> dict:
    """Generate a JSON summary of results."""
    return {
        "total": len(results),
        "passed": sum(1 for r in results if r.passed),
        "failed": sum(1 for r in results if not r.passed),
        "errors": sum(1 for r in results if r.error),
        "results": [
            {
                "page": _get_name(r.current_path),
                "baseline": r.baseline_path,
                "current": r.current_path,
                "diff": r.diff_path,
                "diff_percent": r.diff_percent,
                "diff_pixels": r.diff_pixels,
                "passed": r.passed,
                "threshold": r.threshold,
                "error": r.error,
            }
            for r in results
        ],
    }
