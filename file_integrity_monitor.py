import sys
import logging
from PySide2.QtCore import Qt, QThread, Signal
from PySide2.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, QTextEdit, QHBoxLayout, QSizePolicy, QMessageBox
from PySide2.QtGui import QFontMetrics
import os
import time
import subprocess
import deploy_integrity_monitor as monitor
from language_resources import language_resources
from localization import setup_locale, _

class ShellCommandThread(QThread):
    output_signal = Signal(str)
    error_signal = Signal(str)
    finished_signal = Signal()
    status_signal = Signal(str)

    def __init__(self, command, output_widget):
        super().__init__()
        self.command = command
        self.output_widget = output_widget
        self._is_running = True

    def run(self):
        try:
            logging.info(_("Start executing the command: {command}".format(command=self.command)))

            if self.command == 'deploy':
                self.status_signal.emit(_('deploying monitoring'))
                self.output_signal.emit(_('deploying monitoring'))
                monitor.deploy_monitoring(self.send_to_output)
                self.output_signal.emit(_('monitoring deployment completed'))
                logging.info(_('monitoring deployment completed'))
                self.status_signal.emit(_('monitoring deployment completed'))

            elif self.command == 'start_monitoring':
                self.status_signal.emit(_('File monitoring...'))
                self.output_signal.emit(_('Starting file monitoring...'))
                monitor.start_monitoring(self.send_to_output)
                logging.info(_('Start file monitoring'))

            elif self.command == 'status':
                self.status_signal.emit(_('Checking the deployment status'))
                self.output_signal.emit(_('Checking deployment status...'))
                monitor.check_deployment_status(self.send_to_output)

            elif self.command == 'stop_monitoring':
                self.status_signal.emit(_('Stop monitoring...'))
                self.output_signal.emit(_('Stopping file monitoring...'))
                monitor.stop_monitoring(self.send_to_output)
                self._is_running = False
                logging.info(_('File monitoring stopped'))
                self.status_signal.emit(_('File monitoring stopped'))

            elif self.command == 'remove':
                self.status_signal.emit(_('Remove monitoring...'))
                self.output_signal.emit(_('Remove monitoring...'))
                monitor.remove_monitoring(self.send_to_output)
                self.output_signal.emit(_('Monitoring has been removed'))
                logging.info(_('Monitoring has been removed'))
                self.status_signal.emit(_('Monitoring has been removed'))

        except Exception as e:
            error_msg = f"ERROR: {e}"
            self.error_signal.emit(error_msg)
            logging.error(error_msg)
        finally:
            self.finished_signal.emit()

    def send_to_output(self, message):
        self.output_signal.emit(message)
        logging.info(message)


class FileIntegrityMonitor(QWidget):
    def __init__(self):
        super().__init__()
        self.current_language = os.environ.get('LANG').split('.')[0]

        self.layout = QHBoxLayout()

        self.button_layout = QVBoxLayout()

        self.deploy_button = QPushButton(language_resources[self.current_language]['Deployment monitoring'], self)
        self.set_button_width(self.deploy_button)
        self.deploy_button.setFixedHeight(60)
        self.deploy_button.clicked.connect(self.deploy_monitoring)
        self.button_layout.addWidget(self.deploy_button)

        self.start_button = QPushButton(language_resources[self.current_language]['Start monitoring'], self)
        self.set_button_width(self.start_button)
        self.start_button.setFixedHeight(60)
        self.start_button.clicked.connect(self.start_monitoring)
        self.button_layout.addWidget(self.start_button)

        self.check_button = QPushButton(language_resources[self.current_language]['Checking the deployment status'], self)
        self.set_button_width(self.check_button)
        self.check_button.setFixedHeight(60)
        self.check_button.clicked.connect(self.check_deployment_status)
        self.button_layout.addWidget(self.check_button)

        self.stop_button = QPushButton(language_resources[self.current_language]['Stop monitoring'], self)
        self.set_button_width(self.stop_button)
        self.stop_button.setFixedHeight(60)
        self.stop_button.clicked.connect(self.stop_monitoring)
        self.button_layout.addWidget(self.stop_button)

        self.remove_button = QPushButton(language_resources[self.current_language]['Remove monitoring'], self)
        self.set_button_width(self.remove_button)
        self.remove_button.setFixedHeight(60)
        self.remove_button.clicked.connect(self.remove_monitoring)
        self.button_layout.addWidget(self.remove_button)

        self.layout.addLayout(self.button_layout)

        self.right_layout = QVBoxLayout()

        self.status_label = QLabel(_("Monitoring status: Unknown"), self)
        self.right_layout.addWidget(self.status_label)

        self.output_area_deploy = QTextEdit(self)
        self.output_area_deploy.setReadOnly(True)
        self.output_area_deploy.setPlaceholderText(_('Deployment monitoring output...'))
        self.right_layout.addWidget(self.output_area_deploy)

        self.output_area_start = QTextEdit(self)
        self.output_area_start.setReadOnly(True)
        self.output_area_start.setPlaceholderText(_('Start monitoring output...'))
        self.right_layout.addWidget(self.output_area_start)

        self.output_area_check = QTextEdit(self)
        self.output_area_check.setReadOnly(True)
        self.output_area_check.setPlaceholderText(_('Checking the deployment status output...'))
        self.right_layout.addWidget(self.output_area_check)

        self.output_area_stop = QTextEdit(self)
        self.output_area_stop.setReadOnly(True)
        self.output_area_stop.setPlaceholderText(_('Stop monitoring output...'))
        self.right_layout.addWidget(self.output_area_stop)

        self.output_area_remove = QTextEdit(self)
        self.output_area_remove.setReadOnly(True)
        self.output_area_remove.setPlaceholderText(_('Remove monitoring output...'))
        self.right_layout.addWidget(self.output_area_remove)

        self.layout.addLayout(self.right_layout)
        self.setLayout(self.layout)

        self.monitoring_thread = None
    def set_button_width(self, button):
        font_metrics = QFontMetrics(button.font())
        text_width = font_metrics.horizontalAdvance(button.text())

        button.setFixedWidth(max(text_width + 20, 150))


    def get_text(self, key):
        try:
            return language_resources[self.current_language][key]
        except KeyError as e:
            print(f"KeyError: {e} - key not found in language_resources")
            return key

    def update_language(self, language):
        self.current_language = language
        self.deploy_button.setText(self.get_text('Deployment monitoring'))
        self.start_button.setText(self.get_text('Start monitoring'))
        self.check_button.setText(self.get_text('Checking the deployment status'))
        self.stop_button.setText(self.get_text('Stop monitoring'))
        self.remove_button.setText(self.get_text('Remove monitoring'))
        self.status_label.setText(self.get_text('Monitoring status: Unknown'))

        self.set_button_width(self.deploy_button)
        self.set_button_width(self.start_button)
        self.set_button_width(self.check_button)
        self.set_button_width(self.stop_button)
        self.set_button_width(self.remove_button)

    def deploy_monitoring(self):
        self.clear_output_area()
        self.run_command('deploy')

    def check_deployment_status(self):
        self.clear_output_area()
        self.run_command('status')

    def start_monitoring(self):
        self.clear_output_area()
        if self.monitoring_thread and self.monitoring_thread.isRunning():
            self.output_area_start.append(_('Monitoring is already running.'))
        else:
            self.run_command('start_monitoring')

    def stop_monitoring(self):
        self.clear_output_area()
        self.run_command('stop_monitoring')

    def remove_monitoring(self):
        self.clear_output_area()
        self.run_command('remove')

    def run_command(self, command):
        if command == 'start_monitoring' and self.monitoring_thread is not None and self.monitoring_thread.isRunning():
            self.monitoring_thread._is_running = False

        thread = ShellCommandThread(command, self.get_output_widget(command))
        thread.output_signal.connect(self.get_output_widget(command).append)
        thread.error_signal.connect(self.get_output_widget(command).append)
        thread.finished_signal.connect(lambda: self.get_output_widget(command).append(_("Operation completed")))
        thread.status_signal.connect(self.update_status_label)
        self.monitoring_thread = thread
        thread.start()

    def get_output_widget(self, command):
        if command == 'deploy':
            return self.output_area_deploy
        elif command == 'status':
            return self.output_area_check
        elif command == 'start_monitoring':
            return self.output_area_start
        elif command == 'stop_monitoring':
            return self.output_area_stop
        elif command == 'remove':
            return self.output_area_remove

    def clear_output_area(self):
        self.output_area_deploy.clear()
        self.output_area_check.clear()
        self.output_area_remove.clear()
        self.output_area_start.clear()
        self.output_area_stop.clear()

    def update_status_label(self, status_text):
        self.status_label.setText(_("Monitoring status: {}").format(status_text))
