---
title: "Logo & Watermark Feature"
description: "Add logo image and text watermark support with 9-position placement, opacity, and config persistence"
status: completed
priority: P1
effort: 3h
branch: n/a
tags: [feature, watermark, logo, pyqt5, pillow]
created: 2026-02-10
completed: 2026-02-10
---

# Logo & Watermark Feature

## Context
- Brainstorm report: `plans/reports/brainstorm-260210-1545-logo-watermark-feature.md`
- Main file: `resize-webp.py` (478 lines, single-file PyQt5 app)
- Config: `resize-webp-config.json` (JSON persistence, already has `load_config`/`save_config`)

## Processing Order
```
Load -> Rembg -> Crop -> WATERMARK -> Resize -> Save
```

## Phases

| # | Phase | Status | Effort | File |
|---|-------|--------|--------|------|
| 1 | UI Components | **completed** | 1h | `phase-01-ui-components.md` |
| 2 | Helper Function `apply_watermark()` | **completed** | 1h | `phase-02-helper-function.md` |
| 3 | Worker Integration + Logo Cache | **completed** | 30m | `phase-03-worker-integration.md` |
| 4 | Config Persistence | **completed** | 30m | `phase-04-config-persistence.md` |

## Key Dependencies
- PIL/Pillow (already imported)
- No new pip packages required
- Font: `ImageFont.truetype()` with system font fallback

## Architecture Decision
- Single file approach maintained (no module split needed, total ~600 lines after feature)
- `apply_watermark()` as standalone function (like existing `calc_resize()`)
- Logo cached as PIL object in worker `__init__` for batch performance

## Security Enhancements Applied
- **Path Validation**: Logo file paths validated against directory traversal attacks
- **File Size Limits**: 10MB max logo file size enforced
- **Error Handling**: Enhanced config save error handling with user feedback
- **Worker Cancellation**: Proper thread cancellation support to prevent resource leaks
- **Input Sanitization**: File extension validation for logo files (PNG, WEBP, JPG, JPEG only)

## Final Status
**ALL PHASES COMPLETED** - Feature fully implemented with security hardening and config persistence.
