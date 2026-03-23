"""Screenshot capturer using Playwright."""

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .config import Config, PageConfig, Viewport


@dataclass
class CaptureResult:
    page_path: str
    page_name: str
    viewport: str
    filepath: str
    timestamp: float
    url: str
    width: int
    height: int
    success: bool
    error: Optional[str] = None


def capture_screenshots(config: Config, output_dir: Optional[str] = None) -> list[CaptureResult]:
    """Capture screenshots for all configured pages and viewports.

    Uses Playwright sync API for reliability.
    """
    from playwright.sync_api import sync_playwright

    out_dir = Path(output_dir or config.capture_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for viewport in config.viewports:
            context = browser.new_context(
                viewport={"width": viewport.width, "height": viewport.height},
                color_scheme=config.color_scheme or "light",
            )
            page = context.new_page()

            for page_config in config.pages:
                url = config.base_url.rstrip("/") + page_config.path
                filename = f"{page_config.safe_name}_{viewport.label}.png"
                filepath = str(out_dir / filename)

                try:
                    # Navigate
                    page.goto(url, wait_until="networkidle", timeout=30000)

                    # Wait for specific element if configured
                    if page_config.wait_for:
                        page.wait_for_selector(page_config.wait_for, timeout=10000)

                    # Additional wait
                    wait_ms = max(config.wait_before_capture, page_config.wait_ms)
                    if wait_ms > 0:
                        page.wait_for_timeout(wait_ms)

                    # Capture
                    page.screenshot(
                        path=filepath,
                        full_page=page_config.full_page,
                    )

                    # Save metadata
                    meta = {
                        "url": url,
                        "viewport": viewport.label,
                        "width": viewport.width,
                        "height": viewport.height,
                        "timestamp": time.time(),
                        "full_page": page_config.full_page,
                        "page_title": page.title(),
                    }
                    meta_path = filepath.replace(".png", ".meta.json")
                    Path(meta_path).write_text(json.dumps(meta, indent=2))

                    results.append(CaptureResult(
                        page_path=page_config.path,
                        page_name=page_config.safe_name,
                        viewport=viewport.label,
                        filepath=filepath,
                        timestamp=time.time(),
                        url=url,
                        width=viewport.width,
                        height=viewport.height,
                        success=True,
                    ))

                except Exception as e:
                    results.append(CaptureResult(
                        page_path=page_config.path,
                        page_name=page_config.safe_name,
                        viewport=viewport.label,
                        filepath=filepath,
                        timestamp=time.time(),
                        url=url,
                        width=viewport.width,
                        height=viewport.height,
                        success=False,
                        error=str(e),
                    ))

            context.close()

        browser.close()

    return results


def capture_single_url(url: str, output_path: str,
                       width: int = 1920, height: int = 1080,
                       full_page: bool = True,
                       wait_ms: int = 500) -> CaptureResult:
    """Capture a single URL screenshot."""
    from playwright.sync_api import sync_playwright

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": width, "height": height},
        )
        page = context.new_page()

        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
            if wait_ms > 0:
                page.wait_for_timeout(wait_ms)

            page.screenshot(path=output_path, full_page=full_page)

            result = CaptureResult(
                page_path=url,
                page_name="single",
                viewport=f"custom_{width}x{height}",
                filepath=output_path,
                timestamp=time.time(),
                url=url,
                width=width,
                height=height,
                success=True,
            )
        except Exception as e:
            result = CaptureResult(
                page_path=url,
                page_name="single",
                viewport=f"custom_{width}x{height}",
                filepath=output_path,
                timestamp=time.time(),
                url=url,
                width=width,
                height=height,
                success=False,
                error=str(e),
            )

        context.close()
        browser.close()

    return result
