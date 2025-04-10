import os
import re
from datetime import datetime, timedelta
from PySide2.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QDateTimeEdit, QPushButton, QTextEdit, QRadioButton
from PySide2.QtCore import QDateTime, Qt, QThread, Signal
import subprocess
from PySide2.QtGui import QFontMetrics
from language_resources import language_resources
from localization import setup_locale, _

class LogQueryThread(QThread):
    update_logs_signal = Signal(str)

    def __init__(self, time_range, lines):
        super().__init__()
        self.time_range = time_range
        self.lines = lines

    def run(self):
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            log_collection_path = os.path.join(script_dir, 'log_collection.py')

            if self.time_range:
                command = ['python3', log_collection_path, '-t', self.time_range[0], self.time_range[1]]
            elif self.lines:
                command = ['python3', log_collection_path, '-n', str(self.lines)]
            else:
                self.update_logs_signal.emit("Error: Input parameter is required.")
                return

            result = subprocess.run(command, capture_output=True, text=True)

            if result.returncode == 0:
                self.update_logs_signal.emit(result.stdout)
            else:
                self.update_logs_signal.emit(f"ERROR: {result.stderr}")
        except Exception as e:
            self.update_logs_signal.emit(f"ERROR: {str(e)}")


class LogViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.current_language = os.environ.get('LANG').split('.')[0]
        self.initUI()

    def initUI(self):

        main_layout = QVBoxLayout()

        top_layout = QVBoxLayout()

        filter_time_layout = QHBoxLayout()

        self.filter_time_button = QRadioButton(language_resources[self.current_language]['Filter time'], self)
        self.filter_time_button.setChecked(True)
        self.filter_time_button.toggled.connect(self.toggle_filters)

        self.time_label = QLabel(language_resources[self.current_language]['Select time period:'], self)
        self.time_label.setFixedWidth(160)
        self.time_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.start_datetime_edit = QDateTimeEdit(self)
        self.start_datetime_edit.setDateTime(QDateTime.currentDateTime().addSecs(-3600))
        self.start_datetime_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.start_datetime_edit.setCalendarPopup(True)

        self.end_datetime_edit = QDateTimeEdit(self)
        self.end_datetime_edit.setDateTime(QDateTime.currentDateTime())
        self.end_datetime_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.end_datetime_edit.setCalendarPopup(True)

        filter_time_layout.addWidget(self.filter_time_button)
        filter_time_layout.addWidget(self.time_label)
        filter_time_layout.addWidget(self.start_datetime_edit)
        filter_time_layout.addWidget(self.end_datetime_edit)
        top_layout.addLayout(filter_time_layout)

        filter_lines_layout = QHBoxLayout()
        self.filter_lines_button = QRadioButton(language_resources[self.current_language]['Filter by number of rows'], self)
        self.filter_lines_button.toggled.connect(self.toggle_filters)

        self.lines_label = QLabel(language_resources[self.current_language]['Enter the number of rows:'], self)
        self.lines_label.setFixedWidth(150)
        self.lines_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.lines_input = QLineEdit(self)
        placeholder_text = _("Enter the number of rows, for example 100")
        self.lines_input.setPlaceholderText(placeholder_text)
        font_metrics = QFontMetrics(self.lines_input.font())
        text_width = font_metrics.horizontalAdvance(placeholder_text)
        self.lines_input.setFixedWidth(text_width + 20)
        self.lines_input.setEnabled(False)

        filter_lines_layout.addWidget(self.filter_lines_button)
        filter_lines_layout.addWidget(self.lines_label)
        filter_lines_layout.addWidget(self.lines_input)
        top_layout.addLayout(filter_lines_layout)

        self.collect_logs_button = QPushButton(language_resources[self.current_language]['Log Collection'], self)
        self.collect_logs_button.setFixedSize(100, 30)
        self.collect_logs_button.clicked.connect(self.collect_logs)
        top_layout.addWidget(self.collect_logs_button)

        top_layout.setSpacing(10)
        filter_time_layout.setSpacing(10)
        filter_lines_layout.setSpacing(10)

        self.time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lines_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.start_datetime_edit.setAlignment(Qt.AlignCenter)
        self.end_datetime_edit.setAlignment(Qt.AlignCenter)
        self.lines_input.setAlignment(Qt.AlignCenter)

        filter_time_layout.addStretch()
        filter_lines_layout.addStretch()

        main_layout.addLayout(top_layout)

        self.log_viewer_output_area = QTextEdit(self)
        self.log_viewer_output_area.setReadOnly(True)
        main_layout.addWidget(self.log_viewer_output_area)

        self.setLayout(main_layout)

    def get_text(self, key):
        return language_resources[self.current_language][key]

    def update_language(self, language):
        self.current_language = language
        self.filter_time_button.setText(self.get_text('Filter time'))
        self.time_label.setText(self.get_text('Select time period:'))
        self.filter_lines_button.setText(self.get_text('Filter by number of rows'))
        self.lines_label.setText(self.get_text('Enter the number of rows:'))
        self.collect_logs_button.setText(self.get_text('Log Collection'))


    def toggle_filters(self):
        if self.filter_time_button.isChecked():
            self.start_datetime_edit.setEnabled(True)
            self.end_datetime_edit.setEnabled(True)
            self.lines_input.setEnabled(False)
        elif self.filter_lines_button.isChecked():
            self.start_datetime_edit.setEnabled(False)
            self.end_datetime_edit.setEnabled(False)
            self.lines_input.setEnabled(True)

    def collect_logs(self):
        self.log_viewer_output_area.setPlainText(_("Logs are being collected, please wait..."))
        start_datetime = self.start_datetime_edit.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        end_datetime = self.end_datetime_edit.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        lines_to_show = self.lines_input.text()

        time_range = None
        if self.filter_time_button.isChecked() and start_datetime and end_datetime:
            time_range = (start_datetime, end_datetime)
        elif self.filter_lines_button.isChecked() and lines_to_show:
            time_range = None
        else:
            self.log_viewer_output_area.setPlainText(_("Error: Please enter the number of rows"))
            return

        self.log_query_thread = LogQueryThread(time_range, lines_to_show)
        self.log_query_thread.update_logs_signal.connect(self.update_logs_display)
        self.log_query_thread.start()

    def update_logs_display(self, logs):
        self.log_viewer_output_area.setPlainText(logs)

