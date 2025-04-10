from PySide2.QtWidgets import QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton, QStackedWidget, QTextEdit, QWidget, QLabel, QMenuBar, QMenu, QAction, QMessageBox, QApplication, QSizePolicy
from PySide2.QtCore import Qt
import sys
import os
import getpass
from system_info import SystemInfoCheck
from system_check import SystemCheck
from driver_check import DriverCheck
from large_file_check import LargeFileCheck
from log_viewer import LogViewer
from system_monitoring import SystemMonitoring
from file_integrity_monitor import FileIntegrityMonitor
from unitx_file_manager import FileManager
from language_resources import language_resources
from localization import setup_locale, _

class SystemCheckApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("System issue diagnose tool for Ubuntu 22.04")
        self.setGeometry(100, 100, 1280, 720)

        self.current_language = os.environ.get('LANG').split('.')[0]

        self.current_button = None

        self.stacked_widget = QStackedWidget(self)

        self.initUI()


    def initUI(self):
        self.create_menu()

        main_layout = QVBoxLayout()

        self.title_label = QLabel(language_resources[self.current_language]['title'], self)
        main_layout.addWidget(self.title_label)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        button_layout.setContentsMargins(0, 0, 0, 0)

        self.btn_system_info = QPushButton(language_resources[self.current_language]['system_info'], self)
        self.style_button(self.btn_system_info)
        self.btn_system_info.clicked.connect(self.show_system_info)
        button_layout.addWidget(self.btn_system_info)

        self.btn_check_system = QPushButton(language_resources[self.current_language]['ssh_status'], self)
        self.style_button(self.btn_check_system)
        self.btn_check_system.clicked.connect(self.show_system_check)
        button_layout.addWidget(self.btn_check_system)

        self.btn_driver_update = QPushButton(language_resources[self.current_language]['gpu_driver'], self)
        self.style_button(self.btn_driver_update)
        self.btn_driver_update.clicked.connect(self.show_driver_check)
        button_layout.addWidget(self.btn_driver_update)

        self.btn_large_files = QPushButton(language_resources[self.current_language]['large_file'], self)
        self.style_button(self.btn_large_files)
        self.btn_large_files.clicked.connect(self.show_large_files)
        button_layout.addWidget(self.btn_large_files)

        self.btn_log_viewer = QPushButton(language_resources[self.current_language]['log_collection'], self)
        self.style_button(self.btn_log_viewer)
        self.btn_log_viewer.clicked.connect(self.show_log_viewer)
        button_layout.addWidget(self.btn_log_viewer)

        self.btn_system_monitoring = QPushButton(language_resources[self.current_language]['system_monitoring'], self)
        self.style_button(self.btn_system_monitoring)
        self.btn_system_monitoring.clicked.connect(self.show_system_monitoring)
        button_layout.addWidget(self.btn_system_monitoring)

        self.btn_file_integrity = QPushButton(language_resources[self.current_language]['file_integrity'], self)
        self.style_button(self.btn_file_integrity)
        self.btn_file_integrity.clicked.connect(self.show_file_integrity_monitor)
        button_layout.addWidget(self.btn_file_integrity)

        self.btn_config_editor = QPushButton(language_resources[self.current_language]['config_editor'], self)
        self.style_button(self.btn_config_editor)
        self.btn_config_editor.clicked.connect(self.show_config_editor)
        button_layout.addWidget(self.btn_config_editor)

        main_layout.addLayout(button_layout)

        self.system_info = SystemInfoCheck()
        self.system_check = None
        self.driver_check = None
        self.large_file_check = None
        self.log_viewer = None
        self.system_monitoring = None
        self.file_integrity_monitor = None
        self.config_editor = None

        self.output_area = QTextEdit(self)
        self.output_area.setReadOnly(True)
        self.output_area.setMinimumHeight(200)

        self.stacked_widget.addWidget(self.output_area)

        container = QWidget(self)
        container.setLayout(main_layout)
        main_layout.addWidget(self.stacked_widget)
        self.setCentralWidget(container)

    def create_menu(self):
        menu_bar = self.menuBar()

        lang_menu = menu_bar.addMenu("Language | 语言")

        lang_english = QAction("English", self)
        lang_chinese = QAction("中文", self)
        lang_menu.addAction(lang_english)
        lang_menu.addAction(lang_chinese)

        lang_english.triggered.connect(self.set_english_language)
        lang_chinese.triggered.connect(self.set_chinese_language)

        help_menu = menu_bar.addMenu("Help | 帮助")
        self.help_action = QAction(self.get_help_text(), self)
        help_menu.addAction(self.help_action)
        self.help_action.triggered.connect(self.show_help)

        about_action = QAction("关于", self)
        self.about_action = QAction(self.get_about_text(), self)
        help_menu.addAction(self.about_action)
        self.about_action.triggered.connect(self.show_about)

    def update_ui_text(self):
        lang = self.current_language
        resources = language_resources[lang]

        self.title_label.setText(resources['title'])
        self.btn_system_info.setText(resources['system_info'])
        self.btn_check_system.setText(resources['ssh_status'])
        self.btn_driver_update.setText(resources['gpu_driver'])
        self.btn_large_files.setText(resources['large_file'])
        self.btn_log_viewer.setText(resources['log_collection'])
        self.btn_system_monitoring.setText(resources['system_monitoring'])
        self.btn_file_integrity.setText(resources['file_integrity'])
        self.btn_config_editor.setText(resources['config_editor'])

        self.help_action.setText(resources['help'])
        self.about_action.setText(resources['about'])
        
        if self.system_info:
             self.system_info.update_language(lang)
        if self.system_check:
            self.system_check.update_language(lang)
        if self.driver_check:
            self.driver_check.update_language(lang)
        if self.log_viewer:
            self.log_viewer.update_language(lang)
        if self.file_integrity_monitor:
            self.file_integrity_monitor.update_language(lang)

    def set_english_language(self):
        self.current_language = 'en_US'
        self.update_ui_text()

    def set_chinese_language(self):
        self.current_language = 'zh_CN'
        self.update_ui_text()

    def get_help_text(self):
        if self.current_language == 'en_US':
            return "View Help"
        else:
            return "查看帮助"

    def get_about_text(self):
        if self.current_language == 'en_US':
            return "About"
        else:
            return "关于"

    def style_button(self, button, active=False):
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {'#1976D2' if active else '#4CAF50'};
                color: white;
                border: 2px solid {'#1976D2' if active else '#4CAF50'};
                border-radius: 12px;
                font-size: 14px;
                padding: 10px 20px;
            }}
            QPushButton:hover {{
                background-color: #45a049;
                border: 2px solid #45a049;
            }}
            QPushButton:pressed {{
                background-color: #1976D2;
                border: 2px solid #1976D2;
            }}
        """)

        # Make button text dynamically resize
        button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def update_button_style(self, button):
        if self.current_button:
            self.style_button(self.current_button, active=False)
        self.style_button(button, active=True)
        self.current_button = button

    def show_system_info(self):
        self.update_button_style(self.btn_system_info)
        self.stacked_widget.addWidget(self.system_info)
        self.stacked_widget.setCurrentWidget(self.system_info)
        self.system_info.output_area.clear()
        self.system_info.clear_disk_and_inode_info()
        self.system_info.clear_button_styles()
        self.system_info.disk_analysis_button.setVisible(False)

    def show_system_check(self):
        self.update_button_style(self.btn_check_system)
        if self.system_check is None:
            self.system_check = SystemCheck()
            self.stacked_widget.addWidget(self.system_check)
        self.stacked_widget.setCurrentWidget(self.system_check)

    def show_driver_check(self):
        self.update_button_style(self.btn_driver_update)
        if self.driver_check is None:
            self.driver_check = DriverCheck()
            self.stacked_widget.addWidget(self.driver_check)
        self.driver_check.check_drivers()
        self.stacked_widget.setCurrentWidget(self.driver_check)

    def show_large_files(self):
        self.update_button_style(self.btn_large_files)
        if self.large_file_check is None:
            self.large_file_check = LargeFileCheck()
            self.stacked_widget.addWidget(self.large_file_check)
        self.stacked_widget.setCurrentWidget(self.large_file_check)

    def show_log_viewer(self):
        self.update_button_style(self.btn_log_viewer)
        if self.log_viewer is None:
            self.log_viewer = LogViewer()
            self.stacked_widget.addWidget(self.log_viewer)
        self.stacked_widget.setCurrentWidget(self.log_viewer)

    def show_system_monitoring(self):
        self.update_button_style(self.btn_system_monitoring)
        if self.system_monitoring is None:
            self.system_monitoring = SystemMonitoring()
            self.system_monitoring.open_grafana()
            self.stacked_widget.addWidget(self.system_monitoring)
        self.system_monitoring.open_grafana()
        self.stacked_widget.setCurrentWidget(self.system_monitoring)


    def show_file_integrity_monitor(self):
        self.update_button_style(self.btn_file_integrity)
        current_user = getpass.getuser()  # 每次点击都检查当前用户
        if current_user != 'unitx':
            QMessageBox.warning(self, _("Error"), _("Please run this script as unitx user."))
            return
        if self.file_integrity_monitor is None:
            self.file_integrity_monitor = FileIntegrityMonitor()
            self.stacked_widget.addWidget(self.file_integrity_monitor)
        self.stacked_widget.setCurrentWidget(self.file_integrity_monitor)

    def show_config_editor(self):
        self.update_button_style(self.btn_config_editor)
        if self.config_editor is None:
            self.config_editor = FileManager()
        self.config_editor.show()

    def show_help(self):
        QMessageBox.information(self, self.get_help_text(), _("Please select an operation according to the prompts on the interface."))

    def show_about(self):
        QMessageBox.information(self, self.get_about_text(), _("Ubuntu 22.04 System issue diagnose tool\nVersion 1.2"))

