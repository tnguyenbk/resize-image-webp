# Project Overview - Product Development Requirements

**Project Name**: Image Resize WebP
**Version**: 1.2.0
**Last Updated**: 2026-02-11
**Status**: Production-ready with enhanced UI and advanced watermark features

## Executive Summary

Image Resize WebP is a desktop application built with PyQt5 for batch processing images with background removal, intelligent cropping, resizing, format conversion, and professional watermarking capabilities. The application features a 3-column UI layout with independent logo and text watermark controls, including rotation and tiling features. It targets photographers, e-commerce sellers, and content creators who need efficient batch image processing with advanced branding features.

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

### FR5: Watermark (v1.2.0 - Enhanced)
- **FR5.1**: Logo watermarking (independent controls)
  - Enable/disable logo via checkbox
  - Select logo file (PNG, WEBP, JPG, JPEG)
  - Configure logo size (5-80% of image width)
  - Independent position selection: 9-position grid
  - Independent opacity slider (1-100%)
  - Independent edge padding (0-500px)
  - Clear logo path
- **FR5.2**: Text watermarking (independent controls)
  - Enable/disable text via checkbox
  - Enter custom watermark text
  - Configure font size (8-200px)
  - Independent position selection: 9-position grid
  - Independent opacity slider (1-100%)
  - Independent edge padding (0-500px)
  - Text rotation (0-360 degrees)
  - Tiling mode (repeat across entire image)
- **FR5.3**: Logo and text independence
  - Logo and text can be placed at different positions
  - Logo and text have separate opacity and padding controls
  - No stacking behavior (fully independent positioning)

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
- **FR8.4**: Auto-save all watermark settings (14 keys)
- **FR8.5**: Config file: `resize-webp-config.json`
- **FR8.6**: Validate and restore settings on app startup
- **FR8.7**: Config type and range validation for security

### FR9: UI Layout (v1.2.0)
- **FR9.1**: 3-column responsive layout
  - Column 1: File list and selection controls
  - Column 2: Preview, image info, and basic processing controls
  - Column 3: Logo and text watermark sections (independent)
- **FR9.2**: Minimum window size: 1100x600 pixels
- **FR9.3**: Preview panel with image thumbnail (max 400px)
- **FR9.4**: Grouped controls using QGroupBox for clarity

### FR10: Image Preview
- **FR10.1**: Display selected image in preview panel
- **FR10.2**: Show image filename
- **FR10.3**: Show image dimensions (WxH)
- **FR10.4**: Show file size (formatted)
- **FR10.5**: Thumbnail max size: 400px

## Non-Functional Requirements

### NFR1: Performance
- **NFR1.1**: Process 100 images in under 5 minutes (1000px width, u2net model)
- **NFR1.2**: UI remains responsive during processing
- **NFR1.3**: Logo cached once per batch (not per image)
- **NFR1.4**: Memory usage under 2GB for 500 image batches

### NFR2: Usability
- **NFR2.1**: 3-column interface for organized workflow
- **NFR2.2**: Clear labels in Vietnamese (target audience)
- **NFR2.3**: Intuitive control grouping (file list, processing, watermarks)
- **NFR2.4**: Independent logo and text watermark controls
- **NFR2.5**: Immediate visual feedback (preview, progress bar)
- **NFR2.6**: Settings persist across restarts (no re-configuration)
- **NFR2.7**: Minimum window size 1100x600 for comfortable use

### NFR3: Reliability
- **NFR3.1**: Handle corrupted images gracefully (log error, skip file)
- **NFR3.2**: Handle missing logo files gracefully (warn, skip watermark)
- **NFR3.3**: Handle missing fonts gracefully (fallback chain)
- **NFR3.4**: Config corruption recovery (reset to defaults)
- **NFR3.5**: Worker thread cancellation support (clean shutdown)

### NFR4: Security
- **NFR4.1**: Validate logo file paths (no directory traversal)
- **NFR4.2**: Enforce logo file size limit (10MB max)
- **NFR4.3**: Enforce input image file size limit (100MB max)
- **NFR4.4**: Validate file types against whitelist
- **NFR4.5**: Sanitize paths before saving to config
- **NFR4.6**: Config type and range validation to prevent injection
- **NFR4.7**: No arbitrary code execution from config files
- **NFR4.8**: Worker thread guards against restart memory leaks

### NFR5: Maintainability
- **NFR5.1**: Single-file application (resize-webp.py, ~976 LOC)
- **NFR5.2**: Pure functions for core logic (e.g., `apply_watermark()`)
- **NFR5.3**: Clear separation: UI layer, logic layer, worker layer
- **NFR5.4**: Comprehensive inline comments
- **NFR5.5**: Unit tests for critical functions
- **NFR5.6**: Safe config loading with validation helpers

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
- Input images: 100MB maximum (security protection)
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

### AC2: Watermark Feature (v1.2.0)
- User selects logo file (PNG, 2MB)
- User sets logo position to bottom-right, size 20%, opacity 70%, padding 20px
- User enables text watermark "© 2026 Brand"
- User sets text position to top-center, opacity 80%, padding 10px, rotation 45°
- User enables text tiling mode
- User processes 50 images
- All output images show logo at bottom-right and tiled text at specified rotation
- Logo loaded only once (verified in logs)
- Settings persist after restart with correct values

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

### Phase 1: Logo Watermark Feature (v1.1.0 - Completed)
- Added watermark UI controls to right panel
- Implemented `apply_watermark()` pure function
- Worker integration with logo caching
- Config persistence for 9 watermark settings
- **Effort**: 3 hours

### Phase 2: UI Redesign & Enhanced Watermarks (v1.2.0 - Completed)
- Restructured from 2-column to 3-column layout
- Separated logo and text watermark controls (independent)
- Added text rotation (0-360 degrees)
- Added text tiling mode
- Added config validation helpers (`safe_config_int`, `safe_config_str`)
- Added file size limits for security
- Added worker restart guards
- **Effort**: 6 hours

**Total Development Time**: 9 hours

## Risk Assessment

### High Risks (Mitigated)
- **R1**: UI crowding in right panel → Mitigated with 3-column layout
- **R2**: Font not found → Mitigated with fallback chain (arial → DejaVuSans → default)
- **R3**: Thread safety → Mitigated with read-only logo cache
- **R4**: Config corruption → Mitigated with type validation helpers
- **R5**: File size bombs → Mitigated with 100MB input limit

### Medium Risks (Monitored)
- **R6**: Large logo files slow processing → 10MB limit enforced
- **R7**: Non-ASCII text rendering → Pillow handles Unicode, font coverage varies
- **R8**: Window too wide for small screens → 1100px minimum may exclude 1024x768 users

### Low Risks (Accepted)
- **R9**: Config file write frequency → Acceptable for small JSON file
- **R10**: Single-file LOC count (976) → Acceptable for desktop app, modularization planned for v2

## Future Roadmap (V2.0)

### Planned Features
1. Config save debouncing to prevent write race conditions
2. PIL image cleanup with context managers
3. Multiple watermark layers (stack multiple logos/texts)
4. Logo rotation support (-180° to +180°)
5. Text color picker (currently white only)
6. Watermark templates (save/load presets)
7. Drag-and-drop logo positioning with live preview
8. Advanced text effects (outline, shadow, gradient)
9. Batch mode: Different watermarks per image based on filename pattern
10. Scrollable UI for small screens (1024x768 support)

### Planned Improvements
1. Performance optimization: Logo resize caching
2. UI improvements: Watermark preview before processing
3. Export settings: Share config with team members
4. Detailed processing logs for debugging
5. Better font fallback with explicit system paths
6. Worker stop timeout validation

## Version History

### v1.2.0 (2026-02-11)
- Restructured UI from 2-column to 3-column layout (1100x600 minimum)
- Separated logo and text watermark controls (fully independent)
- Added independent position, opacity, and padding for logo and text
- Added text rotation (0-360 degrees)
- Added text tiling mode (repeat across image)
- Added config validation helpers (`safe_config_int`, `safe_config_str`)
- Added file size limit for input images (100MB max)
- Added worker restart guard to prevent memory leaks
- Enhanced security with config type validation
- Config schema extended to 14 watermark keys

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
