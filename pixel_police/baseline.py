"""Baseline manager: store and manage approved screenshots."""

import json
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .config import Config
from .comparator import compare_images, ComparisonResult, IgnoreBox


@dataclass
class BaselineInfo:
    filepath: str
    page_name: str
    viewport: str
    approved_at: float
    url: str = ""

    @property
    def approved_date(self) -> str:
        import datetime
        return datetime.datetime.fromtimestamp(self.approved_at).isoformat()


class BaselineManager:
    """Manage baseline screenshots for comparison."""

    def __init__(self, config: Config):
        self.config = config
        self.baseline_dir = Path(config.baseline_dir)
        self.baseline_dir.mkdir(parents=True, exist_ok=True)

    def _baseline_path(self, page_name: str, viewport: str) -> str:
        """Get baseline file path for a page/viewport combo."""
        return str(self.baseline_dir / f"{page_name}_{viewport}.png")

    def _meta_path(self, page_name: str, viewport: str) -> str:
        """Get metadata file path."""
        return str(self.baseline_dir / f"{page_name}_{viewport}.baseline.json")

    def has_baseline(self, page_name: str, viewport: str) -> bool:
        """Check if a baseline exists for this page/viewport."""
        return Path(self._baseline_path(page_name, viewport)).exists()

    def get_baseline_info(self, page_name: str, viewport: str) -> Optional[BaselineInfo]:
        """Get info about an existing baseline."""
        meta_path = self._meta_path(page_name, viewport)
        if not Path(meta_path).exists():
            return None

        data = json.loads(Path(meta_path).read_text())
        return BaselineInfo(
            filepath=self._baseline_path(page_name, viewport),
            page_name=data.get("page_name", page_name),
            viewport=data.get("viewport", viewport),
            approved_at=data.get("approved_at", 0),
            url=data.get("url", ""),
        )

    def approve(self, capture_path: str, page_name: str, viewport: str,
                url: str = "") -> str:
        """Approve a capture as the new baseline."""
        baseline_path = self._baseline_path(page_name, viewport)
        shutil.copy2(capture_path, baseline_path)

        # Save metadata
        meta = {
            "page_name": page_name,
            "viewport": viewport,
            "approved_at": time.time(),
            "source": capture_path,
            "url": url,
        }
        meta_path = self._meta_path(page_name, viewport)
        Path(meta_path).write_text(json.dumps(meta, indent=2))

        return baseline_path

    def approve_all(self, capture_dir: str) -> list[str]:
        """Approve all captures in a directory as new baselines."""
        approved = []
        capture_path = Path(capture_dir)

        for png_file in capture_path.glob("*.png"):
            # Parse page name and viewport from filename
            # Format: {page_name}_{viewport_name}_{WxH}.png
            stem = png_file.stem
            parts = stem.rsplit("_", 2)

            if len(parts) >= 3:
                page_name = parts[0]
                viewport = f"{parts[1]}_{parts[2]}"
            elif len(parts) == 2:
                page_name = parts[0]
                viewport = parts[1]
            else:
                page_name = stem
                viewport = "default"

            # Load metadata if available
            meta_file = png_file.with_suffix("").with_suffix(".meta.json")
            url = ""
            if meta_file.exists():
                meta = json.loads(meta_file.read_text())
                url = meta.get("url", "")

            baseline_path = self.approve(str(png_file), page_name, viewport, url)
            approved.append(baseline_path)

        return approved

    def compare_all(self, capture_dir: str,
                    threshold: Optional[float] = None) -> list[ComparisonResult]:
        """Compare all captures against their baselines."""
        th = threshold if threshold is not None else self.config.threshold
        capture_path = Path(capture_dir)
        results = []

        for png_file in sorted(capture_path.glob("*.png")):
            if ".meta." in png_file.name:
                continue

            stem = png_file.stem
            parts = stem.rsplit("_", 2)

            if len(parts) >= 3:
                page_name = parts[0]
                viewport = f"{parts[1]}_{parts[2]}"
            elif len(parts) == 2:
                page_name = parts[0]
                viewport = parts[1]
            else:
                page_name = stem
                viewport = "default"

            baseline_path = self._baseline_path(page_name, viewport)

            # Build ignore regions from config
            ignore_boxes = []
            for page_cfg in self.config.pages:
                if page_cfg.safe_name == page_name:
                    for region in page_cfg.ignore_regions:
                        ignore_boxes.append(IgnoreBox(
                            x=region.x, y=region.y,
                            width=region.width, height=region.height,
                        ))

            diff_dir = Path(self.config.report_dir) / "diffs"
            diff_dir.mkdir(parents=True, exist_ok=True)
            diff_path = str(diff_dir / f"{stem}_diff.png")

            result = compare_images(
                baseline_path=baseline_path,
                current_path=str(png_file),
                diff_output_path=diff_path,
                threshold=th,
                ignore_regions=ignore_boxes if ignore_boxes else None,
            )
            results.append(result)

        return results

    def list_baselines(self) -> list[BaselineInfo]:
        """List all existing baselines."""
        baselines = []
        for meta_file in self.baseline_dir.glob("*.baseline.json"):
            data = json.loads(meta_file.read_text())
            png_file = meta_file.with_suffix("").with_suffix(".png")
            baselines.append(BaselineInfo(
                filepath=str(png_file),
                page_name=data.get("page_name", ""),
                viewport=data.get("viewport", ""),
                approved_at=data.get("approved_at", 0),
                url=data.get("url", ""),
            ))
        return baselines

    def clear(self) -> int:
        """Remove all baselines."""
        count = 0
        for f in self.baseline_dir.glob("*"):
            f.unlink()
            count += 1
        return count
