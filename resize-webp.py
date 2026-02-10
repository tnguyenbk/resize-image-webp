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
    except Exception:
        pass


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


class ResizeWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(int, int, int, int)

    def __init__(self, files, target_w, target_h, quality, output_dir,
                 same_as_input, use_max_size, max_size, rembg_fn=None,
                 model_name="u2net", crop_pct=0):
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

    def run(self):
        session = None
        if self.rembg_fn:
            from rembg import new_session
            print(f"[INFO] Loading model: {self.model_name}...")
            session = new_session(self.model_name)
        ok, fail, total_before, total_after = 0, 0, 0, 0
        for i, path in enumerate(self.files):
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

        self.btn_resize.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setMaximum(len(files))
        self.progress.setValue(0)

        self.worker = ResizeWorker(
            files, self.spin_w.value(), self.spin_h.value(),
            self.quality_slider.value(), output_dir, same_as_input,
            use_max, self.spin_max.value(), rembg_fn,
            self.combo_model.currentText(), self.spin_crop.value(),
        )
        self.worker.progress.connect(self.progress.setValue)
        self.worker.finished.connect(self.on_resize_done)
        self.worker.start()

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
