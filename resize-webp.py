import sys
import os
import json
import traceback
from io import BytesIO
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QListWidget, QPushButton, QLabel, QSpinBox, QCheckBox, QSlider,
    QFileDialog, QProgressBar, QGroupBox, QFormLayout, QMessageBox,
    QLineEdit, QRadioButton, QAbstractItemView, QComboBox,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage
from PIL import Image

SUPPORTED_EXTS = {".webp", ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".gif"}
FILTER_STR = "Images (" + " ".join(f"*{e}" for e in sorted(SUPPORTED_EXTS)) + ")"
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resize-webp-config.json")

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


def pil_to_qpixmap(pil_img, max_size=400):
    # Keep aspect ratio and fit within max_size
    pil_img = pil_img.copy()
    pil_img.thumbnail((max_size, max_size), Image.LANCZOS)
    buf = BytesIO()
    pil_img.save(buf, format="PNG")
    qimg = QImage()
    qimg.loadFromData(buf.getvalue())
    return QPixmap.fromImage(qimg)


def fmt_size(size):
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def safe_config_int(cfg, key, default, min_val=None, max_val=None):
    """Safely load integer from config with validation."""
    try:
        val = int(cfg.get(key, default))
        if min_val is not None and val < min_val:
            return default
        if max_val is not None and val > max_val:
            return default
        return val
    except (ValueError, TypeError):
        return default


def safe_config_str(cfg, key, default, valid_values=None):
    """Safely load string from config with validation."""
    val = cfg.get(key, default)
    if not isinstance(val, str):
        return default
    if valid_values and val not in valid_values:
        return default
    return val


def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[WARN] Failed to save config: {e}")


def calc_resize(orig_w, orig_h, target_w, target_h, use_max_size, max_size):
    if use_max_size:
        if orig_w >= orig_h:
            new_w = min(orig_w, max_size)
            new_h = max(1, round(new_w * orig_h / orig_w))
        else:
            new_h = min(orig_h, max_size)
            new_w = max(1, round(new_h * orig_w / orig_h))
        return new_w, new_h
    return target_w, target_h


def apply_watermark(img, logo_img=None, text=None,
                    # Logo params (independent)
                    logo_position='bottom-right', logo_size_pct=20,
                    logo_opacity_pct=50, logo_padding=10,
                    logo_size_mode='width',
                    # Text params (independent)
                    text_position='bottom-right', font_size=24,
                    text_opacity_pct=50, text_padding=10,
                    # New params
                    text_rotation=0, text_tiling=False):
    """Apply logo and/or text watermark to RGBA image with independent controls. Returns new image."""
    if not logo_img and not text:
        return img

    from PIL import ImageDraw, ImageFont

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

        return max(0, x), max(0, y)

    def _adjust_opacity(layer, opacity_pct):
        """Multiply alpha channel by opacity percentage."""
        r, g, b, a = layer.split()
        a = a.point(lambda p: int(p * opacity_pct / 100))
        return Image.merge("RGBA", (r, g, b, a))

    # Process logo
    if logo_img:
        # Calculate logo size based on mode
        if logo_size_mode == 'px':
            # Fixed pixel size
            logo_w = max(1, int(logo_size_pct))
        elif logo_size_mode == 'max':
            # Size based on max edge (longest side)
            max_edge = max(img.width, img.height)
            logo_w = max(1, int(max_edge * logo_size_pct / 100))
        else:  # 'width'
            # Size based on width (default)
            logo_w = max(1, int(img.width * logo_size_pct / 100))

        ratio = logo_w / logo_img.width
        logo_h = max(1, int(logo_img.height * ratio))
        logo_resized = logo_img.resize((logo_w, logo_h), Image.LANCZOS)
        logo_resized = _adjust_opacity(logo_resized, logo_opacity_pct)
        ax, ay = _calc_anchor(logo_w, logo_h, img.width, img.height, logo_position, logo_padding)
        img.paste(logo_resized, (ax, ay), logo_resized)

    # Process text watermark
    if text:
        # Try system font, fallback to default
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except OSError:
            try:
                font = ImageFont.truetype("DejaVuSans.ttf", font_size)
            except OSError:
                font = ImageFont.load_default()

        # Create text layer
        temp_layer = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        temp_draw = ImageDraw.Draw(temp_layer)
        bbox = temp_draw.textbbox((0, 0), text, font=font)
        txt_w = bbox[2] - bbox[0]
        txt_h = bbox[3] - bbox[1]

        # Create tight text image with extra padding to prevent clipping
        padding = max(10, int(font_size * 0.3))
        text_img = Image.new("RGBA", (txt_w + padding * 2, txt_h + padding * 2), (0, 0, 0, 0))
        draw = ImageDraw.Draw(text_img)
        # Draw text with offset to account for bbox positioning
        draw.text((padding - bbox[0], padding - bbox[1]), text, font=font, fill=(255, 255, 255, 255))

        # Apply rotation if needed
        if text_rotation != 0:
            text_img = text_img.rotate(-text_rotation, expand=True, fillcolor=(0, 0, 0, 0))

        # Tiling or single placement
        if text_tiling:
            # Create tile layer
            tile_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
            tw, th = text_img.size
            step_x = int(tw * 2)  # 2x spacing
            step_y = int(th * 2)
            start_x = -(tw // 2)
            start_y = -(th // 2)

            y = start_y
            while y < img.height:
                x = start_x
                while x < img.width:
                    tile_layer.paste(text_img, (x, y), text_img)
                    x += step_x
                y += step_y

            # Apply opacity to entire tile layer
            tile_layer = _adjust_opacity(tile_layer, text_opacity_pct)
            img = Image.alpha_composite(img, tile_layer)
        else:
            # Single placement at position
            tw, th = text_img.size
            ax, ay = _calc_anchor(tw, th, img.width, img.height, text_position, text_padding)
            text_img = _adjust_opacity(text_img, text_opacity_pct)
            img.paste(text_img, (ax, ay), text_img)

    return img


class ResizeWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(int, int, int, int)

    def __init__(self, files, target_w, target_h, quality, output_dir,
                 same_as_input, use_max_size, max_size, rembg_fn=None,
                 model_name="u2net", crop_pct=0, auto_crop_white=False, white_tolerance=10,
                 # Output format and size mode
                 output_format="webp", keep_original=False,
                 # Watermark params
                 wm_logo_path=None, logo_position='bottom-right', logo_size_pct=20,
                 logo_opacity_pct=50, logo_padding=10, logo_size_mode='width',
                 wm_text=None, text_position='bottom-right', font_size=24,
                 text_opacity_pct=50, text_padding=10,
                 text_rotation=0, text_tiling=False):
        super().__init__()
        self.files = files
        self.target_w = target_w
        self.target_h = target_h
        self.quality = quality
        self.output_dir = output_dir
        self.same_as_input = same_as_input
        self.use_max_size = use_max_size
        self.max_size = max_size
        self.rembg_fn = rembg_fn
        self.model_name = model_name
        self.crop_pct = crop_pct
        self.auto_crop_white = auto_crop_white
        self.white_tolerance = white_tolerance
        self.output_format = output_format.lower()
        self.keep_original = keep_original
        self.wm_logo_path = wm_logo_path
        self.logo_position = logo_position
        self.logo_size_pct = logo_size_pct
        self.logo_opacity_pct = logo_opacity_pct
        self.logo_padding = logo_padding
        self.logo_size_mode = logo_size_mode
        self.wm_text = wm_text
        self.text_position = text_position
        self.font_size = font_size
        self.text_opacity_pct = text_opacity_pct
        self.text_padding = text_padding
        self.text_rotation = text_rotation
        self.text_tiling = text_tiling
        self._stop_requested = False

    def stop(self):
        self._stop_requested = True

    def run(self):
        session = None
        if self.rembg_fn:
            from rembg import new_session
            print(f"[INFO] Loading model: {self.model_name}...")
            session = new_session(self.model_name)

        # Cache logo for batch
        wm_logo_img = None
        if self.wm_logo_path:
            try:
                wm_logo_img = Image.open(self.wm_logo_path).convert("RGBA")
                print(f"[INFO] Logo loaded: {self.wm_logo_path}")
            except Exception as e:
                print(f"[WARN] Cannot load logo: {e}")

        ok, fail, total_before, total_after = 0, 0, 0, 0
        for i, path in enumerate(self.files):
            if self._stop_requested:
                print("[INFO] Processing stopped by user")
                break
            print(f"[INFO] Processing {os.path.basename(path)}...")
            try:
                # Check file size (max 100MB to prevent decompression bombs)
                file_size = os.path.getsize(path)
                if file_size > 100 * 1024 * 1024:
                    print(f"[WARN] File too large ({file_size / (1024*1024):.1f}MB), skipped: {os.path.basename(path)}")
                    fail += 1
                    continue

                total_before += file_size
                img = Image.open(path).convert("RGBA")
                if self.rembg_fn and session:
                    img = self.rembg_fn(img, session=session)
                if self.crop_pct > 0:
                    cw, ch = img.size
                    dx = int(cw * self.crop_pct / 200)
                    dy = int(ch * self.crop_pct / 200)
                    img = img.crop((dx, dy, cw - dx, ch - dy))

                # Auto crop white border
                if self.auto_crop_white:
                    from PIL import ImageChops
                    # Create white background reference, find content bounds
                    bg = Image.new("RGB", img.size, (255, 255, 255))
                    rgb_img = img.convert("RGB")
                    diff = ImageChops.difference(rgb_img, bg)
                    # Apply tolerance: pixels with diff <= tolerance are considered white
                    if self.white_tolerance > 0:
                        diff = diff.point(lambda p: 0 if p <= self.white_tolerance else p)
                    bbox = diff.getbbox()
                    if bbox:
                        img = img.crop(bbox)

                # Apply watermark (before resize)
                if wm_logo_img or self.wm_text:
                    img = apply_watermark(
                        img, logo_img=wm_logo_img, text=self.wm_text,
                        logo_position=self.logo_position,
                        logo_size_pct=self.logo_size_pct,
                        logo_opacity_pct=self.logo_opacity_pct,
                        logo_padding=self.logo_padding,
                        logo_size_mode=self.logo_size_mode,
                        text_position=self.text_position,
                        font_size=self.font_size,
                        text_opacity_pct=self.text_opacity_pct,
                        text_padding=self.text_padding,
                        text_rotation=self.text_rotation,
                        text_tiling=self.text_tiling,
                    )

                # Resize (or keep original)
                if self.keep_original:
                    resized = img
                else:
                    w, h = calc_resize(img.width, img.height,
                                       self.target_w, self.target_h,
                                       self.use_max_size, self.max_size)
                    resized = img.resize((w, h), Image.LANCZOS)

                # Determine output format and extension
                if self.output_format == "jpeg" or self.output_format == "jpg":
                    ext = ".jpg"
                    save_format = "JPEG"
                    # Convert RGBA to RGB for JPEG
                    if resized.mode == "RGBA":
                        rgb_img = Image.new("RGB", resized.size, (255, 255, 255))
                        rgb_img.paste(resized, mask=resized.split()[3])
                        resized = rgb_img
                elif self.output_format == "png":
                    ext = ".png"
                    save_format = "PNG"
                else:  # webp
                    ext = ".webp"
                    save_format = "WEBP"

                basename = os.path.splitext(os.path.basename(path))[0]
                if self.same_as_input:
                    out_dir = os.path.dirname(path)
                    out_path = os.path.join(out_dir, f"{basename}_resized{ext}")
                else:
                    out_path = os.path.join(self.output_dir, f"{basename}{ext}")
                # Avoid overwriting existing files
                if os.path.exists(out_path):
                    n = 2
                    while True:
                        candidate = os.path.join(
                            os.path.dirname(out_path),
                            f"{basename} ({n}){ext}"
                        )
                        if not os.path.exists(candidate):
                            out_path = candidate
                            break
                        n += 1

                # Save with appropriate format and quality
                if save_format == "PNG":
                    resized.save(out_path, save_format)
                else:
                    resized.save(out_path, save_format, quality=self.quality)
                total_after += os.path.getsize(out_path)
                ok += 1
            except Exception as e:
                print(f"[ERROR] {os.path.basename(path)}: {e}")
                traceback.print_exc()
                fail += 1
            self.progress.emit(i + 1)
        self.finished.emit(ok, fail, total_before, total_after)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Resize & Convert to WebP")
        self.setMinimumSize(1100, 600)
        self.files = []
        self.current_img = None
        self.aspect_ratio = 1.0
        self.updating_spinbox = False
        self.cfg = load_config()
        self._rembg_remove = None
        self.worker = None

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        # --- Column 1: File List ---
        col1 = QVBoxLayout()
        btn_row = QHBoxLayout()
        btn_files = QPushButton("Chọn Files")
        btn_folder = QPushButton("Chọn Folder")
        btn_clear = QPushButton("Xóa hết")
        btn_delete = QPushButton("Xóa selected")
        btn_files.clicked.connect(self.select_files)
        btn_folder.clicked.connect(self.select_folder)
        btn_clear.clicked.connect(self.clear_files)
        btn_delete.clicked.connect(self.delete_selected)
        btn_row.addWidget(btn_files)
        btn_row.addWidget(btn_folder)
        btn_row.addWidget(btn_delete)
        btn_row.addWidget(btn_clear)
        col1.addLayout(btn_row)

        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.file_list.currentRowChanged.connect(self.on_file_selected)
        col1.addWidget(self.file_list)

        self.select_info = QLabel("Ctrl/Shift+click để chọn nhiều. Không chọn = tất cả.")
        self.select_info.setStyleSheet("color: #666; font-size: 11px;")
        col1.addWidget(self.select_info)

        layout.addLayout(col1, 1)

        # --- Column 2: Preview + Basic Controls ---
        col2 = QVBoxLayout()

        self.preview_label = QLabel("Chưa chọn ảnh")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(400, 280)
        self.preview_label.setMaximumSize(600, 450)
        self.preview_label.setScaledContents(False)
        self.preview_label.setStyleSheet("border: 1px solid #ccc; background: #f9f9f9;")
        col2.addWidget(self.preview_label, 1)

        self.info_label = QLabel("")
        col2.addWidget(self.info_label)

        # Output folder
        out_group = QGroupBox("Folder output")
        out_layout = QHBoxLayout(out_group)
        self.output_edit = QLineEdit(self.cfg.get("output_dir", ""))
        self.output_edit.setPlaceholderText("Cùng folder với file gốc")
        self.output_edit.setReadOnly(True)
        btn_out = QPushButton("Chọn...")
        btn_out_clear = QPushButton("Reset")
        btn_out.clicked.connect(self.select_output_dir)
        btn_out_clear.clicked.connect(self.clear_output_dir)
        out_layout.addWidget(self.output_edit, 1)
        out_layout.addWidget(btn_out)
        out_layout.addWidget(btn_out_clear)
        col2.addWidget(out_group)

        # Size controls
        size_group = QGroupBox("Kích thước")
        size_layout = QVBoxLayout(size_group)

        # Mode: exact vs max vs keep original
        self.radio_exact = QRadioButton("Chính xác (W x H)")
        self.radio_max = QRadioButton("Theo max (giữ tỷ lệ từng ảnh)")
        self.radio_keep = QRadioButton("Giữ nguyên (không resize)")
        self.radio_exact.setChecked(True)
        self.radio_exact.toggled.connect(self.on_mode_changed)
        self.radio_max.toggled.connect(self.on_mode_changed)
        self.radio_keep.toggled.connect(self.on_mode_changed)
        size_layout.addWidget(self.radio_exact)
        size_layout.addWidget(self.radio_max)
        size_layout.addWidget(self.radio_keep)

        # Exact size inputs
        self.exact_widget = QWidget()
        exact_form = QFormLayout(self.exact_widget)
        exact_form.setContentsMargins(0, 0, 0, 0)
        self.spin_w = QSpinBox()
        self.spin_w.setRange(1, 99999)
        self.spin_w.setValue(800)
        self.spin_h = QSpinBox()
        self.spin_h.setRange(1, 99999)
        self.spin_h.setValue(600)
        self.spin_w.valueChanged.connect(self.on_width_changed)
        self.spin_h.valueChanged.connect(self.on_height_changed)
        self.lock_ratio = QCheckBox("Giữ tỷ lệ")
        self.lock_ratio.setChecked(True)
        exact_form.addRow("Width:", self.spin_w)
        exact_form.addRow("Height:", self.spin_h)
        exact_form.addRow(self.lock_ratio)
        size_layout.addWidget(self.exact_widget)

        # Max size input
        self.max_widget = QWidget()
        max_form = QFormLayout(self.max_widget)
        max_form.setContentsMargins(0, 0, 0, 0)
        self.spin_max = QSpinBox()
        self.spin_max.setRange(1, 99999)
        self.spin_max.setValue(1024)
        max_form.addRow("Max (px):", self.spin_max)
        self.max_widget.setVisible(False)
        size_layout.addWidget(self.max_widget)

        col2.addWidget(size_group)

        # Crop border
        crop_layout = QHBoxLayout()
        crop_layout.addWidget(QLabel("Crop viền (%):"))
        self.spin_crop = QSpinBox()
        self.spin_crop.setRange(0, 80)
        self.spin_crop.setValue(0)
        self.spin_crop.setSuffix("%")
        crop_layout.addWidget(self.spin_crop)
        col2.addLayout(crop_layout)

        # Auto crop white border
        auto_crop_layout = QHBoxLayout()
        self.chk_auto_crop_white = QCheckBox("Auto crop viền trắng")
        self.chk_auto_crop_white.setChecked(self.cfg.get("auto_crop_white", False))
        self.chk_auto_crop_white.toggled.connect(self._save_auto_crop_config)
        auto_crop_layout.addWidget(self.chk_auto_crop_white)
        self.spin_white_tolerance = QSpinBox()
        self.spin_white_tolerance.setRange(0, 50)
        self.spin_white_tolerance.setValue(safe_config_int(self.cfg, "white_tolerance", 10, 0, 50))
        self.spin_white_tolerance.setPrefix("Tolerance: ")
        self.spin_white_tolerance.setToolTip("Ngưỡng nhận diện trắng (0=trắng tuyệt đối, cao hơn=rộng hơn)")
        self.spin_white_tolerance.valueChanged.connect(self._save_auto_crop_config)
        auto_crop_layout.addWidget(self.spin_white_tolerance)
        col2.addLayout(auto_crop_layout)

        # Quality slider
        q_layout = QHBoxLayout()
        q_layout.addWidget(QLabel("Chất lượng:"))
        self.quality_slider = QSlider(Qt.Horizontal)
        self.quality_slider.setRange(1, 100)
        self.quality_slider.setValue(80)
        self.quality_label = QLabel("80")
        self.quality_slider.valueChanged.connect(lambda v: self.quality_label.setText(str(v)))
        q_layout.addWidget(self.quality_slider)
        q_layout.addWidget(self.quality_label)
        col2.addLayout(q_layout)

        # Export format selector
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Định dạng:"))
        self.combo_format = QComboBox()
        self.combo_format.addItems(["WebP", "JPEG", "PNG"])
        self.combo_format.setCurrentIndex(0)
        format_layout.addWidget(self.combo_format, 1)
        col2.addLayout(format_layout)

        # Remove background
        rembg_layout = QHBoxLayout()
        self.chk_rembg = QCheckBox("Xóa nền")
        self.combo_model = QComboBox()
        self.combo_model.addItems(["u2net", "silueta"])
        saved_model = self.cfg.get("rembg_model", "u2net")
        idx = self.combo_model.findText(saved_model)
        if idx >= 0:
            self.combo_model.setCurrentIndex(idx)
        self.combo_model.setEnabled(False)
        self.chk_rembg.toggled.connect(self.combo_model.setEnabled)
        self.combo_model.currentTextChanged.connect(self._save_model)
        rembg_layout.addWidget(self.chk_rembg)
        rembg_layout.addWidget(QLabel("Model:"))
        rembg_layout.addWidget(self.combo_model, 1)
        col2.addLayout(rembg_layout)

        # Progress + button
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        col2.addWidget(self.progress)

        self.btn_resize = QPushButton("Convert to WebP")
        self.btn_resize.setStyleSheet("padding: 8px; font-weight: bold;")
        self.btn_resize.clicked.connect(self.start_resize)
        col2.addWidget(self.btn_resize)

        layout.addLayout(col2, 1)

        # --- Column 3: Logo + Watermark ---
        col3 = QVBoxLayout()

        # Logo section
        logo_group = QGroupBox("Logo")
        logo_layout = QVBoxLayout(logo_group)

        self.chk_logo = QCheckBox("Logo ảnh")
        logo_layout.addWidget(self.chk_logo)

        logo_path_layout = QHBoxLayout()
        self.logo_path_edit = QLineEdit()
        self.logo_path_edit.setReadOnly(True)
        self.logo_path_edit.setPlaceholderText("Chọn file logo...")
        self.btn_logo_browse = QPushButton("Chọn...")
        self.btn_logo_clear = QPushButton("Clear")
        self.btn_logo_browse.clicked.connect(self._select_logo)
        self.btn_logo_clear.clicked.connect(self._clear_logo)
        logo_path_layout.addWidget(self.logo_path_edit, 1)
        logo_path_layout.addWidget(self.btn_logo_browse)
        logo_path_layout.addWidget(self.btn_logo_clear)
        logo_layout.addLayout(logo_path_layout)

        logo_position_layout = QHBoxLayout()
        logo_position_layout.addWidget(QLabel("Vị trí:"))
        self.combo_logo_position = QComboBox()
        self.combo_logo_position.addItems(WATERMARK_POSITIONS)
        self.combo_logo_position.setCurrentIndex(8)  # Default: bottom-right
        logo_position_layout.addWidget(self.combo_logo_position, 1)
        logo_layout.addLayout(logo_position_layout)

        logo_opacity_layout = QHBoxLayout()
        logo_opacity_layout.addWidget(QLabel("Opacity:"))
        self.logo_opacity_slider = QSlider(Qt.Horizontal)
        self.logo_opacity_slider.setRange(1, 100)
        self.logo_opacity_slider.setValue(50)
        self.logo_opacity_label = QLabel("50%")
        self.logo_opacity_slider.valueChanged.connect(lambda v: self.logo_opacity_label.setText(f"{v}%"))
        logo_opacity_layout.addWidget(self.logo_opacity_slider, 1)
        logo_opacity_layout.addWidget(self.logo_opacity_label)
        logo_layout.addLayout(logo_opacity_layout)

        logo_size_layout = QHBoxLayout()
        logo_size_layout.addWidget(QLabel("Size:"))
        self.logo_size_slider = QSlider(Qt.Horizontal)
        self.logo_size_slider.setRange(5, 80)
        self.logo_size_slider.setValue(20)
        self.logo_size_label = QLabel("20%")
        self.logo_size_slider.valueChanged.connect(lambda v: self.logo_size_label.setText(f"{v}%"))
        logo_size_layout.addWidget(self.logo_size_slider, 1)
        logo_size_layout.addWidget(self.logo_size_label)
        logo_layout.addLayout(logo_size_layout)

        logo_size_mode_layout = QHBoxLayout()
        self.radio_logo_px = QRadioButton("px cố định")
        self.radio_logo_by_width = QRadioButton("% theo width")
        self.radio_logo_by_max = QRadioButton("% theo cạnh max")
        self.radio_logo_by_width.setChecked(True)
        self.radio_logo_px.toggled.connect(self._on_logo_mode_changed)
        self.radio_logo_by_width.toggled.connect(self._on_logo_mode_changed)
        self.radio_logo_by_max.toggled.connect(self._on_logo_mode_changed)
        logo_size_mode_layout.addWidget(self.radio_logo_px)
        logo_size_mode_layout.addWidget(self.radio_logo_by_width)
        logo_size_mode_layout.addWidget(self.radio_logo_by_max)
        logo_layout.addLayout(logo_size_mode_layout)

        logo_padding_layout = QHBoxLayout()
        logo_padding_layout.addWidget(QLabel("Padding:"))
        self.spin_logo_padding = QSpinBox()
        self.spin_logo_padding.setRange(0, 500)
        self.spin_logo_padding.setValue(10)
        self.spin_logo_padding.setSuffix("px")
        logo_padding_layout.addWidget(self.spin_logo_padding, 1)
        logo_layout.addLayout(logo_padding_layout)

        # Wire toggle and save signals
        self.chk_logo.toggled.connect(self._toggle_logo_controls)
        self.chk_logo.toggled.connect(self._save_logo_config)
        self.chk_logo.toggled.connect(self._update_preview)
        self.combo_logo_position.currentIndexChanged.connect(self._save_logo_config)
        self.combo_logo_position.currentIndexChanged.connect(self._update_preview)
        self.logo_opacity_slider.valueChanged.connect(self._save_logo_config)
        self.logo_opacity_slider.valueChanged.connect(self._update_preview)
        self.logo_size_slider.valueChanged.connect(self._save_logo_config)
        self.logo_size_slider.valueChanged.connect(self._update_preview)
        self.spin_logo_padding.valueChanged.connect(self._save_logo_config)
        self.spin_logo_padding.valueChanged.connect(self._update_preview)

        # Restore logo settings from config
        self.chk_logo.setChecked(self.cfg.get("wm_logo_enabled", False))
        logo_path = self.cfg.get("wm_logo_path", "")
        if logo_path and os.path.isfile(logo_path):
            self.logo_path_edit.setText(logo_path)

        logo_pos_key = safe_config_str(self.cfg, "logo_position", "bottom-right", WM_POS_KEYS)
        logo_pos_idx = WM_POS_KEYS.index(logo_pos_key) if logo_pos_key in WM_POS_KEYS else 8
        self.combo_logo_position.setCurrentIndex(logo_pos_idx)

        self.logo_opacity_slider.setValue(safe_config_int(self.cfg, "logo_opacity", 50, 1, 100))
        self.spin_logo_padding.setValue(safe_config_int(self.cfg, "logo_padding", 10, 0, 500))

        # Logo size mode
        logo_size_mode = self.cfg.get("logo_size_mode", "width")
        if logo_size_mode == "px":
            self.radio_logo_px.setChecked(True)
            self.logo_size_slider.setValue(safe_config_int(self.cfg, "wm_logo_size_pct", 100, 10, 500))
        elif logo_size_mode == "max":
            self.radio_logo_by_max.setChecked(True)
            self.logo_size_slider.setValue(safe_config_int(self.cfg, "wm_logo_size_pct", 20, 5, 80))
        else:
            self.radio_logo_by_width.setChecked(True)
            self.logo_size_slider.setValue(safe_config_int(self.cfg, "wm_logo_size_pct", 20, 5, 80))
        self._on_logo_mode_changed()  # Update slider range based on loaded mode

        # Initial disabled state
        self._toggle_logo_controls(self.chk_logo.isChecked())

        col3.addWidget(logo_group)

        # Text Watermark section
        wm_text_group = QGroupBox("Text Watermark")
        wm_text_layout = QVBoxLayout(wm_text_group)

        self.chk_text_wm = QCheckBox("Text watermark")
        wm_text_layout.addWidget(self.chk_text_wm)

        text_edit_layout = QHBoxLayout()
        text_edit_layout.addWidget(QLabel("Text:"))
        self.wm_text_edit = QLineEdit()
        self.wm_text_edit.setPlaceholderText("Nhập text watermark...")
        text_edit_layout.addWidget(self.wm_text_edit, 1)
        wm_text_layout.addLayout(text_edit_layout)

        font_size_layout = QHBoxLayout()
        font_size_layout.addWidget(QLabel("Font size:"))
        self.spin_font_size = QSpinBox()
        self.spin_font_size.setRange(8, 200)
        self.spin_font_size.setValue(24)
        font_size_layout.addWidget(self.spin_font_size, 1)
        wm_text_layout.addLayout(font_size_layout)

        wm_text_position_layout = QHBoxLayout()
        wm_text_position_layout.addWidget(QLabel("Vị trí:"))
        self.combo_wm_text_position = QComboBox()
        self.combo_wm_text_position.addItems(WATERMARK_POSITIONS)
        self.combo_wm_text_position.setCurrentIndex(8)  # Default: bottom-right
        wm_text_position_layout.addWidget(self.combo_wm_text_position, 1)
        wm_text_layout.addLayout(wm_text_position_layout)

        wm_text_opacity_layout = QHBoxLayout()
        wm_text_opacity_layout.addWidget(QLabel("Opacity:"))
        self.wm_text_opacity_slider = QSlider(Qt.Horizontal)
        self.wm_text_opacity_slider.setRange(1, 100)
        self.wm_text_opacity_slider.setValue(50)
        self.wm_text_opacity_label = QLabel("50%")
        self.wm_text_opacity_slider.valueChanged.connect(lambda v: self.wm_text_opacity_label.setText(f"{v}%"))
        wm_text_opacity_layout.addWidget(self.wm_text_opacity_slider, 1)
        wm_text_opacity_layout.addWidget(self.wm_text_opacity_label)
        wm_text_layout.addLayout(wm_text_opacity_layout)

        wm_text_padding_layout = QHBoxLayout()
        wm_text_padding_layout.addWidget(QLabel("Padding:"))
        self.spin_wm_text_padding = QSpinBox()
        self.spin_wm_text_padding.setRange(0, 500)
        self.spin_wm_text_padding.setValue(10)
        self.spin_wm_text_padding.setSuffix("px")
        wm_text_padding_layout.addWidget(self.spin_wm_text_padding, 1)
        wm_text_layout.addLayout(wm_text_padding_layout)

        wm_rotation_layout = QHBoxLayout()
        wm_rotation_layout.addWidget(QLabel("Rotation:"))
        self.spin_wm_rotation = QSpinBox()
        self.spin_wm_rotation.setRange(0, 360)
        self.spin_wm_rotation.setValue(0)
        self.spin_wm_rotation.setSuffix("°")
        wm_rotation_layout.addWidget(self.spin_wm_rotation, 1)
        wm_text_layout.addLayout(wm_rotation_layout)

        wm_tiling_layout = QHBoxLayout()
        self.chk_wm_tiling = QCheckBox("Lặp watermark (tiling)")
        wm_tiling_layout.addWidget(self.chk_wm_tiling)
        wm_text_layout.addLayout(wm_tiling_layout)

        # Wire toggle and save signals
        self.chk_text_wm.toggled.connect(self._toggle_text_controls)
        self.chk_text_wm.toggled.connect(self._save_text_wm_config)
        self.chk_text_wm.toggled.connect(self._update_preview)
        self.wm_text_edit.textChanged.connect(self._save_text_wm_config)
        self.wm_text_edit.textChanged.connect(self._update_preview)
        self.spin_font_size.valueChanged.connect(self._save_text_wm_config)
        self.spin_font_size.valueChanged.connect(self._update_preview)
        self.combo_wm_text_position.currentIndexChanged.connect(self._save_text_wm_config)
        self.combo_wm_text_position.currentIndexChanged.connect(self._update_preview)
        self.wm_text_opacity_slider.valueChanged.connect(self._save_text_wm_config)
        self.wm_text_opacity_slider.valueChanged.connect(self._update_preview)
        self.spin_wm_text_padding.valueChanged.connect(self._save_text_wm_config)
        self.spin_wm_text_padding.valueChanged.connect(self._update_preview)
        self.spin_wm_rotation.valueChanged.connect(self._save_text_wm_config)
        self.spin_wm_rotation.valueChanged.connect(self._update_preview)
        self.chk_wm_tiling.toggled.connect(self._save_text_wm_config)
        self.chk_wm_tiling.toggled.connect(self._update_preview)

        # Restore text watermark settings from config
        self.chk_text_wm.setChecked(self.cfg.get("wm_text_enabled", False))
        self.wm_text_edit.setText(self.cfg.get("wm_text_content", ""))
        self.spin_font_size.setValue(safe_config_int(self.cfg, "wm_font_size", 24, 8, 200))

        wm_text_pos_key = safe_config_str(self.cfg, "wm_text_position", "bottom-right", WM_POS_KEYS)
        wm_text_pos_idx = WM_POS_KEYS.index(wm_text_pos_key) if wm_text_pos_key in WM_POS_KEYS else 8
        self.combo_wm_text_position.setCurrentIndex(wm_text_pos_idx)

        self.wm_text_opacity_slider.setValue(safe_config_int(self.cfg, "wm_text_opacity", 50, 1, 100))
        self.spin_wm_text_padding.setValue(safe_config_int(self.cfg, "wm_text_padding", 10, 0, 500))
        self.spin_wm_rotation.setValue(safe_config_int(self.cfg, "wm_rotation", 0, 0, 360))
        self.chk_wm_tiling.setChecked(self.cfg.get("wm_tiling", False))

        # Initial disabled state
        self._toggle_text_controls(self.chk_text_wm.isChecked())

        col3.addWidget(wm_text_group)

        col3.addStretch(1)  # Placeholder for text watermark (phase 4)

        layout.addLayout(col3, 1)

    def resizeEvent(self, event):
        """Handle window resize to update preview scaling."""
        super().resizeEvent(event)
        if self.current_img:
            self._update_preview()

    def on_mode_changed(self):
        exact = self.radio_exact.isChecked()
        use_max = self.radio_max.isChecked()
        keep_original = self.radio_keep.isChecked()
        self.exact_widget.setVisible(exact)
        self.max_widget.setVisible(use_max)

    def _save_model(self, name):
        self.cfg["rembg_model"] = name
        save_config(self.cfg)

    def select_files(self):
        start_dir = self.cfg.get("input_dir", "")
        paths, _ = QFileDialog.getOpenFileNames(self, "Chọn ảnh", start_dir, FILTER_STR)
        if paths:
            self.cfg["input_dir"] = os.path.dirname(paths[0])
            save_config(self.cfg)
            self.add_files(paths)

    def select_folder(self):
        start_dir = self.cfg.get("input_dir", "")
        folder = QFileDialog.getExistingDirectory(self, "Chọn folder ảnh", start_dir)
        if folder:
            self.cfg["input_dir"] = folder
            save_config(self.cfg)
            paths = [
                os.path.join(folder, f)
                for f in os.listdir(folder)
                if os.path.splitext(f)[1].lower() in SUPPORTED_EXTS
            ]
            self.add_files(paths)

    def select_output_dir(self):
        start_dir = self.cfg.get("output_dir", "")
        folder = QFileDialog.getExistingDirectory(self, "Chọn folder output", start_dir)
        if folder:
            self.output_edit.setText(folder)
            self.cfg["output_dir"] = folder
            save_config(self.cfg)

    def clear_output_dir(self):
        self.output_edit.setText("")
        self.cfg.pop("output_dir", None)
        save_config(self.cfg)

    def add_files(self, paths):
        existing = set(self.files)
        for p in paths:
            if p not in existing:
                self.files.append(p)
                self.file_list.addItem(os.path.basename(p))

    def clear_files(self):
        self.files.clear()
        self.file_list.clear()
        self.preview_label.setPixmap(QPixmap())
        self.preview_label.setText("Chưa chọn ảnh")
        self.info_label.setText("")
        self.current_img = None

    def delete_selected(self):
        """Delete selected items from file list."""
        selected = self.file_list.selectedItems()
        if not selected:
            return
        for item in selected:
            row = self.file_list.row(item)
            self.file_list.takeItem(row)
            if 0 <= row < len(self.files):
                self.files.pop(row)
        # Clear preview if no files left
        if not self.files:
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText("Chưa chọn ảnh")
            self.info_label.setText("")
            self.current_img = None

    def on_file_selected(self, row):
        if row < 0 or row >= len(self.files):
            return
        path = self.files[row]
        try:
            self.current_img = Image.open(path)
            w, h = self.current_img.size
            self.aspect_ratio = w / h
            fsize = os.path.getsize(path)
            ext = os.path.splitext(path)[1].upper()
            self.info_label.setText(f"Gốc: {w}x{h} px | {fmt_size(fsize)} | {ext}")

            self.updating_spinbox = True
            self.spin_w.setValue(w)
            self.spin_h.setValue(h)
            self.updating_spinbox = False

            self._update_preview()
        except Exception as e:
            self.preview_label.setText(f"Lỗi: {e}")

    def _update_preview(self):
        """Update preview with watermark overlay."""
        if not self.current_img:
            return

        try:
            # Create preview with watermark
            preview_img = self.current_img.copy().convert("RGBA")

            # Apply watermark if enabled
            logo_img = None
            if self.chk_logo.isChecked() and self.logo_path_edit.text().strip():
                logo_path = self.logo_path_edit.text().strip()
                if os.path.isfile(logo_path):
                    try:
                        logo_img = Image.open(logo_path).convert("RGBA")
                    except:
                        pass

            text = None
            if self.chk_text_wm.isChecked() and self.wm_text_edit.text().strip():
                text = self.wm_text_edit.text().strip()

            if logo_img or text:
                logo_pos_idx = self.combo_logo_position.currentIndex()
                logo_position = WM_POS_KEYS[logo_pos_idx] if 0 <= logo_pos_idx < len(WM_POS_KEYS) else "bottom-right"

                text_pos_idx = self.combo_wm_text_position.currentIndex()
                text_position = WM_POS_KEYS[text_pos_idx] if 0 <= text_pos_idx < len(WM_POS_KEYS) else "bottom-right"

                preview_img = apply_watermark(
                    preview_img, logo_img=logo_img, text=text,
                    logo_position=logo_position,
                    logo_size_pct=self.logo_size_slider.value(),
                    logo_opacity_pct=self.logo_opacity_slider.value(),
                    logo_padding=self.spin_logo_padding.value(),
                    logo_size_mode=self.cfg.get("logo_size_mode", "width"),
                    text_position=text_position,
                    font_size=self.spin_font_size.value(),
                    text_opacity_pct=self.wm_text_opacity_slider.value(),
                    text_padding=self.spin_wm_text_padding.value(),
                    text_rotation=self.spin_wm_rotation.value(),
                    text_tiling=self.chk_wm_tiling.isChecked(),
                )

            # Scale to fit QLabel size while keeping aspect ratio
            label_width = self.preview_label.width()
            label_height = self.preview_label.height()
            pixmap = pil_to_qpixmap(preview_img, max(label_width, label_height))

            # Scale pixmap to fit label
            pixmap = pixmap.scaled(
                label_width, label_height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

            self.preview_label.setPixmap(pixmap)
            self.preview_label.setText("")
        except Exception as e:
            print(f"[WARN] Preview update failed: {e}")

    def on_width_changed(self, val):
        if self.updating_spinbox or not self.lock_ratio.isChecked():
            return
        self.updating_spinbox = True
        self.spin_h.setValue(max(1, round(val / self.aspect_ratio)))
        self.updating_spinbox = False

    def on_height_changed(self, val):
        if self.updating_spinbox or not self.lock_ratio.isChecked():
            return
        self.updating_spinbox = True
        self.spin_w.setValue(max(1, round(val * self.aspect_ratio)))
        self.updating_spinbox = False

    def get_output_dir(self):
        custom = self.output_edit.text().strip()
        if custom and os.path.isdir(custom):
            return custom
        return None

    def get_selected_files(self):
        selected = self.file_list.selectedItems()
        if selected:
            indices = [self.file_list.row(item) for item in selected]
            return [self.files[i] for i in indices]
        return list(self.files)

    def _toggle_logo_controls(self, enabled):
        self.logo_path_edit.setEnabled(enabled)
        self.btn_logo_browse.setEnabled(enabled)
        self.btn_logo_clear.setEnabled(enabled)
        self.combo_logo_position.setEnabled(enabled)
        self.logo_opacity_slider.setEnabled(enabled)
        self.logo_size_slider.setEnabled(enabled)
        self.spin_logo_padding.setEnabled(enabled)

    def _on_logo_mode_changed(self):
        """Update logo size slider range/label based on mode."""
        if self.radio_logo_px.isChecked():
            self.logo_size_slider.setRange(10, 500)
            self.logo_size_slider.setValue(min(self.logo_size_slider.value() * 5, 500))
            self.logo_size_label.setText(f"{self.logo_size_slider.value()}px")
            self.logo_size_slider.valueChanged.disconnect()
            self.logo_size_slider.valueChanged.connect(lambda v: self.logo_size_label.setText(f"{v}px"))
        else:
            self.logo_size_slider.setRange(5, 80)
            self.logo_size_slider.setValue(min(max(self.logo_size_slider.value() // 5, 5), 80))
            self.logo_size_label.setText(f"{self.logo_size_slider.value()}%")
            self.logo_size_slider.valueChanged.disconnect()
            self.logo_size_slider.valueChanged.connect(lambda v: self.logo_size_label.setText(f"{v}%"))
        self.logo_size_slider.valueChanged.connect(self._save_logo_config)
        self.logo_size_slider.valueChanged.connect(self._update_preview)
        self._save_logo_config()
        self._update_preview()

    def _select_logo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn logo", "",
            "Images (*.png *.webp *.jpg *.jpeg)"
        )
        if path:
            # Validate path security
            if not os.path.isfile(path):
                QMessageBox.warning(self, "Lỗi", "File không tồn tại!")
                return
            # Check file size (max 10MB for logos)
            try:
                file_size = os.path.getsize(path)
                if file_size > 10 * 1024 * 1024:
                    QMessageBox.warning(self, "Lỗi", "Logo quá lớn! Tối đa 10MB.")
                    return
            except OSError:
                QMessageBox.warning(self, "Lỗi", "Không thể đọc file!")
                return
            self.logo_path_edit.setText(path)
            self._save_logo_config()

    def _clear_logo(self):
        self.logo_path_edit.setText("")
        self._save_logo_config()

    def _save_logo_config(self):
        self.cfg["wm_logo_enabled"] = self.chk_logo.isChecked()
        self.cfg["wm_logo_path"] = self.logo_path_edit.text()
        self.cfg["logo_position"] = WM_POS_KEYS[self.combo_logo_position.currentIndex()]
        self.cfg["logo_opacity"] = self.logo_opacity_slider.value()
        self.cfg["wm_logo_size_pct"] = self.logo_size_slider.value()
        if self.radio_logo_px.isChecked():
            self.cfg["logo_size_mode"] = "px"
        elif self.radio_logo_by_max.isChecked():
            self.cfg["logo_size_mode"] = "max"
        else:
            self.cfg["logo_size_mode"] = "width"
        self.cfg["logo_padding"] = self.spin_logo_padding.value()
        save_config(self.cfg)

    def _toggle_text_controls(self, enabled):
        self.wm_text_edit.setEnabled(enabled)
        self.spin_font_size.setEnabled(enabled)
        self.combo_wm_text_position.setEnabled(enabled)
        self.wm_text_opacity_slider.setEnabled(enabled)
        self.spin_wm_text_padding.setEnabled(enabled)
        self.spin_wm_rotation.setEnabled(enabled)
        self.chk_wm_tiling.setEnabled(enabled)

    def _save_auto_crop_config(self):
        self.cfg["auto_crop_white"] = self.chk_auto_crop_white.isChecked()
        self.cfg["white_tolerance"] = self.spin_white_tolerance.value()
        save_config(self.cfg)

    def _save_text_wm_config(self):
        self.cfg["wm_text_enabled"] = self.chk_text_wm.isChecked()
        self.cfg["wm_text_content"] = self.wm_text_edit.text()
        self.cfg["wm_font_size"] = self.spin_font_size.value()
        self.cfg["wm_text_position"] = WM_POS_KEYS[self.combo_wm_text_position.currentIndex()]
        self.cfg["wm_text_opacity"] = self.wm_text_opacity_slider.value()
        self.cfg["wm_text_padding"] = self.spin_wm_text_padding.value()
        self.cfg["wm_rotation"] = self.spin_wm_rotation.value()
        self.cfg["wm_tiling"] = self.chk_wm_tiling.isChecked()
        save_config(self.cfg)

    def start_resize(self):
        # Guard against concurrent workers
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "Lỗi", "Đang xử lý! Vui lòng đợi.")
            return

        files = self.get_selected_files()
        if not files:
            QMessageBox.warning(self, "Lỗi", "Chưa chọn file nào!")
            return

        output_dir = self.get_output_dir()
        same_as_input = output_dir is None
        if same_as_input:
            output_dir = ""

        use_max = self.radio_max.isChecked()
        keep_original = self.radio_keep.isChecked()

        rembg_fn = None
        if self.chk_rembg.isChecked():
            if self._rembg_remove:
                rembg_fn = self._rembg_remove
            else:
                QMessageBox.critical(self, "Lỗi",
                    "rembg không khả dụng.\n"
                    "Chạy: pip install \"rembg[gpu]\" hoặc \"rembg[cpu]\"")
                return

        # Gather watermark params
        wm_logo_path = None
        if self.chk_logo.isChecked() and self.logo_path_edit.text().strip():
            wm_logo_path = self.logo_path_edit.text().strip()

        logo_pos_idx = self.combo_logo_position.currentIndex()
        logo_position = WM_POS_KEYS[logo_pos_idx] if 0 <= logo_pos_idx < len(WM_POS_KEYS) else "bottom-right"

        wm_text = None
        if self.chk_text_wm.isChecked() and self.wm_text_edit.text().strip():
            wm_text = self.wm_text_edit.text().strip()

        text_pos_idx = self.combo_wm_text_position.currentIndex()
        text_position = WM_POS_KEYS[text_pos_idx] if 0 <= text_pos_idx < len(WM_POS_KEYS) else "bottom-right"

        # Get output format
        output_format = self.combo_format.currentText().lower()

        self.btn_resize.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setMaximum(len(files))
        self.progress.setValue(0)

        self.worker = ResizeWorker(
            files, self.spin_w.value(), self.spin_h.value(),
            self.quality_slider.value(), output_dir, same_as_input,
            use_max, self.spin_max.value(), rembg_fn,
            self.combo_model.currentText(), self.spin_crop.value(),
            self.chk_auto_crop_white.isChecked(), self.spin_white_tolerance.value(),
            # Output format and size mode
            output_format=output_format,
            keep_original=keep_original,
            # Watermark params
            wm_logo_path=wm_logo_path,
            logo_position=logo_position,
            logo_size_pct=self.logo_size_slider.value(),
            logo_opacity_pct=self.logo_opacity_slider.value(),
            logo_padding=self.spin_logo_padding.value(),
            logo_size_mode='px' if self.radio_logo_px.isChecked() else ('max' if self.radio_logo_by_max.isChecked() else 'width'),
            wm_text=wm_text,
            text_position=text_position,
            font_size=self.spin_font_size.value(),
            text_opacity_pct=self.wm_text_opacity_slider.value(),
            text_padding=self.spin_wm_text_padding.value(),
            text_rotation=self.spin_wm_rotation.value(),
            text_tiling=self.chk_wm_tiling.isChecked(),
        )
        self.worker.progress.connect(self.progress.setValue)
        self.worker.finished.connect(self.on_resize_done)
        self.worker.start()

    def closeEvent(self, event):
        """Handle window close - stop worker if running."""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(3000)  # Wait up to 3 seconds
            if self.worker.isRunning():
                self.worker.terminate()
        event.accept()

    def on_resize_done(self, ok, fail, total_before, total_after):
        self.btn_resize.setEnabled(True)
        self.progress.setVisible(False)
        reduction = (1 - total_after / total_before) * 100 if total_before else 0
        msg = f"Hoàn tất! {ok} thành công\n"
        msg += f"Trước: {fmt_size(total_before)} → Sau: {fmt_size(total_after)}\n"
        msg += f"Giảm: {reduction:.1f}%"
        if fail:
            msg += f"\n{fail} file lỗi"
        QMessageBox.information(self, "Kết quả", msg)


if __name__ == "__main__":
    # Fix DLL search path for onnxruntime on Windows
    import os, site
    ort_dll_dir = os.path.join(site.getsitepackages()[0], "onnxruntime", "capi")
    if os.path.isdir(ort_dll_dir):
        os.environ["PATH"] = ort_dll_dir + os.pathsep + os.environ.get("PATH", "")
        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(ort_dll_dir)

    _rembg_remove = None
    try:
        import onnxruntime
        print(f"[INFO] onnxruntime {onnxruntime.__version__}")
        from rembg import remove as _rembg_remove
        print("[INFO] rembg pre-loaded OK")
    except (Exception, SystemExit) as e:
        print(f"[WARN] rembg not available: {e}")
    app = QApplication(sys.argv)
    window = MainWindow()
    window._rembg_remove = _rembg_remove
    window.show()
    sys.exit(app.exec_())
