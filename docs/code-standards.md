# Code Standards and Structure

**Last Updated**: 2026-02-10
**Application**: Image Resize WebP v1.1.0

## Codebase Structure

### File Organization

```
resize-webp.py              # Main application (600 LOC)
├── Imports (lines 1-14)
├── Constants (lines 16-29)
├── Helper Functions (lines 32-56)
├── Worker Thread (lines 59-200)
├── Main Window UI (lines 203-600)
└── Application Entry (lines 602-606)
```

### Module Breakdown

**Imports Section:**
- PyQt5 widgets, core, GUI components
- PIL (Pillow) for image processing
- Standard library (sys, os, json, traceback, io)

**Constants:**
- `SUPPORTED_EXTS`: Set of supported image extensions
- `FILTER_STR`: File dialog filter string
- `CONFIG_PATH`: Path to configuration JSON
- `WATERMARK_POSITIONS`: UI-friendly position names (9 positions)
- `WM_POS_KEYS`: Internal position keys for config

**Helper Functions:**
- `pil_to_qpixmap()`: Convert PIL Image to Qt QPixmap for preview
- `fmt_size()`: Format byte size to human-readable string
- `load_config()`: Load JSON config with error handling
- `save_config()`: Save JSON config with error handling
- `apply_watermark()`: Apply logo/text watermark to image (pure function)

**Worker Thread Class:**
- `ResizeWorker(QThread)`: Background image processing
  - Constructor: Accept all processing parameters
  - `run()`: Main processing loop with pipeline
  - Signals: `progress`, `finished`, `error`

**Main Window Class:**
- `MainWindow(QMainWindow)`: Primary application UI
  - Constructor: Build UI, load config, connect signals
  - UI methods: `_build_ui()`, `_build_watermark_section()`
  - Event handlers: `_on_input_folder()`, `_on_preview_select()`, etc.
  - Processing: `start_resize()`, `_resize_done()`
  - Config: `_save_wm_config()` for watermark settings

## Coding Conventions

### Naming Standards

**Classes:**
- PascalCase: `MainWindow`, `ResizeWorker`, `ImgInfo`

**Functions/Methods:**
- snake_case: `load_config()`, `apply_watermark()`, `_save_wm_config()`
- Private methods prefixed with `_`: `_build_ui()`, `_on_input_folder()`

**Variables:**
- snake_case: `input_dir`, `output_dir`, `logo_path`
- Instance variables: `self.chk_logo`, `self.logo_path_edit`
- Constants: UPPER_SNAKE_CASE: `CONFIG_PATH`, `SUPPORTED_EXTS`

**UI Widget Naming:**
- Prefix with widget type: `chk_` (checkbox), `combo_` (combobox), `slider_` (slider)
- Examples: `self.chk_logo`, `self.combo_position`, `self.slider_opacity`

### Code Style

**Line Length:**
- Prefer 100 characters max
- Break long import lists, function parameters across multiple lines

**Indentation:**
- 4 spaces (no tabs)
- Consistent indentation for nested structures

**String Quotes:**
- Double quotes for UI strings: `"Bat dau"`, `"Watermark"`
- Single quotes acceptable for internal strings

**Imports:**
- Group by: standard library, third-party, local modules
- Sort alphabetically within groups

### Function Design

**Pure Functions:**
- No side effects, return new values
- Example: `apply_watermark(img, ...)` returns new Image object
- Testable, predictable, reusable

**Helper Functions:**
- Internal helpers prefixed with `_`
- Example: `_calc_anchor()`, `_adjust_opacity()` inside `apply_watermark()`

**Error Handling:**
- Try-except blocks for I/O operations
- User-friendly error messages via `QMessageBox`
- Logging for debugging (print statements acceptable for small app)

**Function Signatures:**
```python
def apply_watermark(
    img: Image.Image,
    logo_img: Image.Image | None,
    logo_size_pct: int,
    text_content: str,
    font_size: int,
    position: str,
    opacity: int,
    padding: int
) -> Image.Image:
    """Apply watermark to image (pure function)."""
```

## Architectural Patterns

### Layered Architecture

**Presentation Layer:**
- `MainWindow` class: UI construction, event handling
- PyQt5 widgets: Buttons, sliders, checkboxes, labels
- Responsibilities: User input, visual feedback, config updates

**Business Logic Layer:**
- `apply_watermark()`: Watermark application logic
- `ResizeWorker.run()`: Image processing pipeline
- Pure functions preferred, clear input/output contracts

**Data Layer:**
- `load_config()` / `save_config()`: JSON persistence
- File I/O for images (PIL.Image.open, .save)
- Config schema validation on load

### Threading Model

**Main Thread:**
- UI rendering and event handling
- Config updates (auto-save on control changes)
- Preview image display

**Worker Thread:**
- `ResizeWorker(QThread)`: All heavy processing
- Signals communicate with main thread (progress, finished, error)
- Logo cached once per batch (performance optimization)

**Thread Safety:**
- Logo loaded as read-only PIL object (safe for multi-threaded access)
- No shared mutable state between threads
- Worker cancellation via flag (future enhancement)

### Image Processing Pipeline

**Order of operations (in `ResizeWorker.run()`):**
1. Load image from disk (`Image.open()`)
2. Apply rembg background removal (if enabled)
3. Auto-crop transparent edges (if enabled)
4. **Apply watermark** (logo and/or text) - NEW in v1.1.0
5. Resize to target dimensions (W, H, or W+H mode)
6. Save as WebP with quality setting

**Critical:** Watermark applied AFTER crop, BEFORE resize
- Ensures watermark positioned relative to final composition
- Avoids watermark being cropped out
- Scales watermark proportionally with final resize

## Configuration Management

### Config File Schema

**Location:** `resize-webp-config.json` (same directory as script)

**Schema v1.1.0:**
```json
{
  "input_dir": "string (absolute path)",
  "output_dir": "string (absolute path)",
  "rembg_model": "u2net_human_seg | u2net",
  "wm_logo_enabled": "boolean",
  "wm_logo_path": "string (absolute path, validated)",
  "wm_logo_size_pct": "integer (5-80)",
  "wm_text_enabled": "boolean",
  "wm_text_content": "string (any UTF-8 text)",
  "wm_font_size": "integer (8-200)",
  "wm_position": "string (WM_POS_KEYS: top-left, center, etc.)",
  "wm_opacity": "integer (1-100)",
  "wm_padding": "integer (0-500)"
}
```

**Auto-save Triggers:**
- Folder selection (input/output)
- Rembg model change
- Any watermark control change (checkbox, slider, spinbox, text input)

**Validation on Load:**
- Logo path existence check (clear if missing)
- Position key validation against `WM_POS_KEYS`
- Numeric ranges enforced by UI controls (spinboxes/sliders restore valid defaults)
- Missing keys: Use hardcoded defaults

### Default Values

```python
DEFAULT_CONFIG = {
    "input_dir": "",
    "output_dir": "",
    "rembg_model": "u2net_human_seg",
    "wm_logo_enabled": False,
    "wm_logo_path": "",
    "wm_logo_size_pct": 15,
    "wm_text_enabled": False,
    "wm_text_content": "",
    "wm_font_size": 24,
    "wm_position": "bottom-right",
    "wm_opacity": 80,
    "wm_padding": 20
}
```

## Error Handling Standards

### User-Facing Errors

**File Not Found:**
```python
if not os.path.exists(logo_path):
    QMessageBox.warning(self, "Loi", f"Logo file not found: {logo_path}")
    return
```

**Invalid Input:**
```python
if not input_dir or not output_dir:
    QMessageBox.warning(self, "Loi", "Please select input and output folders.")
    return
```

**Processing Errors:**
```python
except Exception as e:
    self.error.emit(f"Error processing {fname}: {str(e)}")
```

### Developer-Facing Errors

**Config Corruption:**
```python
try:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)
except:
    return {}  # Silent fallback to defaults
```

**Image Load Errors:**
```python
try:
    img = Image.open(fpath).convert("RGBA")
except Exception as e:
    print(f"[ERROR] Failed to load {fname}: {e}")
    continue  # Skip file, continue batch
```

### Logging Strategy

**Current Approach:**
- Print statements for debugging (acceptable for small app)
- Error messages logged to console
- Future: Consider Python logging module for production

**Log Levels (when using logging module):**
- INFO: Processing start/finish, file counts
- WARNING: Missing logo, invalid paths, skipped files
- ERROR: Critical failures, exceptions

## Security Standards

### Input Validation

**File Paths:**
```python
# Validate against directory traversal
logo_path = os.path.abspath(logo_path)
if ".." in logo_path or not os.path.exists(logo_path):
    return  # Reject suspicious paths
```

**File Types:**
```python
# Whitelist allowed extensions
LOGO_EXTS = {".png", ".webp", ".jpg", ".jpeg"}
if os.path.splitext(logo_path)[1].lower() not in LOGO_EXTS:
    QMessageBox.warning(self, "Loi", "Invalid logo format.")
    return
```

**File Size Limits:**
```python
# Enforce 10MB max for logo files
MAX_LOGO_SIZE = 10 * 1024 * 1024  # 10MB
if os.path.getsize(logo_path) > MAX_LOGO_SIZE:
    QMessageBox.warning(self, "Loi", "Logo file too large (max 10MB).")
    return
```

### Config Security

**Path Sanitization:**
```python
# Sanitize before saving
config["wm_logo_path"] = os.path.abspath(logo_path)
```

**Position Key Validation:**
```python
# Only allow known position keys
if position not in WM_POS_KEYS:
    position = "bottom-right"  # Fallback to default
```

### Thread Safety

**Read-Only Caching:**
```python
# Logo loaded once, never modified
self.logo_img = Image.open(logo_path).convert("RGBA") if logo_path else None
```

**No Shared Mutable State:**
- Worker receives copies of all parameters
- No global variables modified during processing

## Testing Standards

### Unit Tests

**Test File:** `test_watermark_feature.py`

**Coverage Requirements:**
- Position calculation (9 positions)
- Opacity adjustment (edge cases: 1%, 100%)
- Logo resize logic (edge cases: 0%, 100%, logo > image)
- Text rendering with font fallback
- Stacking logic (logo + text at same position)

**Example Test Structure:**
```python
def test_apply_watermark_position_top_left():
    img = Image.new("RGBA", (1000, 1000), (255, 255, 255, 255))
    logo = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
    result = apply_watermark(img, logo, 10, "", 24, "top-left", 100, 20)
    # Assert logo positioned at (20, 20)
```

### Integration Tests

**Manual Test Scenarios:**
1. Enable logo, select file, process 10 images → Verify all have watermark
2. Enable text, process batch → Verify text renders correctly
3. Enable both logo + text at same position → Verify stacking
4. Change opacity to 50% → Verify transparency
5. Restart app → Verify settings restored

### Security Testing

**Validation Tests:**
1. Attempt directory traversal (`../../../etc/passwd`) → Reject
2. Upload 50MB logo → Reject
3. Upload .exe file as logo → Reject
4. Inject special chars in text (`<script>alert(1)</script>`) → Safe rendering

## Performance Guidelines

### Optimization Strategies

**Logo Caching:**
```python
# Load once per batch, not per image
self.logo_img = Image.open(logo_path).convert("RGBA") if logo_path else None
for fpath in image_files:
    # Reuse self.logo_img for all images
    watermarked = apply_watermark(img, self.logo_img, ...)
```

**Lazy Imports:**
```python
# Import ImageDraw/ImageFont only when needed
def apply_watermark(...):
    from PIL import ImageDraw, ImageFont  # Lazy import
```

**Thumbnail Previews:**
```python
# Resize preview images to 400px max
pil_img.thumbnail((max_size, max_size), Image.LANCZOS)
```

### Performance Targets

**Batch Processing:**
- 100 images (1000px width, u2net model): Under 5 minutes
- Logo caching: 1x load per batch (not N× per image)

**Memory Usage:**
- 500 image batch: Under 2GB RAM
- Worker thread: Release images after processing

**UI Responsiveness:**
- No freezes during processing (worker thread)
- Progress bar updates every image (not every pixel)

## Code Quality Metrics

### Maintainability

**Single File Application:**
- Entire app in `resize-webp.py` (600 LOC)
- No external modules (besides dependencies)
- Easy to distribute (single .py file + requirements.txt)

**Function Complexity:**
- Max cyclomatic complexity: 10
- Prefer small, focused functions (10-30 lines)
- Extract helpers for complex logic (`_calc_anchor()`, `_adjust_opacity()`)

**Comments:**
- Inline comments for complex logic
- Docstrings for public functions
- Avoid obvious comments (e.g., `# Set width` before `width = 1000`)

### Code Review Standards

**Review Checklist:**
- [ ] Functions are pure where possible
- [ ] Error handling covers edge cases
- [ ] Security validation for all file paths
- [ ] UI controls connected to auto-save signals
- [ ] No code duplication (DRY principle)
- [ ] Clear variable names (no `x`, `tmp`, `data`)
- [ ] Consistent naming conventions

**Review Score Target:** >90% (see `plans/reports/code-reviewer-260210-1615-watermark-feature.md`)

## Dependency Management

### Required Dependencies

```
PyQt5>=5.15.0
Pillow>=8.0.0
rembg>=2.0.0
```

**Installation:**
```bash
pip install PyQt5 Pillow rembg
```

### Dependency Constraints

**PyQt5:**
- GUI framework
- Stable API, minimal breaking changes
- Cross-platform support

**Pillow:**
- Image processing library
- Used for: Load, resize, crop, watermark, save
- LANCZOS resampling for high quality

**Rembg:**
- Background removal using ML models
- Requires: torch, onnx (auto-installed)
- Models downloaded on first use (~100MB)

## Future Code Standards

### V2.0 Enhancements

**Modular Structure:**
- Split into modules: `ui.py`, `processing.py`, `watermark.py`, `config.py`
- Easier testing and maintenance

**Type Hints:**
- Full type annotations for all functions
- Use `mypy` for static type checking

**Logging:**
- Replace print statements with Python logging module
- Log levels: DEBUG, INFO, WARNING, ERROR
- Rotate log files to prevent disk bloat

**Configuration:**
- Consider YAML/TOML for config (more readable than JSON)
- Schema validation with Pydantic

**Testing:**
- Pytest for unit tests
- Coverage target: >90%
- CI/CD integration (GitHub Actions)

## References

**PyQt5 Documentation:** https://doc.qt.io/qtforpython/
**Pillow Documentation:** https://pillow.readthedocs.io/
**Rembg Documentation:** https://github.com/danielgatis/rembg
**PEP 8 Style Guide:** https://www.python.org/dev/peps/pep-0008/
