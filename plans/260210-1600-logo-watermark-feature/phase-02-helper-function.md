# Phase 2: Helper Function `apply_watermark()`

## Priority: P1 | Status: **COMPLETED** ✓

## Overview
Standalone function (like `calc_resize()`) that composites logo and/or text onto an image. Placed after `calc_resize()` (~line 64).

## Key Insights
- Image is RGBA at this point in pipeline (converted at line 97)
- Logo must be resized relative to **current** image dimensions (pre-resize)
- Text drawn on transparent layer, then composited (Pillow has no direct text opacity)
- If both logo + text at same position, stack vertically (logo on top, text below)

## Function Signature
```python
def apply_watermark(img, logo_img=None, text=None,
                    position='bottom-right', logo_size_pct=20,
                    font_size=24, opacity_pct=50, padding=10):
    """Apply logo and/or text watermark to RGBA image. Returns new image."""
```

## Parameters
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| img | PIL.Image (RGBA) | required | Source image |
| logo_img | PIL.Image or None | None | Pre-loaded logo (already RGBA) |
| text | str or None | None | Watermark text |
| position | str | 'bottom-right' | One of WM_POS_KEYS |
| logo_size_pct | int | 20 | Logo width as % of image width |
| font_size | int | 24 | Text font size in pixels |
| opacity_pct | int | 50 | Opacity 1-100 |
| padding | int | 10 | Distance from edge in px |

## Implementation Steps

### 1. Early return
```python
if not logo_img and not text:
    return img
```

### 2. Position calculation helper (internal)
```python
def _calc_anchor(element_w, element_h, img_w, img_h, position, padding):
    """Return (x, y) for element placement."""
    # Horizontal
    if 'left' in position:
        x = padding
    elif 'right' in position:
        x = img_w - element_w - padding
    else:  # center
        x = (img_w - element_w) // 2

    # Vertical
    if 'top' in position:
        y = padding
    elif 'bottom' in position:
        y = img_h - element_h - padding
    else:  # middle
        y = (img_h - element_h) // 2

    return x, y
```

### 3. Opacity adjustment helper
```python
def _adjust_opacity(layer, opacity_pct):
    """Multiply alpha channel by opacity percentage."""
    r, g, b, a = layer.split()
    a = a.point(lambda p: int(p * opacity_pct / 100))
    return Image.merge("RGBA", (r, g, b, a))
```

### 4. Logo processing
```python
if logo_img:
    # Resize logo proportionally
    logo_w = max(1, int(img.width * logo_size_pct / 100))
    ratio = logo_w / logo_img.width
    logo_h = max(1, int(logo_img.height * ratio))
    logo_resized = logo_img.resize((logo_w, logo_h), Image.LANCZOS)
    # Adjust opacity
    logo_resized = _adjust_opacity(logo_resized, opacity_pct)
```

### 5. Text processing
```python
if text:
    from PIL import ImageDraw, ImageFont
    # Try system font, fallback to default
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except OSError:
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()
    # Measure text
    txt_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(txt_layer)
    bbox = draw.textbbox((0, 0), text, font=font)
    txt_w = bbox[2] - bbox[0]
    txt_h = bbox[3] - bbox[1]
```

### 6. Stacking logic (both enabled, same position)
```python
if logo_img and text:
    # Stack: logo on top, text below, 5px gap
    total_h = logo_h + 5 + txt_h
    total_w = max(logo_w, txt_w)
    ax, ay = _calc_anchor(total_w, total_h, img.width, img.height, position, padding)
    # Paste logo
    logo_x = ax + (total_w - logo_w) // 2
    img.paste(logo_resized, (logo_x, ay), logo_resized)
    # Draw text
    txt_x = ax + (total_w - txt_w) // 2
    txt_y = ay + logo_h + 5
    draw2 = ImageDraw.Draw(txt_layer)
    draw2.text((txt_x, txt_y), text, font=font, fill=(255, 255, 255, 255))
    txt_layer = _adjust_opacity(txt_layer, opacity_pct)
    img = Image.alpha_composite(img, txt_layer)
```

### 7. Single element placement
```python
elif logo_img:
    ax, ay = _calc_anchor(logo_w, logo_h, img.width, img.height, position, padding)
    img.paste(logo_resized, (ax, ay), logo_resized)
elif text:
    ax, ay = _calc_anchor(txt_w, txt_h, img.width, img.height, position, padding)
    draw.text((ax, ay), text, font=font, fill=(255, 255, 255, 255))
    txt_layer = _adjust_opacity(txt_layer, opacity_pct)
    img = Image.alpha_composite(img, txt_layer)
```

### 8. Return modified image
```python
return img
```

## Related Code Files
- **Modify**: `resize-webp.py` - add `apply_watermark()` function after `calc_resize()` (~line 64)
- **Import needed**: `ImageDraw, ImageFont` from PIL (lazy import inside function to avoid startup cost)

## Todo
- [x] Implement `apply_watermark()` with position calc
- [x] Implement opacity adjustment
- [x] Implement logo resize + composite
- [x] Implement text render + composite
- [x] Implement stacking logic
- [x] Handle edge cases (coords clamped to bounds)

## Completion Notes
- `apply_watermark()` function fully implemented as standalone helper
- Position calculation logic working correctly for all 9 positions
- Opacity adjustment applied via alpha channel manipulation
- Logo resized proportionally based on percentage of image width
- Text rendered with font fallback chain (arial → DejaVuSans → default)
- Stacking logic implemented: logo on top, text below with 5px gap
- Edge cases handled: coordinates clamped, zero-size protection, missing fonts
- Function is pure with no side effects, returns new RGBA image

## Technical Details
- Uses internal `_calc_anchor()` helper for position computation
- Uses `_adjust_opacity()` helper for alpha channel adjustment
- Text drawn on transparent layer then alpha-composited for opacity control
- Lazy import of ImageDraw/ImageFont to minimize startup cost
- LANCZOS resampling for high-quality logo resizing

## Success Criteria
- Logo renders at correct position with correct size and opacity
- Text renders with readable font
- Both logo + text stack correctly when at same position
- No crash on edge inputs (0% size, huge padding, missing font)
- Function is pure (no side effects, returns new image)

## Risk
- **Font not found**: Fallback chain: arial.ttf -> DejaVuSans.ttf -> default bitmap font
- **Logo overflow**: Clamp coordinates with `max(0, ...)` to keep within bounds
