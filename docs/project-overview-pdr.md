# Project Overview - Product Development Requirements

**Project Name**: Image Resize WebP
**Version**: 1.1.0
**Last Updated**: 2026-02-10
**Status**: Production-ready with watermark feature

## Executive Summary

Image Resize WebP is a desktop application built with PyQt5 for batch processing images with background removal, intelligent cropping, resizing, format conversion, and professional watermarking capabilities. The application targets photographers, e-commerce sellers, and content creators who need efficient batch image processing with branding features.

## Product Vision

Provide a user-friendly, performant desktop tool for bulk image processing with focus on:
- Background removal for product photography
- Automated cropping and resizing
- WebP conversion for web optimization
- Professional watermarking for brand protection
- Configuration persistence for workflow efficiency

## Functional Requirements

### FR1: Image Input/Output
- **FR1.1**: Select input folder containing images
- **FR1.2**: Select output folder for processed images
- **FR1.3**: Support formats: WEBP, JPG, JPEG, PNG, BMP, TIFF, GIF
- **FR1.4**: Preserve folder structure in output
- **FR1.5**: Display image preview before processing

### FR2: Background Removal
- **FR2.1**: Enable/disable background removal via checkbox
- **FR2.2**: Model selection: u2net_human_seg (portraits), u2net (general)
- **FR2.3**: Process images using rembg library
- **FR2.4**: Output transparent PNG/WEBP images

### FR3: Auto-Crop
- **FR3.1**: Enable/disable auto-crop via checkbox
- **FR3.2**: Detect and remove transparent edges
- **FR3.3**: Preserve aspect ratio after cropping

### FR4: Image Resizing
- **FR4.1**: Mode 1 - Fixed width (W): Resize to width, auto-calculate height
- **FR4.2**: Mode 2 - Fixed height (H): Resize to height, auto-calculate width
- **FR4.3**: Mode 3 - Fixed width and height (W+H): Resize to exact dimensions
- **FR4.4**: Configurable target width (default: 1000px)
- **FR4.5**: Configurable target height (default: 1500px)
- **FR4.6**: Use high-quality LANCZOS resampling

### FR5: Watermark (v1.1.0)
- **FR5.1**: Logo watermarking
  - Enable/disable logo via checkbox
  - Select logo file (PNG, WEBP, JPG, JPEG)
  - Configure logo size (5-80% of image width)
  - Clear logo path
- **FR5.2**: Text watermarking
  - Enable/disable text via checkbox
  - Enter custom watermark text
  - Configure font size (8-200px)
- **FR5.3**: Shared watermark controls
  - Position selection: 9-position grid (top-left to bottom-right)
  - Opacity slider (1-100%)
  - Edge padding (0-500px)
- **FR5.4**: Stacking behavior
  - Logo + text at same position: Stack vertically (logo on top, 5px gap)

### FR6: Output Settings
- **FR6.1**: Save as WebP format
- **FR6.2**: Quality slider (10-100%, default 80%)
- **FR6.3**: File naming: `{original_name}_bg_crop_auto_w{width}.webp`

### FR7: Processing
- **FR7.1**: Start processing button
- **FR7.2**: Background thread processing (non-blocking UI)
- **FR7.3**: Progress bar with percentage display
- **FR7.4**: Status label showing current file
- **FR7.5**: Cancel processing capability
- **FR7.6**: Success/error messages after completion

### FR8: Configuration Persistence
- **FR8.1**: Auto-save last selected input folder
- **FR8.2**: Auto-save last selected output folder
- **FR8.3**: Auto-save rembg model selection
- **FR8.4**: Auto-save all watermark settings (9 keys)
- **FR8.5**: Config file: `resize-webp-config.json`
- **FR8.6**: Validate and restore settings on app startup

### FR9: Image Preview
- **FR9.1**: Display selected image in left panel
- **FR9.2**: Show image filename
- **FR9.3**: Show image dimensions (WxH)
- **FR9.4**: Show file size (formatted)
- **FR9.5**: Thumbnail max size: 400px

## Non-Functional Requirements

### NFR1: Performance
- **NFR1.1**: Process 100 images in under 5 minutes (1000px width, u2net model)
- **NFR1.2**: UI remains responsive during processing
- **NFR1.3**: Logo cached once per batch (not per image)
- **NFR1.4**: Memory usage under 2GB for 500 image batches

### NFR2: Usability
- **NFR2.1**: Single-window interface, no popups during normal flow
- **NFR2.2**: Clear labels in Vietnamese (target audience)
- **NFR2.3**: Intuitive control grouping (folders, processing, output)
- **NFR2.4**: Immediate visual feedback (preview, progress bar)
- **NFR2.5**: Settings persist across restarts (no re-configuration)

### NFR3: Reliability
- **NFR3.1**: Handle corrupted images gracefully (log error, skip file)
- **NFR3.2**: Handle missing logo files gracefully (warn, skip watermark)
- **NFR3.3**: Handle missing fonts gracefully (fallback chain)
- **NFR3.4**: Config corruption recovery (reset to defaults)
- **NFR3.5**: Worker thread cancellation support (clean shutdown)

### NFR4: Security
- **NFR4.1**: Validate logo file paths (no directory traversal)
- **NFR4.2**: Enforce logo file size limit (10MB max)
- **NFR4.3**: Validate file types against whitelist
- **NFR4.4**: Sanitize paths before saving to config
- **NFR4.5**: No arbitrary code execution from config files

### NFR5: Maintainability
- **NFR5.1**: Single-file application (resize-webp.py)
- **NFR5.2**: Pure functions for core logic (e.g., `apply_watermark()`)
- **NFR5.3**: Clear separation: UI layer, logic layer, worker layer
- **NFR5.4**: Comprehensive inline comments
- **NFR5.5**: Unit tests for critical functions

### NFR6: Compatibility
- **NFR6.1**: Python 3.7+ support
- **NFR6.2**: Cross-platform (Windows, macOS, Linux)
- **NFR6.3**: PyQt5 5.x compatibility
- **NFR6.4**: Pillow 8.x+ compatibility
- **NFR6.5**: Rembg 2.x compatibility

## Technical Constraints

### TC1: Dependencies
- PyQt5: GUI framework
- Pillow: Image processing
- rembg: Background removal (requires torch/onnx)

### TC2: System Requirements
- **Minimum**: 4GB RAM, 2-core CPU
- **Recommended**: 8GB RAM, 4-core CPU (for rembg model)
- **Disk**: 500MB for rembg models, variable for image storage

### TC3: File Size Limits
- Input images: No hard limit (tested up to 50MB)
- Logo files: 10MB maximum
- Output WebP: Variable (depends on quality setting)

## Acceptance Criteria

### AC1: Core Workflow
- User selects input folder with 10 mixed images (JPG, PNG, WEBP)
- User selects output folder
- User enables rembg + auto-crop + watermark (logo + text)
- User clicks "Bat dau" button
- App processes all 10 images without errors
- Output folder contains 10 WebP files with watermarks
- All settings restored after app restart

### AC2: Watermark Feature (v1.1.0)
- User selects logo file (PNG, 2MB)
- User sets logo size to 20%, position bottom-right, opacity 70%
- User enables text watermark "© 2026 Brand"
- User processes 50 images
- All output images show logo + text correctly positioned
- Logo loaded only once (verified in logs)
- Settings persist after restart

### AC3: Error Handling
- User selects invalid logo path → Warning shown, watermark skipped
- User processes folder with 1 corrupted image → 9 succeed, 1 skipped with error
- User cancels processing mid-batch → Worker stops cleanly, partial results saved

## Success Metrics

### SM1: Performance
- 95% of batches complete without errors
- Average processing time: 3 seconds per image (1000px, u2net)
- UI responsiveness: No freezes during processing

### SM2: User Satisfaction
- Settings persist correctly: 100% of sessions
- Watermark quality: No pixelation, correct positioning
- Error messages: Clear and actionable

### SM3: Code Quality
- Unit test coverage: >80% for critical functions
- Code review score: >90% (see `plans/reports/code-reviewer-260210-1615-watermark-feature.md`)
- No security vulnerabilities in static analysis

## Development Phases

### Phase 1: UI Components (Completed)
- Added watermark UI controls to right panel
- Checkbox toggles, file picker, sliders, spinboxes
- **Effort**: 1 hour

### Phase 2: Helper Function (Completed)
- Implemented `apply_watermark()` pure function
- Position calculation, opacity adjustment, stacking logic
- **Effort**: 1 hour

### Phase 3: Worker Integration (Completed)
- Extended ResizeWorker with watermark parameters
- Logo caching, pipeline integration
- **Effort**: 30 minutes

### Phase 4: Config Persistence (Completed)
- Added 9 watermark config keys
- Auto-save on all control changes
- **Effort**: 30 minutes

**Total Development Time**: 3 hours (as estimated)

## Risk Assessment

### High Risks (Mitigated)
- **R1**: UI crowding in right panel → Mitigated with organized QGroupBox layout
- **R2**: Font not found → Mitigated with fallback chain (arial → DejaVuSans → default)
- **R3**: Thread safety → Mitigated with read-only logo cache

### Medium Risks (Monitored)
- **R4**: Large logo files slow processing → 10MB limit enforced, performance warning could be added
- **R5**: Non-ASCII text rendering → Pillow handles Unicode, font coverage varies (acceptable for v1)

### Low Risks (Accepted)
- **R6**: Config file corruption → Reset to defaults on load error
- **R7**: Frequent config writes → Acceptable for small JSON file (could add debounce in v2)

## Future Roadmap (V2.0)

### Planned Features
1. Multiple watermark layers (stack multiple logos/texts)
2. Logo rotation support (-180° to +180°)
3. Text color picker (currently white only)
4. Watermark templates (save/load presets)
5. Drag-and-drop logo positioning with live preview
6. Advanced text effects (outline, shadow, gradient)
7. Batch mode: Different watermarks per image based on filename pattern

### Planned Improvements
1. Performance optimization: Logo resize caching
2. UI improvements: Watermark preview before processing
3. Export settings: Share config with team members
4. Logging: Detailed processing logs for debugging

## Version History

### v1.1.0 (2026-02-10)
- Added logo watermarking feature
- Added text watermarking feature
- Added 9-position placement grid
- Added opacity and padding controls
- Added config persistence for watermark settings
- Security hardening (path validation, file size limits)

### v1.0.0 (Initial Release)
- Background removal with rembg
- Auto-crop transparent edges
- Image resizing (W, H, W+H modes)
- WebP conversion with quality settings
- Config persistence (input/output folders, rembg model)

## Glossary

- **Rembg**: Background removal library using ML models
- **Auto-crop**: Automatic removal of transparent/empty edges
- **LANCZOS**: High-quality image resampling algorithm
- **WebP**: Modern image format with superior compression
- **Watermark**: Logo or text overlay for brand protection
- **Config Persistence**: Saving user settings to JSON file
- **Worker Thread**: Background thread for non-blocking processing
