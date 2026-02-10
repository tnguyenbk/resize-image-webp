# Codebase Summary

**Last Updated**: 2026-02-10
**Version**: 1.1.0 (Watermark Feature)

## Overview

Image Resize WebP is a PyQt5-based desktop application for batch processing images with the following capabilities:
- Background removal using rembg
- Intelligent auto-cropping (remove transparent edges)
- Image resizing with configurable dimensions
- WebP conversion with quality settings
- **Logo and text watermarking** (NEW in v1.1.0)
- Configuration persistence

## Project Structure

```
Resize image webp/
├── resize-webp.py              # Main application (600 LOC)
├── resize-webp-config.json     # User settings persistence
├── test_watermark_feature.py   # Unit tests for watermark
├── validate_code_structure.py  # Code quality checks
├── plans/                      # Development plans and reports
│   ├── 260210-1600-logo-watermark-feature/
│   │   ├── plan.md
│   │   ├── phase-01-ui-components.md
│   │   ├── phase-02-helper-function.md
│   │   ├── phase-03-worker-integration.md
│   │   └── phase-04-config-persistence.md
│   └── reports/
│       ├── brainstorm-260210-1545-logo-watermark-feature.md
│       ├── tester-260210-1610-watermark-feature-qa.md
│       ├── code-reviewer-260210-1615-watermark-feature.md
│       └── project-manager-260210-1621-logo-watermark-completion.md
└── docs/                       # Documentation
    ├── codebase-summary.md     # This file
    ├── project-overview-pdr.md # Project overview and requirements
    ├── code-standards.md       # Code structure and standards
    └── system-architecture.md  # System architecture
```

## Core Components

### Main Application (`resize-webp.py`)

**Key Classes:**
- `MainWindow`: Primary UI and event handling
- `ResizeWorker(QThread)`: Background image processing worker
- `ImgInfo`: Data class for image metadata

**Key Functions:**
- `apply_watermark()`: Pure function for applying logo/text watermarks
- `load_config()` / `save_config()`: JSON configuration management
- `pil_to_qpixmap()`: PIL Image to Qt pixmap conversion
- `fmt_size()`: Human-readable file size formatting

### Image Processing Pipeline

**Flow:**
1. Load image from disk
2. Apply rembg background removal (optional)
3. Auto-crop transparent edges (optional)
4. **Apply watermark** (logo and/or text) - NEW
5. Resize to target dimensions
6. Save as WebP with quality settings

**Processing occurs in**: `ResizeWorker.run()` method

### Watermark System (v1.1.0)

**Architecture:**
- **UI Layer**: Watermark controls in right panel QGroupBox
- **Logic Layer**: `apply_watermark()` pure function
- **Worker Integration**: Logo cached once per batch, applied per image
- **Persistence**: 9 watermark settings saved to JSON config

**Features:**
- Logo watermarking (PNG, WEBP, JPG, JPEG)
  - Configurable size (5-80% of image width)
  - Position selection (9-position grid)
  - Opacity control (1-100%)
  - Edge padding (0-500px)
- Text watermarking
  - Custom text input
  - Font size control (8-200px)
  - Same position/opacity/padding as logo
  - Font fallback chain: arial.ttf → DejaVuSans.ttf → default
- Stacking logic: Logo + text at same position stack vertically (logo on top, 5px gap)
- Security: Path validation, 10MB file size limit, worker cancellation support

**Configuration Keys:**
```json
{
  "wm_logo_enabled": bool,
  "wm_logo_path": string,
  "wm_logo_size_pct": int (5-80),
  "wm_text_enabled": bool,
  "wm_text_content": string,
  "wm_font_size": int (8-200),
  "wm_position": string (e.g., "bottom-right"),
  "wm_opacity": int (1-100),
  "wm_padding": int (0-500)
}
```

## Dependencies

**Core:**
- `PyQt5`: GUI framework
- `Pillow (PIL)`: Image processing
- `rembg`: Background removal ML model

**Python Version**: 3.7+

## Configuration

**File**: `resize-webp-config.json`

**Schema:**
```json
{
  "input_dir": "last selected input folder",
  "output_dir": "last selected output folder",
  "rembg_model": "u2net_human_seg | u2net",
  "wm_logo_enabled": false,
  "wm_logo_path": "",
  "wm_logo_size_pct": 15,
  "wm_text_enabled": false,
  "wm_text_content": "",
  "wm_font_size": 24,
  "wm_position": "bottom-right",
  "wm_opacity": 80,
  "wm_padding": 20
}
```

**Auto-save triggers**: All UI control changes persist immediately

## Code Metrics

**Total Lines**: ~600 LOC (resize-webp.py)
**Functions**: 8 (including helpers)
**Classes**: 3
**UI Widgets**: ~40 (including 16 watermark controls)
**Config Keys**: 12
**External Dependencies**: 3

## Recent Changes (v1.1.0)

**Added:**
- Watermark UI controls (16 widgets)
- `apply_watermark()` function with position calculation logic
- Logo caching in worker for batch performance
- 9 watermark config keys with auto-save
- Security hardening: file validation, size limits, path sanitization

**Modified:**
- `ResizeWorker.__init__`: Added 7 watermark parameters
- `ResizeWorker.run()`: Integrated watermark step after crop
- `MainWindow.__init__`: Added watermark UI section, config loading
- `MainWindow.start_resize()`: Gather and pass watermark settings to worker
- `save_config()`: Extended to persist watermark settings

**Files Modified**: 1 (resize-webp.py: +122 lines)

## Testing

**Test Files:**
- `test_watermark_feature.py`: Unit tests for watermark functionality
- `validate_code_structure.py`: Code quality validation

**Coverage Areas:**
- Watermark position calculation (9 positions)
- Opacity adjustment
- Logo resize logic
- Text rendering with font fallback
- Stacking logic (logo + text)
- Config persistence (save/load cycle)
- Security validation (path traversal, file size limits)

## Security Considerations

**File Handling:**
- Logo paths validated against directory traversal attacks
- File size limit: 10MB max for logo files
- File type whitelist: PNG, WEBP, JPG, JPEG only
- Path existence checks with graceful fallbacks

**Worker Thread Safety:**
- Logo cached as read-only PIL object (thread-safe)
- Worker cancellation flag support
- Error isolation: Logo load failures don't crash worker

**Input Sanitization:**
- File paths sanitized before saving to config
- Position keys validated against known list
- Numeric ranges enforced by UI controls

## Known Limitations

**Performance:**
- Large logo files (5-10MB) may slow processing
- Font rendering performance varies with text length

**Font Support:**
- Non-ASCII characters depend on available system fonts
- Fallback chain: arial.ttf → DejaVuSans.ttf → default

**UI:**
- Right panel may require scrolling on small screens (800px height minimum)

## Future Enhancements (Roadmap)

**V2.0 Planned:**
- Multiple watermark layers
- Logo rotation support
- Text color picker (currently white only)
- Watermark templates (save/load presets)
- Drag-and-drop logo positioning with preview
- Advanced text effects (outline, shadow, gradient)

## Maintenance Notes

**Code Quality:**
- Pure functions preferred (e.g., `apply_watermark()`)
- Clear separation: UI layer, logic layer, worker layer
- Error handling with user-friendly messages
- Comprehensive inline comments for complex logic

**Documentation:**
- All phases documented in `plans/260210-1600-logo-watermark-feature/`
- Test reports in `plans/reports/`
- Code review findings in `plans/reports/code-reviewer-260210-1615-watermark-feature.md`
