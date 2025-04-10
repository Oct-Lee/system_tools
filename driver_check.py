import subprocess
from PySide2.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit
from PySide2.QtGui import QFont
import os
from language_resources import language_resources
from localization import setup_locale, _

class DriverCheck(QWidget):
    def __init__(self):
        super().__init__()
        self.current_language = os.environ.get('LANG').split('.')[0]

        layout = QVBoxLayout()

        self.title_label = QLabel(language_resources[self.current_language]['GPU driver detection'], self)
        layout.addWidget(self.title_label)

        self.output_area = QTextEdit(self)
        self.output_area.setReadOnly(True)

        font = QFont("Courier New", 12)
        self.output_area.setFont(font)

        layout.addWidget(self.output_area)

        self.setLayout(layout)

    def get_text(self, key):
        return language_resources[self.current_language][key]

    def update_language(self, language):
        self.current_language = language
        self.title_label.setText(self.get_text('GPU driver detection'))

    def check_drivers(self):
        self.output_area.clear()
        self.output_area.append(_('Checking GPU driver status...'))

        try:
            nvidia_output = subprocess.check_output("lspci | grep -i nvidia", shell=True, encoding='utf-8')
            if nvidia_output:
                self.output_area.append("NVIDIA GPU:")
                self.output_area.append(nvidia_output)

                try:
                    driver_output = subprocess.check_output(['nvidia-smi'], encoding='utf-8', errors='replace')
                    self.output_area.append(_('NVIDIA driver information:'))
                    self.output_area.append(driver_output)
                except subprocess.CalledProcessError:
                    self.output_area.append(_("NVIDIA driver is not installed or cannot be accessed."))
            else:
                self.output_area.append(_("NVIDIA GPU not found, driver may need to be installed."))
        except Exception as e:
            self.output_area.append(_("Error checking GPU driver: ") + str(e))

