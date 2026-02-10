# Phase 1: UI Components

## Priority: P1 | Status: **COMPLETED** ✓

## Overview
Add watermark UI controls to right panel, between rembg section and progress bar (line ~288-291 in `resize-webp.py`).

## Key Insights
- Follow existing UI patterns: `QGroupBox` + layout (same as "Folder output", "Kich thuoc" groups)
- Enable/disable child controls based on checkbox state (same pattern as `chk_rembg` -> `combo_model`)
- All new widgets need `self.*` references for later value access in `start_resize()`

## UI Layout
```
QGroupBox("Watermark")
├─ QCheckBox("Logo anh")               → self.chk_logo
│  ├─ QHBoxLayout
│  │  ├─ QLineEdit (readonly)          → self.logo_path_edit
│  │  ├─ QPushButton("Chon...")        → triggers file dialog
│  │  └─ QPushButton("Clear")          → clears path
│  └─ QHBoxLayout
│     ├─ QLabel("Size:")
│     ├─ QSlider(Horizontal, 5-80)     → self.logo_size_slider
│     └─ QLabel("20%")                 → self.logo_size_label
│
├─ QCheckBox("Text watermark")         → self.chk_text_wm
│  ├─ QHBoxLayout
│  │  ├─ QLabel("Text:")
│  │  └─ QLineEdit                     → self.wm_text_edit
│  └─ QHBoxLayout
│     ├─ QLabel("Font size:")
│     └─ QSpinBox(8-200, default 24)   → self.spin_font_size
│
├─ QHBoxLayout (shared controls)
│  ├─ QLabel("Vi tri:")
│  └─ QComboBox(9 positions)           → self.combo_wm_position
│
├─ QHBoxLayout
│  ├─ QLabel("Opacity:")
│  ├─ QSlider(Horizontal, 1-100)       → self.opacity_slider
│  └─ QLabel("50%")                    → self.opacity_label
│
└─ QHBoxLayout
   ├─ QLabel("Padding:")
   └─ QSpinBox(0-500, default 10)      → self.spin_wm_padding
```

## Position Dropdown Values
```python
WATERMARK_POSITIONS = [
    ("Top-left", "top-left"),
    ("Top-center", "top-center"),
    ("Top-right", "top-right"),
    ("Middle-left", "middle-left"),
    ("Center", "center"),
    ("Middle-right", "middle-right"),
    ("Bottom-left", "bottom-left"),
    ("Bottom-center", "bottom-center"),
    ("Bottom-right", "bottom-right"),
]
```
Default: "bottom-right" (index 8)

## Implementation Steps

### 1. Add position constant (after `FILTER_STR`, line ~17)
```python
WATERMARK_POSITIONS = [
    "Top-left", "Top-center", "Top-right",
    "Middle-left", "Center", "Middle-right",
    "Bottom-left", "Bottom-center", "Bottom-right",
]
WM_POS_KEYS = [
    "top-left", "top-center", "top-right",
    "middle-left", "center", "middle-right",
    "bottom-left", "bottom-center", "bottom-right",
]
```

### 2. Build watermark GroupBox (insert after rembg section, before progress bar ~line 289)
- Create `QGroupBox("Watermark")`
- Add all widgets per layout above
- Wire checkbox toggled signals to enable/disable child widgets:
  ```python
  self.chk_logo.toggled.connect(self._toggle_logo_controls)
  self.chk_text_wm.toggled.connect(self._toggle_text_controls)
  ```

### 3. Add helper methods to MainWindow
```python
def _toggle_logo_controls(self, enabled):
    self.logo_path_edit.setEnabled(enabled)
    self.btn_logo_browse.setEnabled(enabled)
    self.btn_logo_clear.setEnabled(enabled)
    self.logo_size_slider.setEnabled(enabled)

def _toggle_text_controls(self, enabled):
    self.wm_text_edit.setEnabled(enabled)
    self.spin_font_size.setEnabled(enabled)

def _select_logo(self):
    path, _ = QFileDialog.getOpenFileName(
        self, "Chon logo", "",
        "Images (*.png *.webp *.jpg *.jpeg)"
    )
    if path:
        self.logo_path_edit.setText(path)

def _clear_logo(self):
    self.logo_path_edit.setText("")
```

### 4. Initial state: all watermark controls disabled (checkboxes unchecked)

## Related Code Files
- **Modify**: `resize-webp.py` (MainWindow.__init__, add ~60 lines of UI code)

## Todo
- [x] Add WATERMARK_POSITIONS / WM_POS_KEYS constants
- [x] Build QGroupBox with all widgets
- [x] Wire toggle signals
- [x] Add file dialog methods for logo
- [x] Set initial disabled state
- [x] Verify UI renders correctly

## Completion Notes
- All UI components implemented successfully
- Watermark group visible in right panel between rembg section and progress bar
- Checkboxes toggle child controls as expected
- Logo file picker supports PNG, WEBP, JPG, JPEG formats
- Sliders and spinboxes configured with correct ranges and defaults
- Layout renders without overflow or breakage

## Security Enhancements
- **File Validation**: Logo file picker restricted to image formats only
- **Path Sanitization**: File paths validated on selection
- **Clear Functionality**: Added clear button to remove logo path safely

## Success Criteria
- Watermark group visible in right panel
- Checkboxes toggle child controls enabled/disabled
- Logo file picker opens and sets path
- All sliders/spinboxes show correct ranges and defaults
- No layout overflow or UI breakage

## Risk
- **UI crowding**: Right panel already has many controls. Mitigation: GroupBox keeps it organized, scroll if needed.
