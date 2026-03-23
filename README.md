# pixel-police

**Visual regression testing: screenshot comparison with before/after diff.**

Catch unintended visual changes before they ship. Capture screenshots, set baselines, and compare with pixel-level precision.

```
pip install pixel-police
playwright install chromium
pixel-police capture http://localhost:3000 --pages /,/about,/login
```

> Pixel-level diff. HTML report with swipe slider. CI-friendly exit codes.

## Why pixel-police?

- **Pixel-perfect diffs** - Compare screenshots pixel-by-pixel with configurable tolerance
- **Multi-viewport** - Test desktop, tablet, and mobile in one command
- **HTML report** - Side-by-side comparison with swipe slider and pass/fail badges
- **Baseline management** - Approve screenshots as baselines, compare against them
- **Ignore regions** - Skip dynamic content areas (timestamps, ads, avatars)
- **CI-ready** - Non-zero exit on visual regressions, JSON summary output

## Quick Start

```bash
# 1. Capture initial screenshots
pixel-police capture http://localhost:3000 --pages /,/about,/pricing

# 2. Approve as baselines
pixel-police approve

# 3. Make changes to your app...

# 4. Capture again
pixel-police capture http://localhost:3000 --pages /,/about,/pricing

# 5. Compare against baselines
pixel-police compare

# 6. If changes are intentional, approve new baselines
pixel-police approve
```

## Multi-Viewport Testing

```bash
# All three viewports
pixel-police capture http://localhost:3000 --viewports desktop,tablet,mobile

# Default viewports:
# desktop: 1920x1080
# tablet:  768x1024
# mobile:  375x812
```

## Configuration

Create `.pixel-police.json` for persistent config:

```bash
pixel-police init http://localhost:3000 --pages /,/about --threshold 0.5
```

```json
{
  "base_url": "http://localhost:3000",
  "threshold": 0.1,
  "pages": [
    {"path": "/", "name": "home", "wait_for": "#main-content"},
    {"path": "/about", "name": "about"},
    {
      "path": "/dashboard",
      "wait_ms": 2000,
      "ignore_regions": [
        {"x": 0, "y": 0, "width": 200, "height": 50, "label": "timestamp"}
      ]
    }
  ],
  "viewports": [
    {"name": "desktop", "width": 1920, "height": 1080},
    {"name": "mobile", "width": 375, "height": 812}
  ]
}
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `pixel-police capture <url>` | Capture screenshots |
| `pixel-police compare` | Compare captures against baselines |
| `pixel-police approve` | Approve captures as new baselines |
| `pixel-police report` | Generate HTML comparison report |
| `pixel-police init <url>` | Create configuration file |

## HTML Report

The report includes:
- Summary with pass/fail/error counts
- Each comparison as a card with baseline, current, and diff images
- Interactive swipe slider to compare baseline vs current
- Color-coded: green (pass), red (fail), yellow (error)

## CI Integration

```yaml
- name: Visual regression test
  run: |
    pixel-police capture http://localhost:3000 --pages /,/about,/login
    pixel-police compare --threshold 0.5
```

`pixel-police compare` exits with code 1 when any comparison fails.

## Ignore Regions

Skip dynamic areas like timestamps, ads, or user avatars:

```json
{
  "pages": [{
    "path": "/dashboard",
    "ignore_regions": [
      {"x": 10, "y": 10, "width": 200, "height": 30, "label": "clock"},
      {"x": 800, "y": 0, "width": 120, "height": 40, "label": "avatar"}
    ]
  }]
}
```

## License

MIT
