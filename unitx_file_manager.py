import os
import sys
import subprocess
import tempfile
import re
import stat
import logging
from localization import setup_locale, _
from PySide2.QtWidgets import (
    QApplication, QMainWindow, QTreeView, QFileSystemModel, QPlainTextEdit,
    QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QMessageBox, QDialog,
    QLineEdit, QLabel, QDialogButtonBox, QSpinBox, QMenu, QInputDialog,
    QComboBox, QCheckBox, QListWidget, QTabWidget, QStatusBar, QTextEdit
)
from PySide2.QtCore import QDir, Qt, QSortFilterProxyModel, QRect
from PySide2.QtGui import QTextCursor, QIcon, QPainter, QFontMetrics, QTextCharFormat

class PasswordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Input Password"))
        self.layout = QVBoxLayout(self)
        self.label = QLabel(_("Please enter the unitx user password:"))
        self.layout.addWidget(self.label)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.layout.addWidget(self.password_input)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)

class FileFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, unitx_home, exclude_dir, parent=None):
        super().__init__(parent)
        self.unitx_home = unitx_home
        self.exclude_dir = exclude_dir

    def filterAcceptsRow(self, source_row, source_parent):
        index = self.sourceModel().index(source_row, 0, source_parent)
        file_path = self.sourceModel().filePath(index)
        return not file_path.startswith(self.exclude_dir)

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
        self.setFixedWidth(self.calculate_width())

    def calculate_width(self):
        digits = len(str(self.editor.document().blockCount()))
        font_metrics = QFontMetrics(self.editor.font())
        return font_metrics.horizontalAdvance('9') * digits + 20

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(event.rect(), Qt.lightGray)

        block = self.editor.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.editor.blockBoundingGeometry(block).translated(self.editor.contentOffset()).top()
        bottom = top + self.editor.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(Qt.black)
                painter.drawText(0, int(top), self.width(), int(self.editor.fontMetrics().height()), Qt.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + self.editor.blockBoundingRect(block).height()
            block_number += 1

class CodeEditor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.editor = QPlainTextEdit()
        self.line_number_area = LineNumberArea(self.editor)

        layout = QHBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.line_number_area)
        layout.addWidget(self.editor)

        self.editor.blockCountChanged.connect(self.update_line_number_area_width)
        self.editor.updateRequest.connect(self.update_line_number_area)
        self.editor.cursorPositionChanged.connect(self.highlight_current_line)

        self.update_line_number_area_width(0)

    def update_line_number_area_width(self, new_block_count):
        self.editor.setViewportMargins(self.line_number_area.width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.editor.viewport().rect()):
            self.update_line_number_area_width(0)

    def highlight_current_line(self):
        extra_selections = []
        selection = QTextEdit.ExtraSelection()
        line_color = Qt.yellow if self.editor.hasFocus() else Qt.lightGray
        selection.format.setBackground(line_color)
        selection.format.setProperty(Qt.BackgroundRole, line_color)
        selection.cursor = self.editor.textCursor()
        selection.cursor.clearSelection()
        extra_selections.append(selection)
        self.editor.setExtraSelections(extra_selections)

    def highlight_search_results(self, keyword, case_sensitive, match_mode):
        extra_selections = self.editor.extraSelections()  # 保留当前行高亮
        text = self.editor.toPlainText()
        flags = 0 if case_sensitive else re.IGNORECASE
        if match_mode == _("Exact Match"):
            pattern = r'\b' + re.escape(keyword) + r'\b'
        else:
            pattern = re.escape(keyword)

        for match in re.finditer(pattern, text, flags):
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(Qt.darkGray)  # 搜索结果高亮为灰色
            cursor = self.editor.textCursor()
            cursor.setPosition(match.start())
            cursor.setPosition(match.end(), QTextCursor.KeepAnchor)
            selection.cursor = cursor
            extra_selections.append(selection)
        self.editor.setExtraSelections(extra_selections)

class FileManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(_("Unitx File Manager Tool"))
        self.resize(1000, 700)

        current_directory = os.path.dirname(os.path.realpath(__file__))
        log_dir = os.path.join(current_directory, "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "file_manager.log")
        dir_mode = stat.S_IMODE(os.stat(log_dir).st_mode)
        if dir_mode != 0o777:
            os.chmod(log_dir, 0o777)
        if not os.path.exists(log_file):
            with open(log_file, 'w') as f:
                pass
        file_mode = stat.S_IMODE(os.stat(log_file).st_mode)
        if file_mode != 0o777:
            os.chmod(log_file, 0o777)
        MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB

        if os.path.exists(log_file):
            file_size = os.path.getsize(log_file)
            if file_size > MAX_LOG_SIZE:
                try:
                    os.remove(log_file)
                    print(f"Log file {log_file} size {file_size / (1024 * 1024):.2f}MB exceeds 10MB and has been deleted")
                except OSError as e:
                    print(f"Failed to delete log file {log_file} : {str(e)}")

        self.logger = logging.getLogger('UnitxFileManager')
        if not self.logger.handlers:
            self.logger.setLevel(logging.INFO)
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        self.logger.info("Program started")

        self.unitx_home = "/home/unitx"
        self.exclude_dir = os.path.join(self.unitx_home, "unitx_volumes")
        self.unitx_password = None
        if not os.path.exists(self.unitx_home):
            QMessageBox.critical(self, _("Error"), _("unitx home directory does not exist!"))
            sys.exit(1)

        if not self.verify_unitx_password():
            sys.exit(1)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QHBoxLayout(self.central_widget)
        self.layout.setStretch(0, 1)
        self.layout.setStretch(1, 2)

        # 左侧文件管理区
        self.left_layout = QVBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setReadOnly(True)
        self.path_input.setText(self.unitx_home)
        self.left_layout.addWidget(self.path_input)

        self.button_layout = QHBoxLayout()
        self.back_button = QPushButton(_("Back"))
        self.back_button.setIcon(QIcon.fromTheme("go-previous"))
        self.back_button.clicked.connect(self.go_up)
        self.back_button.setMinimumWidth(80)
        self.button_layout.addWidget(self.back_button)

        self.home_button = QPushButton(_("Home"))
        self.home_button.setIcon(QIcon.fromTheme("go-home"))
        self.home_button.clicked.connect(self.go_home)
        self.home_button.setMinimumWidth(80)
        self.button_layout.addWidget(self.home_button)

        self.button_layout.addStretch(1)
        self.left_layout.addLayout(self.button_layout)

        self.tree = QTreeView()
        self.model = QFileSystemModel()
        self.model.setRootPath(self.unitx_home)
        self.proxy_model = FileFilterProxyModel(self.unitx_home, self.exclude_dir, self)
        self.proxy_model.setSourceModel(self.model)
        self.tree.setModel(self.proxy_model)
        self.tree.setRootIndex(self.proxy_model.mapFromSource(self.model.index(self.unitx_home)))
        self.tree.setColumnWidth(0, 300)
        self.tree.doubleClicked.connect(self.handle_tree_double_click)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        self.left_layout.addWidget(self.tree)
        self.layout.addLayout(self.left_layout)

        # 右侧编辑区
        self.right_layout = QVBoxLayout()
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.right_layout.addWidget(self.tabs, stretch=3)

        # 第一行：搜索到查看全部
        self.search_layout1 = QHBoxLayout()
        self.search_label = QLabel(_("Search:"))
        self.search_layout1.addWidget(self.search_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(_("Enter keyword"))
        self.search_input.returnPressed.connect(self.search_next)
        self.search_layout1.addWidget(self.search_input, stretch=1)

        self.match_mode = QComboBox()
        self.match_mode.addItems([_("Exact Match"), _("Fuzzy Match")])
        self.search_layout1.addWidget(self.match_mode)

        self.case_sensitive = QCheckBox(_("Case Sensitive"))
        self.search_layout1.addWidget(self.case_sensitive)

        self.loop_search = QCheckBox(_("Loop Search"))
        self.loop_search.setChecked(True)
        self.search_layout1.addWidget(self.loop_search)

        self.prev_button = QPushButton(_("Previous"))
        self.prev_button.clicked.connect(self.search_prev)
        self.prev_button.setMinimumWidth(80)
        self.search_layout1.addWidget(self.prev_button)

        self.next_button = QPushButton(_("Next"))
        self.next_button.clicked.connect(self.search_next)
        self.next_button.setMinimumWidth(80)
        self.search_layout1.addWidget(self.next_button)

        self.all_button = QPushButton(_("View All"))
        self.all_button.clicked.connect(self.search_all)
        self.all_button.setMinimumWidth(80)
        self.search_layout1.addWidget(self.all_button)

        self.right_layout.addLayout(self.search_layout1)

        # 第二行：替换为到跳转
        self.search_layout2 = QHBoxLayout()
        self.replace_label = QLabel(_("Replace with:"))
        self.search_layout2.addWidget(self.replace_label)

        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText(_("Enter replacement"))
        self.search_layout2.addWidget(self.replace_input, stretch=1)

        self.replace_one_button = QPushButton(_("Replace Current"))
        self.replace_one_button.clicked.connect(self.replace_one)
        self.replace_one_button.setMinimumWidth(80)
        self.search_layout2.addWidget(self.replace_one_button)

        self.replace_all_button = QPushButton(_("Replace All"))
        self.replace_all_button.clicked.connect(self.replace_all)
        self.replace_all_button.setMinimumWidth(80)
        self.replace_all_button.setShortcut("Ctrl+H")
        self.search_layout2.addWidget(self.replace_all_button)

        self.line_label = QLabel(_("Go to Line:"))
        self.search_layout2.addWidget(self.line_label)

        self.line_input = QSpinBox()
        self.line_input.setMinimum(1)
        self.search_layout2.addWidget(self.line_input)

        self.goto_button = QPushButton(_("Go"))
        self.goto_button.clicked.connect(self.goto_line)
        self.goto_button.setMinimumWidth(80)
        self.search_layout2.addWidget(self.goto_button)

        self.right_layout.addLayout(self.search_layout2)

        # 第三行：关闭文件到恢复
        self.search_layout3 = QHBoxLayout()
        self.undo_button = QPushButton(_("Undo"))
        self.undo_button.clicked.connect(self.undo)
        self.undo_button.setMinimumWidth(80)
        self.undo_button.setShortcut("Ctrl+Z")
        self.undo_button.setEnabled(False)
        self.search_layout3.addWidget(self.undo_button)

        self.redo_button = QPushButton(_("Redo"))
        self.redo_button.clicked.connect(self.redo)
        self.redo_button.setMinimumWidth(80)
        self.redo_button.setShortcut("Ctrl+Y")
        self.redo_button.setEnabled(False)
        self.search_layout3.addWidget(self.redo_button)

        self.close_button = QPushButton(_("Close File"))
        self.close_button.clicked.connect(self.close_file)
        self.close_button.setMinimumWidth(80)
        self.search_layout3.addWidget(self.close_button)

        self.save_button = QPushButton(_("Save File"))
        self.save_button.clicked.connect(self.save_file)
        self.save_button.setMinimumWidth(80)
        self.save_button.setShortcut("Ctrl+S")
        self.search_layout3.addWidget(self.save_button)

        self.right_layout.addLayout(self.search_layout3)

        self.result_list = QListWidget()
        self.result_list.itemDoubleClicked.connect(self.jump_to_result)
        self.right_layout.addWidget(self.result_list, stretch=1)

        self.layout.addLayout(self.right_layout)

        # 状态栏
        self.status_bar = self.statusBar()
        self.status_bar.showMessage(_("Ready"))

        self.current_file = None
        self.last_search_pos = 0
        self.tab_files = {}

        self.tabs.currentChanged.connect(self.on_tab_changed)

    def verify_unitx_password(self):
        dialog = PasswordDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.unitx_password = dialog.password_input.text()
            test_cmd = f'echo "{self.unitx_password}" | su - unitx -c "whoami"'
            result = subprocess.run(test_cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip() == "unitx":
                return True
            else:
                QMessageBox.critical(self, _("Error"),
                                     _("Incorrect password, unable to verify unitx user identity!"))
                return False
        return False

    def run_as_unitx(self, command):
        cmd = f'echo "{self.unitx_password}" | su - unitx -c "{command}"'
        return subprocess.run(cmd, shell=True, capture_output=True, text=True)

    def go_up(self):
        current_path = self.path_input.text()
        parent_path = os.path.dirname(current_path)
        if parent_path.startswith(self.unitx_home):
            self.path_input.setText(parent_path)
            self.tree.setRootIndex(self.proxy_model.mapFromSource(self.model.index(parent_path)))

    def go_home(self):
        self.path_input.setText(self.unitx_home)
        self.tree.setRootIndex(self.proxy_model.mapFromSource(self.model.index(self.unitx_home)))

    def handle_tree_double_click(self, index):
        file_path = self.proxy_model.mapToSource(index).data(QFileSystemModel.FilePathRole)
        if os.path.isfile(file_path):
            self.load_file(file_path)
        elif os.path.isdir(file_path):
            self.path_input.setText(file_path)
            self.tree.setRootIndex(self.proxy_model.mapFromSource(self.model.index(file_path)))

    def show_context_menu(self, position):
        index = self.tree.indexAt(position)
        if not index.isValid():
            return
        file_path = self.proxy_model.mapToSource(index).data(QFileSystemModel.FilePathRole)
        if os.path.isfile(file_path):
            menu = QMenu(self)
            open_action = menu.addAction(_("Open"))
            action = menu.exec_(self.tree.viewport().mapToGlobal(position))
            if action == open_action:
                self.load_file(file_path)

    def load_file(self, file_path):
        MAX_FILE_SIZE = 10 * 1024 * 1024
        file_size = os.path.getsize(file_path)
        
        if file_size > MAX_FILE_SIZE:
            size_mb = file_size / (1024 * 1024)
            msg = _(
                "File '{filename}' size is {size:.2f} MB, exceeds limit (10MB).\nPlease use another tool to open large files.").format(
                filename=os.path.basename(file_path), size=size_mb)
            QMessageBox.warning(self, _("File Too Large"), msg)
            return

        self.logger.info(f"Starting to load file: {file_path}")

        try:
            result = self.run_as_unitx(f"cat '{file_path}'")
            if result and result.returncode == 0:
                for i in range(self.tabs.count()):
                    if self.tab_files.get(i) == file_path:
                        self.tabs.setCurrentIndex(i)
                        self.logger.info(f"File {file_path} already open, switching to existing tab")
                        return
                new_editor = CodeEditor()
                new_editor.editor.setLineWrapMode(QPlainTextEdit.NoWrap)
                new_editor.editor.setTabStopDistance(40)
                new_editor.editor.setUndoRedoEnabled(True)
                new_editor.editor.setPlainText(result.stdout)
                new_editor.editor.cursorPositionChanged.connect(self.update_status_bar)
                new_editor.editor.document().undoAvailable.connect(self.undo_button.setEnabled)
                new_editor.editor.document().redoAvailable.connect(self.redo_button.setEnabled)
                tab_index = self.tabs.addTab(new_editor, os.path.basename(file_path))
                self.tab_files[tab_index] = file_path
                self.tabs.setCurrentIndex(tab_index)
                self.current_file = file_path
                self.last_search_pos = 0
                self.result_list.clear()
                self.line_input.setMaximum(new_editor.editor.document().lineCount())
                self.update_status_bar()
                self.logger.info(f"File {file_path} loaded successfully, added to new tab")
            else:
                msg = _("Unable to read file: {error}").format(error=result.stderr)
                QMessageBox.warning(self, _("Warning"), msg)
        except Exception as e:
            msg = _("Failed to read file: {error}").format(error=str(e))
            QMessageBox.critical(self, _("Error"), msg)

    def close_tab(self, index):
        if index in self.tab_files:
            del self.tab_files[index]
        self.tabs.removeTab(index)
        if self.tabs.count() == 0:
            self.current_file = None
            self.update_status_bar()

    def on_tab_changed(self, index):
        if index >= 0 and index in self.tab_files:
            self.current_file = self.tab_files[index]
            self.update_status_bar()
            self.result_list.clear()
            self.last_search_pos = 0
            editor = self.current_editor()
            if editor:
                self.line_input.setMaximum(editor.editor.document().lineCount())

    def current_editor(self):
        return self.tabs.currentWidget() if self.tabs.currentWidget() else None

    def update_status_bar(self):
        if self.tabs.count() == 0:
            self.status_bar.showMessage(_("Ready"))
            return
        editor = self.current_editor()
        if editor:
            cursor = editor.editor.textCursor()
            line = cursor.blockNumber() + 1
            col = cursor.columnNumber() + 1
            self.status_bar.showMessage(f"File: {self.current_file or 'None'} | Line: {line} | Col: {col}")

    def save_file(self):
        if not self.current_file or self.tabs.count() == 0:
            QMessageBox.warning(self, _("Warning"), _("Please select a file first!"))
            return
        editor = self.current_editor()
        if editor:
            content = editor.editor.toPlainText()
            try:
                with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
                    temp_path = temp_file.name
                    temp_file.write(content)
                os.chmod(temp_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)

                cmd = f'echo "{self.unitx_password}" | su - unitx -c "cat \'{temp_path}\' > \'{self.current_file}\'"'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    QMessageBox.information(self, _("Success"), _("File saved successfully!"))
                    editor.editor.document().setModified(False)
                    self.logger.info(f"File {self.current_file} saved successfully")
                else:
                    error_msg = result.stderr.strip() or "未知错误"
                    msg = _("Save failed: {error}").format(error=error_msg)
                    QMessageBox.warning(self, _("Warning"), msg)
                os.unlink(temp_path)
            except Exception as e:
                msg = _("Failed to save file: {error}").format(error=str(e))
                QMessageBox.critical(self, _("Error"), msg)
                if 'temp_path' in locals():
                    os.unlink(temp_path)

    def close_file(self):
        if self.tabs.count() > 0:
            index = self.tabs.currentIndex()
            self.logger.info(f"Closing file: {self.current_file}")
            self.close_tab(index)

    def update_search_highlights(self):
        if self.tabs.count() == 0 or not self.search_input.text():
            return
        keyword = self.search_input.text()
        editor = self.current_editor()
        if editor:
            editor.highlight_search_results(keyword, self.case_sensitive.isChecked(), self.match_mode.currentText())

    def search_next(self):
        if not self.current_file or not self.search_input.text() or self.tabs.count() == 0:
            return
        keyword = self.search_input.text()
        editor = self.current_editor()
        if editor:
            text = editor.editor.toPlainText()
            flags = 0 if self.case_sensitive.isChecked() else re.IGNORECASE
            if self.match_mode.currentText() == _("Exact Match"):
                pattern = r'\b' + re.escape(keyword) + r'\b'
            else:
                pattern = re.escape(keyword)

            cursor = editor.editor.textCursor()
            pos = cursor.position()
            match = re.search(pattern, text[pos:], flags)
            if match:
                start, end = match.start() + pos, match.end() + pos
                cursor.setPosition(start)
                cursor.setPosition(end, QTextCursor.KeepAnchor)
                editor.editor.setTextCursor(cursor)
                editor.editor.ensureCursorVisible()
                self.last_search_pos = end
                self.update_search_highlights()
            else:
                if self.loop_search.isChecked():
                    self.last_search_pos = 0
                    match = re.search(pattern, text, flags)
                    if match:
                        start, end = match.start(), match.end()
                        cursor.setPosition(start)
                        cursor.setPosition(end, QTextCursor.KeepAnchor)
                        editor.editor.setTextCursor(cursor)
                        editor.editor.ensureCursorVisible()
                        self.last_search_pos = end
                        self.update_search_highlights()
                    else:
                        msg = _("'{keyword}' not found").format(keyword=keyword)
                        QMessageBox.information(self, _("Hint"), msg)
                else:
                    msg = _("No more '{keyword}' found").format(keyword=keyword)
                    QMessageBox.information(self, _("Hint"), msg)

    from PySide2.QtWidgets import QApplication  # 确保导入

    def search_prev(self):
        if not self.current_file or not self.search_input.text() or self.tabs.count() == 0:
            return
        keyword = self.search_input.text()
        editor = self.current_editor()
        if not editor:
            return

        text = editor.editor.toPlainText()
        flags = 0 if self.case_sensitive.isChecked() else re.IGNORECASE
        if self.match_mode.currentText() == _("Exact Match"):
            pattern = r'\b' + re.escape(keyword) + r'\b'
        else:
            pattern = re.escape(keyword)

        cursor = editor.editor.textCursor()
        pos = cursor.position()

        all_matches = list(re.finditer(pattern, text, flags))

        if not all_matches:
            msg = _("'{keyword}' not found").format(keyword=keyword)
            self.log_translation("'{keyword}' not found", msg)
            QMessageBox.information(self, _("Hint"), msg)
            return

        prev_match = None
        for match in reversed(all_matches):
            if match.end() < pos:
                prev_match = match
                break

        if prev_match:
            start, end = prev_match.start(), prev_match.end()
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.KeepAnchor)
            editor.editor.setTextCursor(cursor)
            editor.editor.ensureCursorVisible()
            editor.editor.setFocus()
            QApplication.processEvents()  # 强制刷新
            self.last_search_pos = start
            self.update_search_highlights()
            # 获取新光标所在的行号
            new_cursor = editor.editor.textCursor()
            block = editor.editor.document().findBlock(new_cursor.position())
            line_number = block.blockNumber() + 1
            self.logger.info(f"已跳转到上一个匹配项: 新光标所在行: {line_number}")
        else:
            if self.loop_search.isChecked():
                last_match = all_matches[-1]
                start, end = last_match.start(), last_match.end()
                cursor.setPosition(start)
                cursor.setPosition(end, QTextCursor.KeepAnchor)
                editor.editor.setTextCursor(cursor)
                editor.editor.ensureCursorVisible()
                editor.editor.setFocus()
                QApplication.processEvents()
                self.last_search_pos = start
                self.update_search_highlights()
            else:
                msg = _("No more '{keyword}' found").format(keyword=keyword)
                self.log_translation("No more '{keyword}' found", msg)
                QMessageBox.information(self, _("Hint"), msg)
    def _update_search_results(self):
        if not self.current_file or not self.search_input.text() or self.tabs.count() == 0:
            self.result_list.clear()
            return 0
        keyword = self.search_input.text()
        editor = self.current_editor()
        if editor:
            text = editor.editor.toPlainText()
            flags = 0 if self.case_sensitive.isChecked() else re.IGNORECASE
            if self.match_mode.currentText() == _("Exact Match"):
                pattern = r'\b' + re.escape(keyword) + r'\b'
            else:
                pattern = re.escape(keyword)

            self.result_list.clear()
            lines = text.splitlines()
            matches = 0
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line, flags):
                    self.result_list.addItem(f"Line {i}: {line}")
                    matches += 1
            return matches
        return 0

    def search_all(self):
        matches = self._update_search_results()
        self.update_search_highlights()
        if matches == 0:
            keyword = self.search_input.text()
            msg = _("'{keyword}' not found").format(keyword=keyword)
            QMessageBox.information(self, _("Hint"), msg)

    def replace_one(self):
        if not self.current_file or not self.search_input.text() or self.tabs.count() == 0:
            return
        keyword = self.search_input.text()
        replace_text = self.replace_input.text()
        editor = self.current_editor()
        if editor:
            self.logger.info(f"Replace current keyword: {keyword} with {replace_text} in file {self.current_file}")
            text = editor.editor.toPlainText()
            flags = 0 if self.case_sensitive.isChecked() else re.IGNORECASE
            if self.match_mode.currentText() == _("Exact Match"):
                pattern = r'\b' + re.escape(keyword) + r'\b'
            else:
                pattern = re.escape(keyword)

            cursor = editor.editor.textCursor()

            if cursor.hasSelection():
                start, end = cursor.selectionStart(), cursor.selectionEnd()
                selected_text = text[start:end]
                match = re.search(pattern, selected_text, flags)
                if match:
                    match_start, match_end = match.start() + start, match.end() + start
                    cursor.setPosition(match_start)
                    cursor.setPosition(match_end, QTextCursor.KeepAnchor)
                    cursor.insertText(replace_text)
                    self.last_search_pos = match_start + len(replace_text)
                    self._search_next_after_replace(keyword, pattern, flags)
                    self.update_search_highlights()
                    block = editor.editor.document().findBlock(match_start)
                    line_number = block.blockNumber() + 1
                    self.logger.info(f"Replacement successful，line: {line_number}")
                    return

            pos = cursor.position()
            match = re.search(pattern, text[pos:], flags)
            if match:
                start, end = match.start() + pos, match.end() + pos
                cursor.setPosition(start)
                cursor.setPosition(end, QTextCursor.KeepAnchor)
                cursor.insertText(replace_text)
                self.last_search_pos = start + len(replace_text)
                self._search_next_after_replace(keyword, pattern, flags)
                self.update_search_highlights()
                block = editor.editor.document().findBlock(start)
                line_number = block.blockNumber() + 1
                self.logger.info(f"Replacement successful，line: {line_number}")
            else:
                if not re.search(pattern, text, flags):
                    msg = _("'{keyword}' not found").format(keyword=keyword)
                    QMessageBox.information(self, _("Hint"), msg)
                elif self.loop_search.isChecked():
                    self.last_search_pos = 0
                    match = re.search(pattern, text, flags)
                    if match:
                        start, end = match.start(), match.end()
                        cursor.setPosition(start)
                        cursor.setPosition(end, QTextCursor.KeepAnchor)
                        cursor.insertText(replace_text)
                        self.last_search_pos = start + len(replace_text)
                        self._search_next_after_replace(keyword, pattern, flags)
                        self.update_search_highlights()
                        block = editor.editor.document().findBlock(start)
                        line_number = block.blockNumber() + 1
                        self.logger.info(f"Replacement successful，line: {line_number}")
                    else:
                        msg = _("Replacement complete, no more '{keyword}' found").format(keyword=keyword)
                        QMessageBox.information(self, _("Hint"), msg)
                else:
                    msg = _("Replacement complete, no more '{keyword}' found").format(keyword=keyword)
                    QMessageBox.information(self, _("Hint"), msg)

    def _search_next_after_replace(self, keyword, pattern, flags):
        editor = self.current_editor()
        if editor:
            text = editor.editor.toPlainText()
            match = re.search(pattern, text[self.last_search_pos:], flags)
            if match:
                start, end = match.start() + self.last_search_pos, match.end() + self.last_search_pos
                cursor = editor.editor.textCursor()
                cursor.setPosition(start)
                cursor.setPosition(end, QTextCursor.KeepAnchor)
                editor.editor.setTextCursor(cursor)
                editor.editor.ensureCursorVisible()

    def replace_all(self):
        if not self.current_file or not self.search_input.text() or self.tabs.count() == 0:
            return
        keyword = self.search_input.text()
        replace_text = self.replace_input.text()
        editor = self.current_editor()
        if editor:
            self.logger.info(f"Replace all keywords: {keyword} with {replace_text} in file {self.current_file}")
            text = editor.editor.toPlainText()
            flags = 0 if self.case_sensitive.isChecked() else re.IGNORECASE
            if self.match_mode.currentText() == _("Exact Match"):
                pattern = r'\b' + re.escape(keyword) + r'\b'
            else:
                pattern = re.escape(keyword)

            cursor = editor.editor.textCursor()
            cursor.beginEditBlock()
            matches = list(re.finditer(pattern, text, flags))
            count = len(matches)

            if count > 0:
                for match in reversed(matches):
                    start, end = match.start(), match.end()
                    cursor.setPosition(start)
                    cursor.setPosition(end, QTextCursor.KeepAnchor)
                    cursor.insertText(replace_text)
                cursor.endEditBlock()
                self.last_search_pos = 0
                self._update_search_results()
                self.update_search_highlights()
                msg = _("Replaced {count} matches").format(count=count)
                QMessageBox.information(self, _("Result"), msg)
                self.logger.info(f"Replace all successfully, replaced {count} matches")
            else:
                cursor.endEditBlock()
                msg = _("'{keyword}' not found").format(keyword=keyword)
                QMessageBox.information(self, _("Hint"), msg)

    def goto_line(self):
        if self.tabs.count() == 0:
            return
        editor = self.current_editor()
        if editor:
            line = self.line_input.value() - 1
            cursor = editor.editor.textCursor()
            cursor.movePosition(QTextCursor.Start)
            cursor.movePosition(QTextCursor.Down, n=line)
            editor.editor.setTextCursor(cursor)
            editor.editor.ensureCursorVisible()

    def jump_to_result(self, item):
        if self.tabs.count() == 0:
            return
        editor = self.current_editor()
        if editor:
            line_number = int(item.text().split(":")[0].replace("Line ", "")) - 1
            cursor = editor.editor.textCursor()
            cursor.movePosition(QTextCursor.Start)
            cursor.movePosition(QTextCursor.Down, n=line_number)
            editor.editor.setTextCursor(cursor)
            editor.editor.ensureCursorVisible()
            line_text = editor.editor.document().findBlockByLineNumber(line_number).text()
            keyword = self.search_input.text()
            if keyword in line_text:
                start = line_text.index(keyword) + cursor.block().position()
                end = start + len(keyword)
                cursor.setPosition(start)
                cursor.setPosition(end, QTextCursor.KeepAnchor)
                editor.editor.setTextCursor(cursor)

    def undo(self):
        if self.tabs.count() > 0:
            editor = self.current_editor()
            if editor:
                self.logger.info(f"Execute undo operation in file {self.current_file}")
                editor.editor.undo()
                self.update_search_highlights()

    def redo(self):
        if self.tabs.count() > 0:
            editor = self.current_editor()
            if editor:
                self.logger.info(f"Performing recovery operation in file {self.current_file}")
                editor.editor.redo()
                self.update_search_highlights()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FileManager()
    window.show()
    sys.exit(app.exec_())
