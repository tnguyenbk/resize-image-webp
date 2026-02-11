# Codebase Summary

**Last Updated**: 2026-02-11
**Version**: 1.2.0 (UI Redesign & Enhanced Watermarks)

## Overview

Image Resize WebP is a PyQt5-based desktop application for batch processing images with the following capabilities:
- Background removal using rembg
- Intelligent auto-cropping (remove transparent edges)
- Image resizing with configurable dimensions
- WebP conversion with quality settings
- **3-column UI layout** (NEW in v1.2.0)
- **Independent logo and text watermarking** with rotation and tiling (ENHANCED in v1.2.0)
- Configuration persistence with validation

## Project Structure

```
Resize image webp/
├── resize-webp.py              # Main application (976 LOC)
├── resize-webp-config.json     # User settings persistence
├── test_watermark_feature.py   # Unit tests for watermark
├── test_ui_watermark.py        # UI integration tests
├── validate_code_structure.py  # Code quality checks
├── plans/                      # Development plans and reports
│   ├── 260210-1600-logo-watermark-feature/
│   │   └── (4 phase files)
│   ├── 260210-1650-ui-redesign-watermark-enhancements/
│   │   ├── plan.md
│   │   └── (7 phase files)
│   └── reports/
│       ├── brainstorm-*.md
│       ├── tester-*.md
│       ├── code-reviewer-*.md
│       ├── scout-*.md
│       └── project-manager-*.md
└── docs/                       # Documentation
    ├── codebase-summary.md     # This file
    ├── project-overview-pdr.md # Project overview and requirements
    ├── code-standards.md       # Code structure and standards
    └── system-architecture.md  # System architecture
```

## Core Components

### Main Application (`resize-webp.py`)

**Key Classes:**
- `MainWindow`: Primary UI with 3-column layout (976 LOC total)
- `ResizeWorker(QThread)`: Background image processing worker
- `ImgInfo`: Data class for image metadata (if present)

**Key Functions:**
- `apply_watermark()`: Pure function for applying logo/text watermarks with independent controls
- `load_config()` / `save_config()`: JSON configuration management
- `safe_config_int()` / `safe_config_str()`: Config validation helpers (NEW)
- `pil_to_qpixmap()`: PIL Image to Qt pixmap conversion
- `fmt_size()`: Human-readable file size formatting
- `calc_resize()`: Calculate resize dimensions

### Image Processing Pipeline

**Flow:**
1. Load image from disk
2. Apply rembg background removal (optional)
3. Auto-crop transparent edges (optional)
4. **Apply watermark** (logo and/or text with independent positioning) - ENHANCED
5. Resize to target dimensions
6. Save as WebP with quality settings

**Processing occurs in**: `ResizeWorker.run()` method

### Watermark System (v1.2.0 - Enhanced)

**Architecture:**
- **UI Layer**: 3-column layout with dedicated watermark column
- **Logo Section**: Independent controls (position, opacity, size, padding)
- **Text Section**: Independent controls (position, opacity, font, padding, rotation, tiling)
- **Logic Layer**: `apply_watermark()` pure function with 12 parameters
- **Worker Integration**: Logo cached once per batch, applied per image
- **Persistence**: 17 config keys with validation (was 12 in v1.1.0)

**Features:**

**Logo Watermarking:**
- Configurable size (5-80% of image width)
- Independent position selection (9-position grid)
- Independent opacity control (1-100%)
- Independent edge padding (0-500px)
- Supported formats: PNG, WEBP, JPG, JPEG
- File size limit: 10MB

**Text Watermarking:**
- Custom text input
- Font size control (8-200px)
- Independent position selection (9-position grid)
- Independent opacity control (1-100%)
- Independent edge padding (0-500px)
- **Text rotation** (0-360 degrees, clockwise) - NEW
- **Tiling mode** (repeat across entire image) - NEW
- Font fallback chain: arial.ttf → DejaVuSans.ttf → default

**Key Improvements from v1.1.0:**
- Logo and text can be placed at different positions (no stacking)
- Separate opacity and padding for logo and text
- Text rotation feature (0-360 degrees)
- Text tiling mode with 2x spacing diagonal pattern
- No overlap or stacking behavior

**Security Features:**
- Path validation (no directory traversal)
- Logo file size limit (10MB)
- Input image file size limit (100MB max) - NEW
- Config type and range validation - NEW
- Worker restart guards - NEW

**Configuration Keys (v1.2.0):**
```json
{
  "wm_logo_enabled": bool,
  "wm_logo_path": string,
  "logo_position": string (9 positions),
  "logo_opacity": int (1-100),
  "logo_size_pct": int (5-80),
  "logo_padding": int (0-500),

  "wm_text_enabled": bool,
  "wm_text_content": string,
  "wm_text_position": string (9 positions),
  "wm_text_opacity": int (1-100),
  "wm_font_size": int (8-200),
  "wm_text_padding": int (0-500),
  "wm_rotation": int (0-360),
  "wm_tiling": bool
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

**Schema v1.2.0:**
```json
{
  "output_dir": "last selected output folder",
  "rembg_model": "u2net_human_seg | u2net",

  "wm_logo_enabled": false,
  "wm_logo_path": "",
  "logo_position": "bottom-right",
  "logo_opacity": 50,
  "logo_size_pct": 20,
  "logo_padding": 10,

  "wm_text_enabled": false,
  "wm_text_content": "",
  "wm_text_position": "bottom-right",
  "wm_text_opacity": 80,
  "wm_font_size": 24,
  "wm_text_padding": 10,
  "wm_rotation": 0,
  "wm_tiling": false
}
```

**Auto-save triggers**: All UI control changes persist immediately
**Validation**: Type and range validation with `safe_config_int()` and `safe_config_str()`

## Code Metrics

**Total Lines**: ~976 LOC (resize-webp.py)
**Functions**: 10+ (including helpers)
**Classes**: 2 (MainWindow, ResizeWorker)
**UI Widgets**: ~50+ (including watermark controls)
**Config Keys**: 17 (watermark-related)
**External Dependencies**: 3

## Recent Changes (v1.2.0)

**Added:**
- 3-column UI layout (file list | preview/basic | watermarks)
- Independent logo controls in dedicated section
- Independent text watermark controls in dedicated section
- Text rotation feature (0-360 degrees)
- Text tiling mode (diagonal pattern with 2x spacing)
- Config validation helpers (`safe_config_int`, `safe_config_str`)
- File size limit for input images (100MB max)
- Worker restart guard to prevent memory leaks
- Minimum window size: 1100x600

**Modified:**
- `MainWindow.__init__`: Restructured to 3-column layout
- `apply_watermark()`: Added independent position/opacity/padding for logo and text
- `apply_watermark()`: Added text rotation and tiling parameters
- `ResizeWorker.__init__`: Extended to 12 watermark parameters
- `ResizeWorker.run()`: Updated watermark integration with new parameters
- `save_config()` / `load_config()`: Added validation for security
- Config schema: Extended to 17 keys with separated logo/text settings

**Files Modified**: 1 (resize-webp.py: +376 lines from v1.1.0)

## Testing

**Test Files:**
- `test_watermark_feature.py`: Unit tests for watermark functionality (269 LOC)
- `test_ui_watermark.py`: UI integration tests (533 LOC)
- `validate_code_structure.py`: Code quality validation

**Coverage Areas:**
- Watermark position calculation (9 positions)
- Independent logo and text positioning
- Opacity adjustment
- Logo resize logic
- Text rendering with font fallback
- Text rotation (0, 45, 90, 180, 270, 360 degrees)
- Text tiling with diagonal pattern
- Config persistence (save/load cycle)
- Config validation (type and range checks)
- Security validation (path traversal, file size limits)

**Test Results (v1.2.0):**
- 64/64 assertions passed (100% pass rate)
- No syntax errors
- All edge cases covered in scout analysis

## Security Considerations

**File Handling:**
- Logo paths validated against directory traversal attacks
- Logo file size limit: 10MB maximum
- Input image file size limit: 100MB maximum (NEW)
- File type whitelist: PNG, WEBP, JPG, JPEG only
- Path existence checks with graceful fallbacks

**Config Security:**
- Type validation prevents injection attacks (NEW)
- Range validation prevents invalid widget states (NEW)
- String validation with whitelists for position keys (NEW)
- Safe defaults for corrupted or missing values

**Worker Thread Safety:**
- Logo cached as read-only PIL object (thread-safe)
- Worker restart guard prevents memory leaks (NEW)
- Stop flag for graceful shutdown
- Error isolation: Image load failures don't crash worker

**Input Sanitization:**
- File paths sanitized before saving to config
- Position keys validated against known list (WM_POS_KEYS)
- Numeric ranges enforced by validation helpers
- Boolean type checks for flags

## Known Limitations

**Performance:**
- Large logo files (5-10MB) may slow processing
- Font rendering performance varies with text length
- Tiling adds ~30% overhead vs. single placement (acceptable)

**Font Support:**
- Non-ASCII characters depend on available system fonts
- Fallback chain: arial.ttf → DejaVuSans.ttf → default bitmap (ignores size)

**UI:**
- Minimum window size 1100x600 may exclude 1024x768 users
- No scrollable areas (fixed layout)
- Column 3 may require vertical space on small screens

**File Size:**
- Single-file architecture at 976 LOC (approaching modularization threshold)

## Future Enhancements (Roadmap)

**V2.0 Planned:**
- Config save debouncing to prevent write race conditions
- PIL image cleanup with context managers
- Multiple watermark layers
- Logo rotation support
- Text color picker (currently white only)
- Watermark templates (save/load presets)
- Drag-and-drop logo positioning with preview
- Advanced text effects (outline, shadow, gradient)
- Scrollable UI for 1024x768 support
- Better font fallback with explicit system paths

## Maintenance Notes

**Code Quality:**
- Pure functions preferred (e.g., `apply_watermark()`)
- Clear separation: UI layer, logic layer, worker layer
- Error handling with user-friendly messages
- Comprehensive inline comments for complex logic
- Config validation helpers prevent crashes

**Documentation:**
- All phases documented in `plans/` directory
- Test reports in `plans/reports/`
- Code review findings in `plans/reports/code-reviewer-*.md`
- Scout analysis in `plans/reports/scout-*.md`

**Quality Score**: 7.5/10 (Good, per code reviewer analysis)
- Strengths: Clean architecture, comprehensive testing, backward-compatible config
- Weaknesses: Config save debouncing needed, PIL image cleanup missing

## Version History Summary

### v1.2.0 (2026-02-11) - UI Redesign & Enhanced Watermarks
- 3-column layout
- Independent logo/text controls
- Text rotation and tiling
- Config validation
- Security enhancements

### v1.1.0 (2026-02-10) - Watermark Feature
- Logo and text watermarking
- 9-position grid
- Config persistence

### v1.0.0 (Initial) - Core Features
- Background removal
- Auto-crop
- Resizing
- WebP conversion
