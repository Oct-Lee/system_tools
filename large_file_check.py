import os
import shutil
from PySide2.QtWidgets import (QWidget, QVBoxLayout, QLabel, QTextEdit, QComboBox,
                               QLineEdit, QPushButton, QProgressBar, QMessageBox,
                               QHBoxLayout, QSizePolicy)
from PySide2.QtGui import QFont, QIntValidator
from PySide2.QtCore import QThread, Signal, QObject, Qt
from localization import _

def format_size(size_bytes):
    if size_bytes < 0 or not isinstance(size_bytes, (int, float)):
        return "Unknown Size"

    size = float(size_bytes)
    if size >= 1024 ** 3:  # GB
        return f"{size / (1024 ** 3):.2f} GB"
    elif size >= 1024 ** 2:  # MB
        return f"{size / (1024 ** 2):.2f} MB"
    else:
        return f"{size / (1024 ** 2):.2f} MB"

class FileScanner(QObject):
    update_progress = Signal(int)
    file_found = Signal(str, object)
    finished = Signal(bool)
    error_occurred = Signal(str)

    def __init__(self, directory, min_size_bytes):
        super().__init__()
        self.directory = directory
        self.min_size_bytes = min_size_bytes
        self.exclude_dirs = {'proc', 'sys', 'dev', 'run', 'tmp', 'var', 'lib', 'snap', 'lost+found'}
        self._is_running = True

    def stop(self):
        self._is_running = False

    def run(self):
        processed_files = 0
        try:
            for root, dirs, files in os.walk(self.directory, topdown=True):
                dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
                if not self._is_running:
                    return
                for file in files:
                    if not self._is_running:
                        return
                    processed_files += 1
                    self.update_progress.emit(processed_files)
                    try:
                        file_path = os.path.join(root, file)
                        if os.path.isfile(file_path):
                            size = os.stat(file_path).st_size
                            if size >= self.min_size_bytes:
                                self.file_found.emit(file_path, size)
                    except (FileNotFoundError, PermissionError) as e:
                        self.error_occurred.emit(_("Unable to access file {file}: {e}").format(file=file_path, e=str(e)))
                    except Exception as e:
                        self.error_occurred.emit(_("Scan error: {e}").format(e=str(e)))
            if self._is_running:
                self.finished.emit(True)
        except Exception:
            if self._is_running:
                self.finished.emit(True)

class LargeFileCheck(QWidget):
    def __init__(self):
        super().__init__()
        self.current_language = os.environ.get('LANG', 'en_US').split('.')[0]
        self.scanner_thread = None
        self.scanner = None
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)

        control_layout = QHBoxLayout()
        control_layout.setSpacing(10)
        control_layout.setAlignment(Qt.AlignLeft)

        self.directory_selector = QComboBox()
        self.directory_selector.addItems(['/home', '/'])
        self.directory_selector.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.directory_selector.setMinimumWidth(100)
        control_layout.addWidget(self.directory_selector)

        size_group = QHBoxLayout()
        size_group.setSpacing(5)

        self.size_input = QLineEdit()
        self.size_input.setPlaceholderText(_("Size"))
        self.size_input.setMinimumWidth(100)
        self.size_input.setValidator(QIntValidator(1, 9999))
        self.size_input.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        size_group.addWidget(self.size_input)

        self.size_unit = QComboBox()
        self.size_unit.addItems(["GB", "MB"])
        self.size_unit.setMinimumWidth(80)
        self.size_unit.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        size_group.addWidget(self.size_unit)

        control_layout.addLayout(size_group)

        self.check_button = QPushButton(_("Start detection"))
        self.check_button.setMinimumWidth(120)
        self.check_button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.check_button.clicked.connect(self.toggle_detection)
        control_layout.addWidget(self.check_button)

        main_layout.addLayout(control_layout)

        self.large_files_output_area = QTextEdit()
        self.large_files_output_area.setReadOnly(True)
        font = QFont("Courier New", 10)
        self.large_files_output_area.setFont(font)
        main_layout.addWidget(self.large_files_output_area, stretch=1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.hide()
        main_layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("Processed 0 files")
        main_layout.addWidget(self.progress_label)

        self.setLayout(main_layout)
        self.setMinimumSize(800, 600)

    def get_disk_usage(self, path):
        try:
            return shutil.disk_usage(path)
        except Exception as e:
            self.large_files_output_area.append(_("[Error] Failed to get disk usage: {e}").format(e=str(e)))
            return None

    def parse_size_input(self):
        try:
            value = int(self.size_input.text())
            unit = self.size_unit.currentText().upper()
            return value * (1024 ** (3 if unit == "GB" else 2))
        except ValueError:
            return None

    def toggle_detection(self):
        if self.scanner_thread and self.scanner_thread.isRunning():
            self.stop_scan()
        else:
            self.start_detection()

    def start_detection(self):
        if not self.size_input.text().strip():
            QMessageBox.warning(self, _("Input Required"), _("Enter minimum file size (MB) default 1000 MB"))
            return

        min_size_bytes = self.parse_size_input()
        if not min_size_bytes:
            QMessageBox.warning(self, _("Invalid Size"), _("Please enter a valid number"))
            return

        unit = self.size_unit.currentText().upper()
        value = int(self.size_input.text())
        if unit == "MB" and value <= 1024:
            QMessageBox.warning(self, _("Invalid Size"), _("MB unit must be greater than 1024 MB (i.e., 1GB)"))
            return
        elif unit == "GB" and value < 1:
            QMessageBox.warning(self, _("Invalid Size"), _("GB unit must be greater than 1 GB"))
            return

        if min_size_bytes < 1024 ** 3:
            QMessageBox.warning(self, _("Invalid Size"), _("Minimum size must be ≥1GB"))
            return

        target_path = self.directory_selector.currentText()
        usage = self.get_disk_usage(target_path)
        if not usage:
            return

        self.large_files_output_area.clear()
        self.show_parameters(target_path, usage, min_size_bytes)

        if min_size_bytes > usage.free:
            self.large_files_output_area.append(
                _("[Warning] Threshold ({threshold}) exceeds free space ({free})").format(
                    threshold=format_size(min_size_bytes),
                    free=format_size(usage.free)
                )
            )
            return

        self.cleanup_scan()
        self.prepare_scan_ui()

        self.scanner_thread = QThread()
        self.scanner = FileScanner(target_path, min_size_bytes)
        self.scanner.moveToThread(self.scanner_thread)

        self.scanner.update_progress.connect(self.update_progress)
        self.scanner.file_found.connect(self.add_file_result)
        self.scanner.error_occurred.connect(self.add_error_message)
        self.scanner.finished.connect(self.on_scan_finished)

        self.scanner_thread.started.connect(self.scanner.run)
        self.scanner_thread.start()

    def show_parameters(self, path, usage, min_size):
        lines = [
            _("[Parameters]"),
            _("Target Directory: {path}").format(path=path),
            _("Minimum Size: {size} {unit}").format(size=self.size_input.text(), unit=self.size_unit.currentText()),
            _("Total Space: {total}").format(total=format_size(usage.total)),
            _("Used Space: {used}").format(used=format_size(usage.used)),
            _("Free Space: {free}").format(free=format_size(usage.free))
        ]
        translated_text = "\n".join(lines)
        self.large_files_output_area.append(translated_text)

    def prepare_scan_ui(self):
        self.large_files_output_area.append(_("Detecting large files..."))
        self.check_button.setText(_("Stop detection"))
        self.progress_bar.show()
        self.progress_label.setText("Processed 0 files")

    def stop_scan(self):
        if self.scanner:
            self.scanner.stop()
        self.check_button.setText(_("Start detection"))
        self.check_button.setEnabled(True)
        self.progress_bar.hide()
        self.progress_label.setText("Processed 0 files")
        self.large_files_output_area.clear()
        self.large_files_output_area.append(_("Stopped detection"))
        self.disconnect_signals()
        self.cleanup_scan()

    def cleanup_scan(self):
        if self.scanner_thread:
            self.scanner_thread.quit()
            self.scanner_thread.wait()
            self.scanner_thread.deleteLater()
            self.scanner_thread = None
        if self.scanner:
            self.scanner.deleteLater()
            self.scanner = None

    def disconnect_signals(self):
        if self.scanner:
            try:
                self.scanner.update_progress.disconnect(self.update_progress)
                self.scanner.file_found.disconnect(self.add_file_result)
                self.scanner.error_occurred.disconnect(self.add_error_message)
                self.scanner.finished.disconnect(self.on_scan_finished)
            except TypeError:
                pass

    def update_progress(self, count):
        if self.scanner and self.scanner._is_running:
            self.progress_label.setText(_("{count} files processed").format(count=count))

    def add_file_result(self, path, size_bytes):
        size_mb = size_bytes / (1024 ** 2)
        self.large_files_output_area.append(
            _("{file_path} (Size: {size:.2f} MB)").format(file_path=path, size=size_mb)
        )

    def add_error_message(self, msg):
        self.large_files_output_area.append(_("[Error] {msg}").format(msg=msg))

    def on_scan_finished(self, completed):
        if completed:
            self.cleanup_scan()
            self.progress_bar.hide()
            self.check_button.setText(_("Start detection"))
            self.check_button.setEnabled(True)
            self.progress_label.setText("Processed 0 files")
            if not self.large_files_output_area.toPlainText().strip():
                self.large_files_output_area.append(_("No large files found."))
            else:
                self.large_files_output_area.append(_("\nLarge files found."))
