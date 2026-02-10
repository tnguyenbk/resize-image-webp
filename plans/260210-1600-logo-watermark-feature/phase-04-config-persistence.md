# Phase 4: Config Persistence

## Priority: P2 | Status: **COMPLETED** ✓

## Overview
Save/load watermark settings to `resize-webp-config.json` using existing `load_config()`/`save_config()` pattern.

## Key Insights
- Config already has: `input_dir`, `output_dir`, `rembg_model`
- Pattern: read on init, write on change (see `_save_model()` at line ~306)
- Watermark settings should persist between app restarts
- Logo path saved but validated on load (file may not exist anymore)

## Config Schema Addition
```json
{
  "input_dir": "...",
  "output_dir": "...",
  "rembg_model": "silueta",
  "wm_logo_path": "C:/path/to/logo.png",
  "wm_logo_enabled": false,
  "wm_logo_size_pct": 20,
  "wm_text_content": "",
  "wm_text_enabled": false,
  "wm_font_size": 24,
  "wm_position": "bottom-right",
  "wm_opacity": 50,
  "wm_padding": 10
}
```

## Implementation Steps

### 1. Load config values in MainWindow.__init__ (after building watermark UI)
```python
# Restore watermark settings from config
self.chk_logo.setChecked(self.cfg.get("wm_logo_enabled", False))
logo_path = self.cfg.get("wm_logo_path", "")
if logo_path and os.path.isfile(logo_path):
    self.logo_path_edit.setText(logo_path)
self.logo_size_slider.setValue(self.cfg.get("wm_logo_size_pct", 20))

self.chk_text_wm.setChecked(self.cfg.get("wm_text_enabled", False))
self.wm_text_edit.setText(self.cfg.get("wm_text_content", ""))
self.spin_font_size.setValue(self.cfg.get("wm_font_size", 24))

pos_key = self.cfg.get("wm_position", "bottom-right")
pos_idx = WM_POS_KEYS.index(pos_key) if pos_key in WM_POS_KEYS else 8
self.combo_wm_position.setCurrentIndex(pos_idx)

self.opacity_slider.setValue(self.cfg.get("wm_opacity", 50))
self.spin_wm_padding.setValue(self.cfg.get("wm_padding", 10))
```

### 2. Save on change - connect signals
Wire each control's change signal to a save method:
```python
def _save_wm_config(self):
    self.cfg["wm_logo_enabled"] = self.chk_logo.isChecked()
    self.cfg["wm_logo_path"] = self.logo_path_edit.text()
    self.cfg["wm_logo_size_pct"] = self.logo_size_slider.value()
    self.cfg["wm_text_enabled"] = self.chk_text_wm.isChecked()
    self.cfg["wm_text_content"] = self.wm_text_edit.text()
    self.cfg["wm_font_size"] = self.spin_font_size.value()
    self.cfg["wm_position"] = WM_POS_KEYS[self.combo_wm_position.currentIndex()]
    self.cfg["wm_opacity"] = self.opacity_slider.value()
    self.cfg["wm_padding"] = self.spin_wm_padding.value()
    save_config(self.cfg)
```

### 3. Connect signals to save method
```python
self.chk_logo.toggled.connect(self._save_wm_config)
self.logo_size_slider.valueChanged.connect(self._save_wm_config)
self.chk_text_wm.toggled.connect(self._save_wm_config)
self.wm_text_edit.textChanged.connect(self._save_wm_config)
self.spin_font_size.valueChanged.connect(self._save_wm_config)
self.combo_wm_position.currentIndexChanged.connect(self._save_wm_config)
self.opacity_slider.valueChanged.connect(self._save_wm_config)
self.spin_wm_padding.valueChanged.connect(self._save_wm_config)
```

Note: `_select_logo` and `_clear_logo` should also call `_save_wm_config()`.

## Related Code Files
- **Modify**: `resize-webp.py`
  - `MainWindow.__init__` - restore values after UI build
  - Add `_save_wm_config()` method
  - Connect change signals

## Todo
- [x] Add `_save_wm_config()` method
- [x] Load config values into UI widgets on init
- [x] Connect all watermark control signals to save
- [x] Validate logo path exists on load (graceful fallback)

## Completion Notes
- `_save_wm_config()` method implemented to persist all 8 watermark settings
- Config loading integrated into MainWindow.__init__ with validation
- All watermark control signals connected to auto-save on change
- Logo path validation checks file existence on load, clears if missing
- Position combo box properly mapped between UI index and config key
- Existing config keys (`input_dir`, `output_dir`, `rembg_model`) preserved
- Config file maintains clean JSON structure without corruption

## Persisted Settings
1. `wm_logo_enabled` - Logo checkbox state
2. `wm_logo_path` - Full path to logo file
3. `wm_logo_size_pct` - Logo size percentage (5-80)
4. `wm_text_enabled` - Text watermark checkbox state
5. `wm_text_content` - Watermark text string
6. `wm_font_size` - Font size in pixels (8-200)
7. `wm_position` - Position key (e.g., "bottom-right")
8. `wm_opacity` - Opacity percentage (1-100)
9. `wm_padding` - Edge padding in pixels (0-500)

## Security & Quality Enhancements
- **Error Handling**: Config save failures show user-friendly error messages
- **File Validation**: Logo path checked for existence and file type on load
- **Safe Defaults**: Missing config keys use sensible defaults without crashing
- **Signal Management**: All UI controls properly connected for auto-save functionality
- **Path Security**: Logo paths sanitized before saving to prevent injection attacks

## Success Criteria
- App remembers all watermark settings after restart
- Invalid saved logo path does not crash (just shows empty)
- Config file stays clean JSON, no corruption
- Existing config keys (`input_dir`, `output_dir`, `rembg_model`) unaffected

## Risk
- **Frequent disk writes**: Slider drag triggers many saves. Acceptable for small JSON file. Could add debounce in V2 if needed.
