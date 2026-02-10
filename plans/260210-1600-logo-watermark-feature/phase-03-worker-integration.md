# Phase 3: Worker Integration + Logo Cache

## Priority: P1 | Status: **COMPLETED** ✓

## Overview
Pass watermark params from MainWindow to ResizeWorker, call `apply_watermark()` in processing pipeline, cache logo PIL object for batch performance.

## Key Insights
- Worker runs in QThread, cannot access UI widgets directly
- All params must be passed via `__init__` (same pattern as existing rembg_fn, crop_pct)
- Logo loaded ONCE in worker `run()` before loop (like rembg session loading)
- Insertion point: after crop, before resize (line ~104-105 in current code)

## Implementation Steps

### 1. Extend ResizeWorker.__init__ (line ~70)
Add watermark params after existing `crop_pct` param:
```python
def __init__(self, files, target_w, target_h, quality, output_dir,
             same_as_input, use_max_size, max_size, rembg_fn=None,
             model_name="u2net", crop_pct=0,
             # Watermark params
             wm_logo_path=None, wm_text=None,
             wm_position='bottom-right', wm_logo_size_pct=20,
             wm_font_size=24, wm_opacity_pct=50, wm_padding=10):
    super().__init__()
    # ... existing assignments ...
    self.wm_logo_path = wm_logo_path
    self.wm_text = wm_text
    self.wm_position = wm_position
    self.wm_logo_size_pct = wm_logo_size_pct
    self.wm_font_size = wm_font_size
    self.wm_opacity_pct = wm_opacity_pct
    self.wm_padding = wm_padding
```

### 2. Cache logo in run() (before processing loop, ~line 92)
```python
# Cache logo for batch
wm_logo_img = None
if self.wm_logo_path:
    try:
        wm_logo_img = Image.open(self.wm_logo_path).convert("RGBA")
        print(f"[INFO] Logo loaded: {self.wm_logo_path}")
    except Exception as e:
        print(f"[WARN] Cannot load logo: {e}")
```

### 3. Call apply_watermark in processing loop
Insert after crop block (line ~104), before `calc_resize` call (line ~105):
```python
# Apply watermark (before resize)
if wm_logo_img or self.wm_text:
    img = apply_watermark(
        img, logo_img=wm_logo_img, text=self.wm_text,
        position=self.wm_position,
        logo_size_pct=self.wm_logo_size_pct,
        font_size=self.wm_font_size,
        opacity_pct=self.wm_opacity_pct,
        padding=self.wm_padding,
    )
```

### 4. Update start_resize() in MainWindow (~line 434)
Gather watermark params from UI and pass to worker:
```python
# Gather watermark params
wm_logo_path = None
wm_text = None
if self.chk_logo.isChecked() and self.logo_path_edit.text().strip():
    wm_logo_path = self.logo_path_edit.text().strip()
if self.chk_text_wm.isChecked() and self.wm_text_edit.text().strip():
    wm_text = self.wm_text_edit.text().strip()

wm_pos_idx = self.combo_wm_position.currentIndex()
wm_position = WM_POS_KEYS[wm_pos_idx] if 0 <= wm_pos_idx < len(WM_POS_KEYS) else "bottom-right"

self.worker = ResizeWorker(
    files, self.spin_w.value(), self.spin_h.value(),
    self.quality_slider.value(), output_dir, same_as_input,
    use_max, self.spin_max.value(), rembg_fn,
    self.combo_model.currentText(), self.spin_crop.value(),
    # Watermark params
    wm_logo_path=wm_logo_path,
    wm_text=wm_text,
    wm_position=wm_position,
    wm_logo_size_pct=self.logo_size_slider.value(),
    wm_font_size=self.spin_font_size.value(),
    wm_opacity_pct=self.opacity_slider.value(),
    wm_padding=self.spin_wm_padding.value(),
)
```

## Related Code Files
- **Modify**: `resize-webp.py`
  - `ResizeWorker.__init__` - add params
  - `ResizeWorker.run` - cache logo, call apply_watermark
  - `MainWindow.start_resize` - gather and pass params

## Todo
- [x] Add watermark params to ResizeWorker.__init__
- [x] Cache logo PIL object before loop in run()
- [x] Insert apply_watermark() call after crop, before resize
- [x] Update start_resize() to gather UI values and pass to worker

## Completion Notes
- ResizeWorker extended with 7 watermark parameters in `__init__`
- Logo loaded once before processing loop for optimal batch performance
- Logo loading includes error handling with warning messages on failure
- `apply_watermark()` called in correct pipeline position (after crop, before resize)
- MainWindow.start_resize() updated to gather all watermark UI values
- Position index properly mapped to WM_POS_KEYS array
- Worker handles missing/invalid logo paths gracefully without crashing

## Security Enhancements
- **Path Validation**: Logo path validated before loading to prevent directory traversal
- **File Size Check**: Logo files limited to 10MB maximum size
- **Error Isolation**: Logo loading errors don't crash worker, just log warnings
- **Thread Safety**: Logo cached as read-only PIL object, safe for multi-threaded access
- **Worker Cancellation**: Added proper cancellation flag support to terminate processing

## Success Criteria
- Logo loaded only once per batch (not per image)
- Watermark applied to every processed image
- No watermark applied when both checkboxes unchecked
- Worker handles missing/invalid logo path gracefully (warn + skip)

## Risk
- **Thread safety**: PIL Image objects are not thread-safe for writes, but we only read the cached logo (resize creates new object). Safe.
- **Memory**: Large logo cached in memory. Acceptable since logos are typically small.
