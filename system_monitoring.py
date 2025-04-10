import subprocess
import requests
from PySide2.QtWidgets import QWidget, QMessageBox

class SystemMonitoring(QWidget):
    def __init__(self):
        super().__init__()

    def open_grafana(self):
        grafana_url = "http://localhost:3000"

        try:
            response = requests.get(grafana_url, timeout=5)
            if response.status_code == 200:
                subprocess.Popen(
                    ["google-chrome", grafana_url],
                    stderr=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    start_new_session=True
                )
            else:
                self.show_error_dialog("Unexpected Status Code", 
                                       f"Grafana returned unexpected status code: {response.status_code}")
        except requests.ConnectionError:
            self.show_error_dialog("Grafana Not Running", 
                                   "Grafana is not running. Please start the Grafana server.")
        except Exception as e:
            self.show_error_dialog("Error", f"An error occurred while opening Grafana: {e}")

    def show_error_dialog(self, title, message):
        error_dialog = QMessageBox(self)
        error_dialog.setIcon(QMessageBox.Critical)
        error_dialog.setWindowTitle(title)
        error_dialog.setText(message)
        error_dialog.exec_()

