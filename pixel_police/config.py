"""Configuration for pixel-police: pages, viewports, thresholds."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Viewport:
    name: str
    width: int
    height: int

    @property
    def label(self) -> str:
        return f"{self.name}_{self.width}x{self.height}"


# Default viewports
VIEWPORTS = {
    "desktop": Viewport("desktop", 1920, 1080),
    "tablet": Viewport("tablet", 768, 1024),
    "mobile": Viewport("mobile", 375, 812),
}


@dataclass
class IgnoreRegion:
    """Region to ignore during comparison (for dynamic content)."""
    x: int
    y: int
    width: int
    height: int
    label: str = ""


@dataclass
class PageConfig:
    """Configuration for a single page to capture."""
    path: str
    name: Optional[str] = None
    wait_for: Optional[str] = None  # CSS selector to wait for
    wait_ms: int = 0  # Additional wait time
    ignore_regions: list[IgnoreRegion] = field(default_factory=list)
    full_page: bool = True

    @property
    def safe_name(self) -> str:
        """Generate filesystem-safe name from path."""
        if self.name:
            return self.name.replace(" ", "_").replace("/", "_")
        name = self.path.strip("/").replace("/", "_") or "index"
        return name


@dataclass
class Config:
    """Full pixel-police configuration."""
    base_url: str = "http://localhost:3000"
    pages: list[PageConfig] = field(default_factory=list)
    viewports: list[Viewport] = field(default_factory=list)
    threshold: float = 0.1  # Percentage diff threshold for failure
    baseline_dir: str = ".pixel-police/baselines"
    capture_dir: str = ".pixel-police/captures"
    report_dir: str = ".pixel-police/reports"
    wait_before_capture: int = 500  # ms to wait after page load
    color_scheme: Optional[str] = None  # "light", "dark", or None

    def __post_init__(self):
        if not self.viewports:
            self.viewports = [VIEWPORTS["desktop"]]
        if not self.pages:
            self.pages = [PageConfig(path="/")]


def load_config(config_path: str = ".pixel-police.json") -> Config:
    """Load configuration from JSON file."""
    path = Path(config_path)
    if not path.exists():
        return Config()

    data = json.loads(path.read_text())
    config = Config(
        base_url=data.get("base_url", "http://localhost:3000"),
        threshold=data.get("threshold", 0.1),
        baseline_dir=data.get("baseline_dir", ".pixel-police/baselines"),
        capture_dir=data.get("capture_dir", ".pixel-police/captures"),
        report_dir=data.get("report_dir", ".pixel-police/reports"),
        wait_before_capture=data.get("wait_before_capture", 500),
        color_scheme=data.get("color_scheme"),
    )

    # Parse pages
    for page_data in data.get("pages", []):
        if isinstance(page_data, str):
            config.pages.append(PageConfig(path=page_data))
        elif isinstance(page_data, dict):
            ignore_regions = []
            for region in page_data.get("ignore_regions", []):
                ignore_regions.append(IgnoreRegion(**region))

            config.pages.append(PageConfig(
                path=page_data["path"],
                name=page_data.get("name"),
                wait_for=page_data.get("wait_for"),
                wait_ms=page_data.get("wait_ms", 0),
                ignore_regions=ignore_regions,
                full_page=page_data.get("full_page", True),
            ))

    # Parse viewports
    for vp_data in data.get("viewports", []):
        if isinstance(vp_data, str) and vp_data in VIEWPORTS:
            config.viewports.append(VIEWPORTS[vp_data])
        elif isinstance(vp_data, dict):
            config.viewports.append(Viewport(
                name=vp_data.get("name", "custom"),
                width=vp_data["width"],
                height=vp_data["height"],
            ))

    return config


def save_config(config: Config, config_path: str = ".pixel-police.json"):
    """Save configuration to JSON file."""
    data = {
        "base_url": config.base_url,
        "threshold": config.threshold,
        "baseline_dir": config.baseline_dir,
        "capture_dir": config.capture_dir,
        "report_dir": config.report_dir,
        "wait_before_capture": config.wait_before_capture,
        "pages": [
            {
                "path": p.path,
                "name": p.name,
                "wait_for": p.wait_for,
                "wait_ms": p.wait_ms,
                "full_page": p.full_page,
                "ignore_regions": [
                    {"x": r.x, "y": r.y, "width": r.width,
                     "height": r.height, "label": r.label}
                    for r in p.ignore_regions
                ] if p.ignore_regions else [],
            }
            for p in config.pages
        ],
        "viewports": [
            {"name": v.name, "width": v.width, "height": v.height}
            for v in config.viewports
        ],
    }

    Path(config_path).write_text(json.dumps(data, indent=2), encoding="utf-8")
