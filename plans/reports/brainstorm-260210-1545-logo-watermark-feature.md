# Brainstorm: Logo & Watermark Feature

## Requirements
- **Type**: Logo image (PNG/WEBP) + Text watermark (both supported)
- **Position**: Dropdown 9 positions (3x3 grid)
- **Controls**: Logo size %, Opacity %, Font size, Padding px
- **Timing**: Apply BEFORE resize (logo scales with image)
- **Persistence**: Save settings in config JSON

## Chosen Approach: Dual Checkbox (Option A)

### Rationale
- KISS principle - clear UI, minimal complexity
- Supports: logo only, text only, or both
- Shared controls (position, opacity, padding) for simplicity
- Stack vertical if both enabled at same position

### UI Design
```
[✓] Logo ảnh
    File: [Chọn...] [Clear]
    Size: [====|===] 20%

[✓] Text watermark
    Text: [________________]
    Font size: [24]

Vị trí: [Bottom-right ▼]
Opacity: [====|===] 50%
Padding: [10] px
```

### Position Grid Mapping
```
TL    TC    TR
ML    C     MR
BL    BC    BR

top-left, top-center, top-right,
middle-left, center, middle-right,
bottom-left, bottom-center, bottom-right
```

## Technical Architecture

### Processing Flow
```
Load → Rembg → Crop → WATERMARK → Resize → Save
                        ↓
              [Logo] [Text] [Both]
```

### Watermark Helper Function
```python
def apply_watermark(img, logo_path=None, text=None,
                    position='bottom-right', logo_size_pct=20,
                    font_size=24, opacity_pct=50, padding=10):
    # Calculate anchor coords
    # Process logo if enabled
    # Process text if enabled
    # Handle stacking if both
    return img
```

### Logo Processing
1. Load logo (cache in worker for batch)
2. Convert to RGBA
3. Resize = img_width * logo_size% (maintain aspect)
4. Adjust opacity via alpha channel
5. Calculate position with padding
6. Composite using Image.alpha_composite()

### Text Processing
1. Create transparent RGBA layer
2. Get font (truetype with fallback to default)
3. Draw text on layer
4. Adjust layer opacity
5. Calculate position (offset if logo exists)
6. Composite layer

### Config Schema
```json
{
  "logo_path": "path/to/logo.png",
  "logo_enabled": false,
  "logo_size_pct": 20,
  "text_content": "© 2026",
  "text_enabled": false,
  "font_size": 24,
  "wm_position": "bottom-right",
  "wm_opacity": 50,
  "wm_padding": 10
}
```

## Risk Assessment

### 1. Font Availability
- **Risk**: Default font ugly or missing
- **Mitigation**: Use ImageFont.truetype() with DejaVu fallback
- **V2**: Allow custom font file selection

### 2. Logo Alpha Channel
- **Risk**: Some logos RGB only (no transparency)
- **Mitigation**: Convert all to RGBA before processing

### 3. Text Opacity Rendering
- **Risk**: Pillow no direct text opacity
- **Mitigation**: Draw on transparent layer, adjust alpha, composite

### 4. Performance
- **Risk**: Loading logo per image = slow batch
- **Mitigation**: Cache logo PIL object in worker, load once

### 5. Edge Cases
- **Risk**: Logo/text overflow bounds with large padding
- **Mitigation**: Clamp coords to image boundaries

## Success Criteria
- [✓] Logo PNG/WEBP paste correct position, size, opacity
- [✓] Text render clear with proper font size
- [✓] Both logo + text compatible (no conflict)
- [✓] Config save/load accurate
- [✓] Performance < 2s/image (with cached logo)
- [✓] No crashes on edge inputs

## Rejected Alternatives

### Option B: Tab Layout
- Too complex for simple use case (violates YAGNI)
- QTabWidget overhead

### Option C: Single Mode Switch
- Doesn't meet "both" requirement
- Less flexible

## Implementation Phases

1. **UI Components** (30% effort)
   - Add checkboxes, inputs, sliders, spinboxes
   - Wire up enable/disable logic
   - Load/save config values

2. **Helper Function** (40% effort)
   - Position calculation logic
   - Logo load, resize, opacity
   - Text render, opacity
   - Stacking logic
   - Error handling

3. **Worker Integration** (20% effort)
   - Pass params to worker
   - Call helper after crop, before resize
   - Cache logo for batch processing

4. **Testing** (10% effort)
   - Logo only, text only, both
   - All 9 positions
   - Edge cases (large padding, small image)
   - Config persistence
