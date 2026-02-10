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
                    position='bottom-right', logo_size_pct=20,
                    font_size=24, opacity_pct=50, padding=10):
    """Apply logo and/or text watermark to RGBA image. Returns new image."""
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
    logo_w = logo_h = 0
    logo_resized = None
    if logo_img:
        # Resize logo proportionally
        logo_w = max(1, int(img.width * logo_size_pct / 100))
        ratio = logo_w / logo_img.width
        logo_h = max(1, int(logo_img.height * ratio))
        logo_resized = logo_img.resize((logo_w, logo_h), Image.LANCZOS)
        # Adjust opacity
        logo_resized = _adjust_opacity(logo_resized, opacity_pct)

    # Process text
    txt_w = txt_h = 0
    txt_layer = None
    font = None
    if text:
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

    # Composite watermarks
    if logo_resized and text:
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
    elif logo_resized:
        ax, ay = _calc_anchor(logo_w, logo_h, img.width, img.height, position, padding)
        img.paste(logo_resized, (ax, ay), logo_resized)
    elif text:
        ax, ay = _calc_anchor(txt_w, txt_h, img.width, img.height, position, padding)
        draw = ImageDraw.Draw(txt_layer)
        draw.text((ax, ay), text, font=font, fill=(255, 255, 255, 255))
        txt_layer = _adjust_opacity(txt_layer, opacity_pct)
        img = Image.alpha_composite(img, txt_layer)

    return img


class ResizeWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(int, int, int, int)

    def __init__(self, files, target_w, target_h, quality, output_dir,
                 same_as_input, use_max_size, max_size, rembg_fn=None,
                 model_name="u2net", crop_pct=0,
                 # Watermark params
                 wm_logo_path=None, wm_text=None,
                 wm_position='bottom-right', wm_logo_size_pct=20,
                 wm_font_size=24, wm_opacity_pct=50, wm_padding=10):
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
        self.wm_logo_path = wm_logo_path
        self.wm_text = wm_text
        self.wm_position = wm_position
        self.wm_logo_size_pct = wm_logo_size_pct
        self.wm_font_size = wm_font_size
        self.wm_opacity_pct = wm_opacity_pct
        self.wm_padding = wm_padding
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
                total_before += os.path.getsize(path)
                img = Image.open(path).convert("RGBA")
                if self.rembg_fn and session:
                    img = self.rembg_fn(img, session=session)
                if self.crop_pct > 0:
                    cw, ch = img.size
                    dx = int(cw * self.crop_pct / 200)
                    dy = int(ch * self.crop_pct / 200)
                    img = img.crop((dx, dy, cw - dx, ch - dy))

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

                w, h = calc_resize(img.width, img.height,
                                   self.target_w, self.target_h,
                                   self.use_max_size, self.max_size)
                resized = img.resize((w, h), Image.LANCZOS)
                basename = os.path.splitext(os.path.basename(path))[0]
                if self.same_as_input:
                    out_dir = os.path.dirname(path)
                    out_path = os.path.join(out_dir, f"{basename}_resized.webp")
                else:
                    out_path = os.path.join(self.output_dir, f"{basename}.webp")
                # Avoid overwriting existing files
                if os.path.exists(out_path):
                    n = 2
                    while True:
                        candidate = os.path.join(
                            os.path.dirname(out_path),
                            f"{basename} ({n}).webp"
                        )
                        if not os.path.exists(candidate):
                            out_path = candidate
                            break
                        n += 1
                resized.save(out_path, "WEBP", quality=self.quality)
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
        self.setMinimumSize(850, 600)
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

        # --- Left panel ---
        left = QVBoxLayout()
        btn_row = QHBoxLayout()
        btn_files = QPushButton("Chọn Files")
        btn_folder = QPushButton("Chọn Folder")
        btn_clear = QPushButton("Xóa hết")
        btn_files.clicked.connect(self.select_files)
        btn_folder.clicked.connect(self.select_folder)
        btn_clear.clicked.connect(self.clear_files)
        btn_row.addWidget(btn_files)
        btn_row.addWidget(btn_folder)
        btn_row.addWidget(btn_clear)
        left.addLayout(btn_row)

        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.file_list.currentRowChanged.connect(self.on_file_selected)
        left.addWidget(self.file_list)

        self.select_info = QLabel("Ctrl/Shift+click để chọn nhiều. Không chọn = tất cả.")
        self.select_info.setStyleSheet("color: #666; font-size: 11px;")
        left.addWidget(self.select_info)

        layout.addLayout(left, 1)

        # --- Right panel ---
        right = QVBoxLayout()

        self.preview_label = QLabel("Chưa chọn ảnh")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(400, 280)
        self.preview_label.setStyleSheet("border: 1px solid #ccc; background: #f9f9f9;")
        right.addWidget(self.preview_label, 1)

        self.info_label = QLabel("")
        right.addWidget(self.info_label)

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
        right.addWidget(out_group)

        # Size controls
        size_group = QGroupBox("Kích thước")
        size_layout = QVBoxLayout(size_group)

        # Mode: exact vs max
        self.radio_exact = QRadioButton("Chính xác (W x H)")
        self.radio_max = QRadioButton("Theo max (giữ tỷ lệ từng ảnh)")
        self.radio_exact.setChecked(True)
        self.radio_exact.toggled.connect(self.on_mode_changed)
        size_layout.addWidget(self.radio_exact)
        size_layout.addWidget(self.radio_max)

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

        right.addWidget(size_group)

        # Crop border
        crop_layout = QHBoxLayout()
        crop_layout.addWidget(QLabel("Crop viền (%):"))
        self.spin_crop = QSpinBox()
        self.spin_crop.setRange(0, 80)
        self.spin_crop.setValue(0)
        self.spin_crop.setSuffix("%")
        crop_layout.addWidget(self.spin_crop)
        right.addLayout(crop_layout)

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
        right.addLayout(q_layout)

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
        right.addLayout(rembg_layout)

        # Watermark group
        wm_group = QGroupBox("Watermark")
        wm_layout = QVBoxLayout(wm_group)

        # Logo controls
        self.chk_logo = QCheckBox("Logo anh")
        wm_layout.addWidget(self.chk_logo)

        logo_path_layout = QHBoxLayout()
        self.logo_path_edit = QLineEdit()
        self.logo_path_edit.setReadOnly(True)
        self.logo_path_edit.setPlaceholderText("Chọn file logo...")
        self.btn_logo_browse = QPushButton("Chon...")
        self.btn_logo_clear = QPushButton("Clear")
        self.btn_logo_browse.clicked.connect(self._select_logo)
        self.btn_logo_clear.clicked.connect(self._clear_logo)
        logo_path_layout.addWidget(self.logo_path_edit, 1)
        logo_path_layout.addWidget(self.btn_logo_browse)
        logo_path_layout.addWidget(self.btn_logo_clear)
        wm_layout.addLayout(logo_path_layout)

        logo_size_layout = QHBoxLayout()
        logo_size_layout.addWidget(QLabel("Size:"))
        self.logo_size_slider = QSlider(Qt.Horizontal)
        self.logo_size_slider.setRange(5, 80)
        self.logo_size_slider.setValue(20)
        self.logo_size_label = QLabel("20%")
        self.logo_size_slider.valueChanged.connect(lambda v: self.logo_size_label.setText(f"{v}%"))
        logo_size_layout.addWidget(self.logo_size_slider, 1)
        logo_size_layout.addWidget(self.logo_size_label)
        wm_layout.addLayout(logo_size_layout)

        # Text watermark controls
        self.chk_text_wm = QCheckBox("Text watermark")
        wm_layout.addWidget(self.chk_text_wm)

        text_edit_layout = QHBoxLayout()
        text_edit_layout.addWidget(QLabel("Text:"))
        self.wm_text_edit = QLineEdit()
        self.wm_text_edit.setPlaceholderText("Nhap text watermark...")
        text_edit_layout.addWidget(self.wm_text_edit, 1)
        wm_layout.addLayout(text_edit_layout)

        font_size_layout = QHBoxLayout()
        font_size_layout.addWidget(QLabel("Font size:"))
        self.spin_font_size = QSpinBox()
        self.spin_font_size.setRange(8, 200)
        self.spin_font_size.setValue(24)
        font_size_layout.addWidget(self.spin_font_size, 1)
        wm_layout.addLayout(font_size_layout)

        # Shared controls
        position_layout = QHBoxLayout()
        position_layout.addWidget(QLabel("Vi tri:"))
        self.combo_wm_position = QComboBox()
        self.combo_wm_position.addItems(WATERMARK_POSITIONS)
        self.combo_wm_position.setCurrentIndex(8)  # Default: bottom-right
        position_layout.addWidget(self.combo_wm_position, 1)
        wm_layout.addLayout(position_layout)

        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel("Opacity:"))
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(1, 100)
        self.opacity_slider.setValue(50)
        self.opacity_label = QLabel("50%")
        self.opacity_slider.valueChanged.connect(lambda v: self.opacity_label.setText(f"{v}%"))
        opacity_layout.addWidget(self.opacity_slider, 1)
        opacity_layout.addWidget(self.opacity_label)
        wm_layout.addLayout(opacity_layout)

        padding_layout = QHBoxLayout()
        padding_layout.addWidget(QLabel("Padding:"))
        self.spin_wm_padding = QSpinBox()
        self.spin_wm_padding.setRange(0, 500)
        self.spin_wm_padding.setValue(10)
        self.spin_wm_padding.setSuffix("px")
        padding_layout.addWidget(self.spin_wm_padding, 1)
        wm_layout.addLayout(padding_layout)

        # Wire toggle signals
        self.chk_logo.toggled.connect(self._toggle_logo_controls)
        self.chk_text_wm.toggled.connect(self._toggle_text_controls)

        # Connect change signals to save config
        self.chk_logo.toggled.connect(self._save_wm_config)
        self.logo_size_slider.valueChanged.connect(self._save_wm_config)
        self.chk_text_wm.toggled.connect(self._save_wm_config)
        self.wm_text_edit.textChanged.connect(self._save_wm_config)
        self.spin_font_size.valueChanged.connect(self._save_wm_config)
        self.combo_wm_position.currentIndexChanged.connect(self._save_wm_config)
        self.opacity_slider.valueChanged.connect(self._save_wm_config)
        self.spin_wm_padding.valueChanged.connect(self._save_wm_config)

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

        # Initial disabled state (after config load)
        self._toggle_logo_controls(self.chk_logo.isChecked())
        self._toggle_text_controls(self.chk_text_wm.isChecked())

        right.addWidget(wm_group)

        # Progress + button
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        right.addWidget(self.progress)

        self.btn_resize = QPushButton("Convert to WebP")
        self.btn_resize.setStyleSheet("padding: 8px; font-weight: bold;")
        self.btn_resize.clicked.connect(self.start_resize)
        right.addWidget(self.btn_resize)

        layout.addLayout(right, 1)

    def on_mode_changed(self):
        exact = self.radio_exact.isChecked()
        self.exact_widget.setVisible(exact)
        self.max_widget.setVisible(not exact)

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
            pixmap = pil_to_qpixmap(self.current_img.copy())
            self.preview_label.setPixmap(pixmap)
            self.preview_label.setText("")
            self.updating_spinbox = True
            self.spin_w.setValue(w)
            self.spin_h.setValue(h)
            self.updating_spinbox = False
        except Exception as e:
            self.preview_label.setText(f"Lỗi: {e}")

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
            self._save_wm_config()

    def _clear_logo(self):
        self.logo_path_edit.setText("")
        self._save_wm_config()

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

    def start_resize(self):
        files = self.get_selected_files()
        if not files:
            QMessageBox.warning(self, "Lỗi", "Chưa chọn file nào!")
            return

        output_dir = self.get_output_dir()
        same_as_input = output_dir is None
        if same_as_input:
            output_dir = ""

        use_max = self.radio_max.isChecked()

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
        wm_text = None
        if self.chk_logo.isChecked() and self.logo_path_edit.text().strip():
            wm_logo_path = self.logo_path_edit.text().strip()
        if self.chk_text_wm.isChecked() and self.wm_text_edit.text().strip():
            wm_text = self.wm_text_edit.text().strip()

        wm_pos_idx = self.combo_wm_position.currentIndex()
        wm_position = WM_POS_KEYS[wm_pos_idx] if 0 <= wm_pos_idx < len(WM_POS_KEYS) else "bottom-right"

        self.btn_resize.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setMaximum(len(files))
        self.progress.setValue(0)

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
