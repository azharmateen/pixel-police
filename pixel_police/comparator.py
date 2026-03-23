"""Image comparator: pixel-by-pixel diff with threshold and overlay."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw


@dataclass
class ComparisonResult:
    baseline_path: str
    current_path: str
    diff_path: Optional[str]
    diff_percent: float
    total_pixels: int
    diff_pixels: int
    passed: bool
    threshold: float
    error: Optional[str] = None
    dimensions_match: bool = True
    baseline_size: tuple = (0, 0)
    current_size: tuple = (0, 0)


@dataclass
class IgnoreBox:
    x: int
    y: int
    width: int
    height: int


def compare_images(baseline_path: str, current_path: str,
                   diff_output_path: Optional[str] = None,
                   threshold: float = 0.1,
                   pixel_tolerance: int = 10,
                   ignore_regions: Optional[list[IgnoreBox]] = None,
                   highlight_color: tuple = (255, 0, 0, 180)) -> ComparisonResult:
    """Compare two images pixel-by-pixel.

    Args:
        baseline_path: Path to baseline screenshot
        current_path: Path to current screenshot
        diff_output_path: Path to save diff overlay image
        threshold: Maximum allowed diff percentage (0-100)
        pixel_tolerance: Per-channel tolerance for pixel comparison (0-255)
        ignore_regions: Regions to skip during comparison
        highlight_color: RGBA color for highlighting changed pixels

    Returns:
        ComparisonResult with diff details
    """
    if not Path(baseline_path).exists():
        return ComparisonResult(
            baseline_path=baseline_path,
            current_path=current_path,
            diff_path=None,
            diff_percent=0,
            total_pixels=0,
            diff_pixels=0,
            passed=False,
            threshold=threshold,
            error=f"Baseline not found: {baseline_path}",
        )

    if not Path(current_path).exists():
        return ComparisonResult(
            baseline_path=baseline_path,
            current_path=current_path,
            diff_path=None,
            diff_percent=0,
            total_pixels=0,
            diff_pixels=0,
            passed=False,
            threshold=threshold,
            error=f"Current screenshot not found: {current_path}",
        )

    baseline = Image.open(baseline_path).convert("RGBA")
    current = Image.open(current_path).convert("RGBA")

    # Check dimensions
    if baseline.size != current.size:
        return ComparisonResult(
            baseline_path=baseline_path,
            current_path=current_path,
            diff_path=None,
            diff_percent=100,
            total_pixels=max(baseline.size[0] * baseline.size[1],
                             current.size[0] * current.size[1]),
            diff_pixels=0,
            passed=False,
            threshold=threshold,
            dimensions_match=False,
            baseline_size=baseline.size,
            current_size=current.size,
            error=f"Size mismatch: baseline={baseline.size}, current={current.size}",
        )

    width, height = baseline.size
    total_pixels = width * height

    # Build ignore mask
    ignore_mask = set()
    if ignore_regions:
        for region in ignore_regions:
            for y in range(region.y, min(region.y + region.height, height)):
                for x in range(region.x, min(region.x + region.width, width)):
                    ignore_mask.add((x, y))

    # Pixel comparison
    baseline_data = baseline.load()
    current_data = current.load()

    diff_pixels = 0
    diff_positions = []

    for y in range(height):
        for x in range(width):
            if (x, y) in ignore_mask:
                continue

            bp = baseline_data[x, y]
            cp = current_data[x, y]

            # Check if any channel differs beyond tolerance
            channel_diff = max(
                abs(bp[0] - cp[0]),
                abs(bp[1] - cp[1]),
                abs(bp[2] - cp[2]),
                abs(bp[3] - cp[3]),
            )

            if channel_diff > pixel_tolerance:
                diff_pixels += 1
                diff_positions.append((x, y))

    comparable_pixels = total_pixels - len(ignore_mask)
    diff_percent = (diff_pixels / comparable_pixels * 100) if comparable_pixels > 0 else 0
    passed = diff_percent <= threshold

    # Generate diff overlay
    diff_path = None
    if diff_output_path and diff_positions:
        diff_path = _generate_diff_overlay(
            current, diff_positions, diff_output_path, highlight_color
        )

    return ComparisonResult(
        baseline_path=baseline_path,
        current_path=current_path,
        diff_path=diff_path,
        diff_percent=round(diff_percent, 4),
        total_pixels=total_pixels,
        diff_pixels=diff_pixels,
        passed=passed,
        threshold=threshold,
        baseline_size=baseline.size,
        current_size=current.size,
    )


def _generate_diff_overlay(current: Image.Image, diff_positions: list[tuple],
                           output_path: str, highlight_color: tuple) -> str:
    """Generate a diff overlay image highlighting changed pixels."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Create overlay
    overlay = current.copy()
    draw = ImageDraw.Draw(overlay, "RGBA")

    # Draw red overlay on changed pixels
    # For performance, batch nearby pixels into rectangles
    for x, y in diff_positions:
        draw.point((x, y), fill=highlight_color)

    # Also create a pure diff image (black background, white diff pixels)
    diff_only = Image.new("RGBA", current.size, (0, 0, 0, 255))
    diff_draw = ImageDraw.Draw(diff_only)
    for x, y in diff_positions:
        diff_draw.point((x, y), fill=(255, 255, 255, 255))

    # Create side-by-side comparison
    width, height = current.size
    combined_width = width * 3  # baseline area | current | diff
    combined = Image.new("RGBA", (combined_width, height), (30, 30, 30, 255))

    # We don't have baseline loaded here, so just show current + overlay + diff
    combined.paste(current, (0, 0))
    combined.paste(overlay, (width, 0))
    combined.paste(diff_only, (width * 2, 0))

    overlay.save(output_path)

    # Also save the combined view
    combined_path = output_path.replace(".png", "_combined.png")
    combined.save(combined_path)

    return output_path
