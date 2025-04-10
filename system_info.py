import subprocess
import logging
import os
import getpass
import socket
from PySide2.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLabel, QPushButton, QHBoxLayout, QMessageBox, QTableWidget, QTableWidgetItem, QDialog, QLineEdit, QDialogButtonBox, QComboBox
from PySide2.QtCore import Qt, Signal
from PySide2.QtGui import QFont
from PySide2.QtWidgets import QInputDialog
from language_resources import language_resources
from localization import setup_locale, _

from PySide2.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QLabel, QDialogButtonBox, QPushButton, QComboBox, QHBoxLayout
import subprocess

from PySide2.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QLabel, QDialogButtonBox, QPushButton, QComboBox, QHBoxLayout
import subprocess

class InputDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("SSHFS Mount/Unmount")
        self.setFixedSize(400, 250)


        layout = QVBoxLayout()

        self.operation_label = QLabel("Select Operation:", self)
        self.operation_combo = QComboBox(self)
        self.operation_combo.addItem("Mount")
        self.operation_combo.addItem("Unmount")
        self.operation_combo.currentIndexChanged.connect(self.update_ui_based_on_operation)

        self.operation_combo.adjustSize()
        self.operation_combo.setMinimumWidth(self.operation_combo.sizeHint().width())
        self.operation_combo.setMaximumWidth(self.operation_combo.sizeHint().width())

        self.ip_label = QLabel("Enter the IP address:", self)
        self.ip_input = QLineEdit(self)
        self.ip_input.setPlaceholderText("e.g. 192.168.10.2")

        self.source_dir_label = QLabel("Enter the source directory:", self)
        self.source_dir_input = QLineEdit(self)
        self.source_dir_input.setPlaceholderText("e.g. /home/unitx/")

        self.target_dir_label = QLabel("Enter the target directory:", self)
        self.target_dir_input = QLineEdit(self)
        self.target_dir_input.setPlaceholderText("e.g. /home/unitx/test")

        button_layout = QHBoxLayout()

        self.mount_button = QPushButton("Mount", self)
        self.mount_button.clicked.connect(self.on_mount_button_clicked)

        self.unmount_button = QPushButton("Unmount", self)
        self.unmount_button.clicked.connect(self.on_unmount_button_clicked)

        button_layout.addWidget(self.mount_button)
        button_layout.addWidget(self.unmount_button)

        layout.addWidget(self.operation_label)
        layout.addWidget(self.operation_combo)
        layout.addWidget(self.ip_label)
        layout.addWidget(self.ip_input)
        layout.addWidget(self.source_dir_label)
        layout.addWidget(self.source_dir_input)
        layout.addWidget(self.target_dir_label)
        layout.addWidget(self.target_dir_input)
        layout.addLayout(button_layout)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Cancel, self)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.setLayout(layout)

        self.update_ui_based_on_operation()


    def get_inputs(self):
        return self.ip_input.text(), self.source_dir_input.text(), self.target_dir_input.text()

    def update_ui_based_on_operation(self):
        operation = self.operation_combo.currentText()
        if operation == "Unmount":
            self.mount_button.setEnabled(False)
            self.unmount_button.setEnabled(True)
            self.ip_input.setDisabled(True)
            self.source_dir_input.setDisabled(True)
            self.target_dir_input.setEnabled(True)
            self.ip_input.setStyleSheet("background-color: lightgray;")
            self.source_dir_input.setStyleSheet("background-color: lightgray;")
            self.target_dir_input.setStyleSheet("background-color: white;")
        else:
            self.mount_button.setEnabled(True)
            self.unmount_button.setEnabled(False)
            self.ip_input.setEnabled(True)
            self.source_dir_input.setEnabled(True)
            self.target_dir_input.setEnabled(True)
            self.ip_input.setStyleSheet("background-color: white;")
            self.source_dir_input.setStyleSheet("background-color: white;")
            self.target_dir_input.setStyleSheet("background-color: white;")

    def on_mount_button_clicked(self):
        ip, source_dir, target_dir = self.get_inputs()
        if not ip or not source_dir or not target_dir:
            QMessageBox.warning(self, "Input Error", "Please provide all required inputs: IP, source directory, and target directory.")
            return

        try:
            sock = socket.create_connection((ip, 36850), timeout=1)
            sock.close()
        except socket.timeout:
            QMessageBox.warning(self, "Network Error", f"Unable to reach IP address: {ip} within timeout. Please check the network connection.")
            return
        except socket.error as e:
            QMessageBox.warning(self, "Network Error", f"Unable to connect to IP address: {ip} on port 36850. Error: {e}")
            return
        except Exception as e:
            QMessageBox.warning(self, "Network Error", f"An unexpected error occurred: {e}")
            return

        command = f"sshfs -p 36850 unitx@{ip}:{source_dir} {target_dir}"
        try:
            result = subprocess.run(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
            )

            if result.returncode == 0:
                QMessageBox.information(self, "Success", f"Successfully mounted {source_dir} at {target_dir}")
            else:
                error_message = result.stderr
                QMessageBox.warning(self, "Command Failed", f"Command failed: {error_message}")

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error while executing command: {e}")

    def on_unmount_button_clicked(self):
        target_dir = self.target_dir_input.text()
        if not target_dir:
            QMessageBox.warning(self, "Input Error", "Please provide the target directory to unmount.")
            return

        try:
            command = f"fusermount -u {target_dir}"
            subprocess.run(command, shell=True, check=True)
            QMessageBox.information(self, "Success", f"Successfully unmounted {target_dir}")
        except subprocess.CalledProcessError as e:
            QMessageBox.warning(self, "Unmount Error", f"Error while unmounting: {e}")

class SystemInfoCheck(QWidget):
    def __init__(self):
        super().__init__()
        self.current_language = os.environ.get('LANG').split('.')[0]
        self.initUI()
    def initUI(self):
        layout = QVBoxLayout()

        button_layout = QHBoxLayout()

        self.run_button = QPushButton(language_resources[self.current_language]['System self-check'], self)
        self.run_button.setFixedSize(100, 30)
        self.run_button.setFont(QFont("Arial", 8))
        self.run_button.clicked.connect(self.on_init_check_button_clicked)
        button_layout.addWidget(self.run_button)

        button_layout.addSpacing(2)

        self.query_disk_button = QPushButton(language_resources[self.current_language]['Disk space check'], self)
        self.query_disk_button.setFixedSize(100, 30)
        self.query_disk_button.setFont(QFont("Arial", 8))
        self.query_disk_button.clicked.connect(self.on_query_disk_button_clicked)
        button_layout.addWidget(self.query_disk_button)

        self.os_info_button = QPushButton(language_resources[self.current_language]['Operating system information'], self)
        self.os_info_button.setFont(QFont("Arial", 8))
        self.os_info_button.setFixedHeight(30)
        self.os_info_button.setMinimumWidth(self.os_info_button.sizeHint().width())
        self.os_info_button.clicked.connect(self.on_get_os_info_button_clicked)
        button_layout.addWidget(self.os_info_button)

        self.mount_disk_button = QPushButton(language_resources[self.current_language]['Disk mount'], self)
        self.mount_disk_button.setFixedSize(100, 30)
        self.mount_disk_button.setFont(QFont("Arial", 8))
        self.mount_disk_button.clicked.connect(self.on_mount_disk_button_clicked)
        button_layout.addWidget(self.mount_disk_button)

        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setAlignment(Qt.AlignLeft)

        layout.addLayout(button_layout)

        self.output_area = QTextEdit(self)
        self.output_area.setReadOnly(True)
        font = QFont("Courier New", 12)
        self.output_area.setFont(font)
        layout.addWidget(self.output_area)

        label_table_layout = QHBoxLayout()
        self.disk_label = QLabel(language_resources[self.current_language]['Disk space usage'], self)
        self.disk_label.setVisible(False)
        self.disk_table_layout = QVBoxLayout()
        self.disk_table_layout.addWidget(self.disk_label)

        self.disk_table = QTableWidget(self)
        self.disk_table.setVisible(False)
        self.disk_table.setSizeAdjustPolicy(QTableWidget.AdjustToContents)
        self.disk_table_layout.addWidget(self.disk_table)

        label_table_layout.addLayout(self.disk_table_layout)

        self.inode_label = QLabel(language_resources[self.current_language]['Inode Usage'], self)
        self.inode_label.setVisible(False)
        self.inode_table_layout = QVBoxLayout()
        self.inode_table_layout.addWidget(self.inode_label)

        self.inode_table = QTableWidget(self)
        self.inode_table.setVisible(False)
        self.inode_table.setSizeAdjustPolicy(QTableWidget.AdjustToContents)
        self.inode_table_layout.addWidget(self.inode_table)

        label_table_layout.addLayout(self.inode_table_layout)

        layout.addLayout(label_table_layout)

        action_button_layout = QHBoxLayout()
        self.disk_analysis_button = QPushButton(language_resources[self.current_language]['Disk Usage Analyzer'], self)
        self.disk_analysis_button.setFixedSize(150, 30)
        self.disk_analysis_button.setFont(QFont("Arial", 8))
        self.disk_analysis_button.clicked.connect(self.on_disk_usage_analysis_button_clicked)
        self.disk_analysis_button.setVisible(False)
        action_button_layout.addWidget(self.disk_analysis_button)

        action_button_layout.addSpacing(2)

        self.disk_monitor_button = QPushButton(language_resources[self.current_language]['Disk monitor deployment'], self)
        self.disk_monitor_button.setFixedSize(150, 30)
        self.disk_monitor_button.setFont(QFont("Arial", 8))
        self.disk_monitor_button.clicked.connect(self.on_disk_monitor_button_clicked)
        self.disk_monitor_button.setVisible(False)
        action_button_layout.addWidget(self.disk_monitor_button)

        self.button1 = QPushButton(language_resources[self.current_language]['Mounting the data disk'], self)
        self.button1.setFont(QFont("Arial", 8))
        self.button1.setFixedHeight(30)
        self.button1.setMinimumWidth(self.button1.sizeHint().width())
        self.button1.clicked.connect(self.on_button1_clicked)
        self.button1.setVisible(False)
        action_button_layout.addWidget(self.button1)

        self.button2 = QPushButton(language_resources[self.current_language]['SSHFS Mount / Unmount'], self)
        self.button2.setFont(QFont("Arial", 8))
        self.button2.setFixedHeight(30)
        self.button2.setMinimumWidth(self.button2.sizeHint().width())
        self.button2.clicked.connect(self.on_button2_clicked)
        self.button2.setVisible(False)
        action_button_layout.addWidget(self.button2)

        self.button3 = QPushButton(language_resources[self.current_language]['Mount Share'], self)
        self.button3.setFont(QFont("Arial", 8))
        self.button3.setFixedHeight(30)
        self.button3.setMinimumWidth(self.button3.sizeHint().width())
        self.button3.clicked.connect(self.on_button3_clicked)
        self.button3.setVisible(False)
        action_button_layout.addWidget(self.button3)

        self.button4 = QPushButton(language_resources[self.current_language]['Button 4'], self)
        self.button4.setFont(QFont("Arial", 8))
        self.button4.setFixedHeight(30)
        self.button4.setMinimumWidth(self.button4.sizeHint().width())
        self.button4.setVisible(False)
        action_button_layout.addWidget(self.button4)

        layout.addLayout(action_button_layout)
        action_button_layout.setAlignment(Qt.AlignLeft)

        self.setLayout(layout)

    def get_text(self, key):
        return language_resources[self.language][key]

    def update_language(self, language):
        self.language = language
        self.run_button.setText(self.get_text('System self-check'))
        self.query_disk_button.setText(self.get_text('Disk space check'))
        self.os_info_button.setText(self.get_text('Operating system information'))
        self.disk_analysis_button.setText(self.get_text('Disk Usage Analyzer'))
        self.disk_monitor_button.setText(self.get_text('Disk monitor deployment'))
        self.disk_label.setText(self.get_text('Disk space usage'))
        self.inode_label.setText(self.get_text('Inode Usage'))
        self.mount_disk_button.setText(self.get_text('Disk mount'))
        self.button1.setText(self.get_text('Mounting the data disk'))
        self.button2.setText(self.get_text('SSHFS Mount / Unmount'))
        self.button3.setText(self.get_text('Mount Share'))

    def on_mount_disk_button_clicked(self):
        self.clear_button_styles()
        self.mount_disk_button.setStyleSheet("border: 2px solid #ADD8E6;")
        self.output_area.clear()
        self.clear_disk_and_inode_info()
        self.disk_analysis_button.setVisible(False)
        self.disk_monitor_button.setVisible(False)

        self.button1.setVisible(True)
        self.button2.setVisible(True)
        self.button3.setVisible(True)
        self.button4.setVisible(False)


    def on_init_check_button_clicked(self):
        self.clear_button_styles()
        self.run_button.setStyleSheet("border: 2px solid #ADD8E6;")
        self.run_init_check_script()

        self.output_area.clear()

        self.clear_disk_and_inode_info()
        self.output_area.setVisible(True)
        self.disk_analysis_button.setVisible(False)
        self.disk_monitor_button.setVisible(False)
        self.button1.setVisible(False)
        self.button2.setVisible(False)
        self.button3.setVisible(False)
        self.button4.setVisible(False)

    def on_query_disk_button_clicked(self):
        self.clear_button_styles()
        self.output_area.clear()
        self.query_disk_button.setStyleSheet("border: 2px solid #ADD8E6;")
        self.check_disk_usage()

        self.disk_label.setVisible(True)
        self.disk_table.setVisible(True)
        self.inode_label.setVisible(True)
        self.inode_table.setVisible(True)

        self.disk_analysis_button.setVisible(True)
        self.disk_monitor_button.setVisible(True)
        self.button1.setVisible(False)
        self.button2.setVisible(False)
        self.button3.setVisible(False)
        self.button4.setVisible(False)

    def on_get_os_info_button_clicked(self):
        self.clear_button_styles()
        self.os_info_button.setStyleSheet("border: 2px solid #ADD8E6;")
        os_info = self.get_os_and_kernel_info()
        self.output_area.clear()
        self.output_area.append(os_info)

        self.clear_disk_and_inode_info()
        self.disk_analysis_button.setVisible(False)
        self.disk_monitor_button.setVisible(False)
        self.button1.setVisible(False)
        self.button2.setVisible(False)
        self.button3.setVisible(False)
        self.button4.setVisible(False)
        self.output_area.setVisible(True)

    def on_disk_usage_analysis_button_clicked(self):
        self.clear_button_styles()
        self.query_disk_button.setStyleSheet("border: 2px solid #ADD8E6;")
        self.disk_analysis_button.setStyleSheet("border: 2px solid #ADD8E6;")
        try:
            subprocess.Popen(['baobab'])
        except Exception as e:
            self.output_area.append(_("Unable to start disk usage analysis: {e}").format(e=e))

    def on_disk_monitor_button_clicked(self):
        self.output_area.clear()
        self.clear_button_styles()
        self.query_disk_button.setStyleSheet("border: 2px solid #ADD8E6;")
        self.disk_monitor_button.setStyleSheet("border: 2px solid #ADD8E6;")

        script_dir = os.path.dirname(os.path.abspath(__file__))
        autostart_dir = os.path.join(os.environ["HOME"], ".config", "autostart")
        autostart_file = os.path.join(autostart_dir, "delayed_run_disk_check.desktop")

        if os.path.isfile(autostart_file):
            self.output_area.append(_("Autostart entry already exists, no need to recreate."))
            return

        os.makedirs(autostart_dir, exist_ok=True)

        try:
            with open(autostart_file, 'w') as f:
                f.write(f"""[Desktop Entry]
Name=Delayed Run Disk Check Script
Exec=nohup bash "{script_dir}/delayed_run_disk_check.sh" > /dev/null 2>&1 & disown
Type=Application
X-GNOME-Autostart-enabled=true
""")
            os.chmod(autostart_file, 0o755)
            self.output_area.append(_("The task has been added to autostart."))
        except Exception as e:
            self.output_area.append(f"{_('Error')}: {e}")
            return
        try:
            if not self.is_script_running(script_dir):
                subprocess.Popen(
                    f'nohup bash -c "bash {script_dir}/delayed_run_disk_check.sh > /dev/null 2>&1 & disown" > /dev/null 2>&1 &',
                    shell=True)
                self.output_area.append(_("The scheduled task has been run and will be executed at 10 am every day."))
            else:
                self.output_area.append(_("The scheduled task is already running and will be executed at 10 am every day."))
        except Exception as e:
            self.output_area.append(f"{_('Error')}: {e}")

    def is_script_running(self, script_dir):
        try:
            result = subprocess.run(['pgrep', '-f', f'{script_dir}/delayed_run_disk_check.sh'],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return bool(result.stdout)
        except subprocess.CalledProcessError:
            return False
        
    def clear_button_styles(self):
        self.run_button.setStyleSheet("")
        self.query_disk_button.setStyleSheet("")
        self.disk_analysis_button.setStyleSheet("")
        self.os_info_button.setStyleSheet("")
        self.mount_disk_button.setStyleSheet("")
        self.disk_analysis_button.setStyleSheet("")
        self.disk_monitor_button.setStyleSheet("")

    def clear_disk_and_inode_info(self):
        self.disk_label.setVisible(False)
        self.disk_table.setVisible(False)
        self.inode_label.setVisible(False)
        self.inode_table.setVisible(False)

        self.disk_table.clear()
        self.inode_table.clear()

    def run_init_check_script(self):
        try:
            current_user = getpass.getuser()
            if current_user != 'unitx':
                QMessageBox.warning(self, "Tip", "Please switch to unitx user operation")
                return

            current_dir = os.path.dirname(os.path.abspath(__file__))

            init_check_script = os.path.join(current_dir, 'init_check.py')

            command = [
                'gnome-terminal',
                '--',
                'zsh', '-i', '-c',
                f'/home/unitx/miniconda3/envs/unified_production/bin/python {init_check_script}; exec zsh'
            ]

            terminal_process = subprocess.Popen(command)

            return "The terminal has been launched and the init_check.py script has been executed."

        except Exception as e:
            error_message = _("An error occurred while executing the script: ") + str(e)
            return error_message

    def get_system_info(self):
        try:
            df_h_info = self.get_disk_usage_info()
            df_i_info = self.get_inode_usage_info()

            self.output_area.clear()
            self.output_area.append(df_h_info)
            self.output_area.append(df_i_info)

        except Exception as e:
            self.output_area.append(_("An error occurred while getting disk information: {e}").format(e=e))

    def run_command(self, command):
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            return result.stdout.strip(), result.stderr.strip()
        except Exception as e:
            return "", str(e)

    def parse_df_output(self, output):
        lines = output.split("\n")
        headers = lines[0].split()
        data = [line.split() for line in lines[1:] if line]
        return headers, data

    def check_disk_usage(self):
        disk_output, disk_error = self.run_command("df -hPTl -x tmpfs -x efivarfs | sort")
        inode_output, inode_error = self.run_command("df -iPTl -x tmpfs -x efivarfs | grep -v \"vfat\" | sort")

        if disk_error:
            QMessageBox.warning(self, _("Disk check error"), _("Unable to get disk usage: {error}").format(error=disk_error))

        if inode_error:
            QMessageBox.warning(self, _("Inode check error"), _("Unable to obtain Inode usage: {error}").format(error=inode_error))

        disk_headers, disk_data = self.parse_df_output(disk_output)
        inode_headers, inode_data = self.parse_df_output(inode_output)

        self.update_table(self.disk_table, disk_headers, disk_data)
        self.update_table(self.inode_table, inode_headers, inode_data)

        self.check_alerts(disk_data, inode_data)

    def update_table(self, table, headers, data):
        table.setColumnCount(len(headers))
        table.setRowCount(len(data))
        table.setHorizontalHeaderLabels(headers)

        for row_idx, row in enumerate(data):
            for col_idx, col in enumerate(row):
                table.setItem(row_idx, col_idx, QTableWidgetItem(col))

        table.resizeColumnsToContents()

    def check_alerts(self, disk_data, inode_data):
        warning_messages = []

        for row in disk_data:
            if len(row) >= 5:
                usage = row[5].strip('%')
                if usage.isdigit() and int(usage) >= 90:
                    warning_messages.append(_("⚠️ {row} has used {usage}% space!").format(row=row[0], usage=usage))

        for row in inode_data:
            if len(row) >= 5:
                usage = row[5].strip('%')
                if usage.isdigit() and int(usage) >= 90:
                    warning_messages.append(_("⚠️ {row} has used {usage}% Inodes!").format(row=row[0], usage=usage))

        if warning_messages:
            alert_text = "\n".join(warning_messages)
            self.output_area.append(_("=== Disk Warning ===\n") +
                        _("Please use \"Disk Usage Analyzer\" to analyze file usage\n") +
                        alert_text + "\n")

    def get_os_and_kernel_info(self):
        try:
            os_info = subprocess.check_output("lsb_release -d", shell=True, encoding='utf-8').strip()
            kernel_info = subprocess.check_output("uname -r", shell=True, encoding='utf-8').strip()

            os_name = os_info.split(":")[1].strip()
            kernel_version = kernel_info.strip()
            return _("Operating system and kernel information:\n{os_name} (kernel version: {kernel_version})").format(os_name=os_name, kernel_version=kernel_version)

        except Exception as e:
            return _("An error occurred while getting operating system and kernel information: {e}").format(e=e)

    def run_command_in_terminal(self, command):
        try:
            process = subprocess.Popen(
                ["gnome-terminal", "--", "zsh", "-c", f"{command}; zsh"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()
            if stdout:
                print("Output:", stdout.decode())
                self.output_area.append(stdout.decode())
            if stderr:
                print("Error:", stderr.decode())
                self.output_area.append(stderr.decode())
            process.wait()
            if process.returncode != 0:
                raise Exception(f"Command failed with error: {stderr.decode()}")

        except Exception as e:
            QMessageBox.warning(self, "Execution error", f"Unable to execute command: {str(e)}")

    def on_button1_clicked(self):
        self.output_area.clear()
        current_user = getpass.getuser()
        if current_user != 'unitx':
            QMessageBox.warning(self, "Tip",  "Please switch to unitx user operation")
            return
        script_path_1 = '/unitx/scripts/2disk-setup.sh'
        script_path_2_base = '/home/unitx/prod/production_src/2disk.sh'

        if not os.path.exists(script_path_1):
            QMessageBox.warning(self, "File not found", f"Script not found at: {script_path_1}")
            return

        process_check = subprocess.Popen(["pgrep", "-f", script_path_1], stdout=subprocess.PIPE)
        process_output, _ = process_check.communicate()
        process_check.wait()

        if process_output:
            QMessageBox.warning(self, "Process running", f"The script {script_path_1} is already running.")
            return

        self.show_script_selection_dialog(script_path_1, script_path_2_base)

    def show_script_selection_dialog(self, script_path_1, script_path_2_base):
        dialog = QDialog(self)
        dialog.setWindowTitle("Mounting the data disk")
        
        dialog.setMinimumWidth(260)
        layout = QVBoxLayout(dialog)

        unmounted_disks = self.get_unmounted_disks()

        self.script_combo_box = QComboBox(dialog)
        self.script_combo_box.addItem("Run 2disk-setup.sh")
        self.script_combo_box.addItem("Run 2disk.sh")
        layout.addWidget(self.script_combo_box)

        self.operation_combo_box = QComboBox(dialog)
        self.operation_combo_box.addItem("migrate")
        self.operation_combo_box.addItem("status")
        self.operation_combo_box.addItem("unmigrate")
        self.operation_combo_box.setEnabled(False)
        layout.addWidget(self.operation_combo_box)

        self.disk_combo_box = QComboBox(dialog)
        if unmounted_disks:
            self.disk_combo_box.addItems(unmounted_disks)
        else:
            self.disk_combo_box.addItem("No unmounted disks available")
        self.disk_combo_box.setEnabled(False)
        layout.addWidget(self.disk_combo_box)

        button_ok = QPushButton("OK", dialog)
        button_ok.clicked.connect(lambda: self.run_selected_script(script_path_1, script_path_2_base, dialog))
        layout.addWidget(button_ok)

        close_button = QPushButton("Close", dialog)
        close_button.clicked.connect(dialog.close)
        layout.addWidget(close_button)

        self.script_combo_box.currentIndexChanged.connect(self.toggle_select_boxes)

        dialog.exec_()
    def run_selected_script(self, script_path_1, script_path_2_base, dialog):
        selected_script = self.script_combo_box.currentText()
        selected_operation = self.operation_combo_box.currentText()
        selected_disk = self.disk_combo_box.currentText()

        if selected_script == "Run 2disk-setup.sh":
            if selected_disk != "No unmounted disks available":
                script_path_2 = f"{script_path_2_base} {selected_operation} {selected_disk}"
                self.run_script(script_path_2, dialog)
            else:
                QMessageBox.warning(self, "Error", "Please make sure the data disk is not mounted.")
        elif selected_script == "Run 2disk.sh":
            if selected_operation in ["unmigrate", "status"]:
                script_path_2 = f"{script_path_2_base} {selected_operation}"
                print(f"Executing script: {script_path_2}")
            else:
                if selected_disk != "No unmounted disks available":
                    script_path_2 = f"{script_path_2_base} {selected_operation} {selected_disk}"
                else:
                    QMessageBox.warning(self, "Error", "Please select an unmounted disk.")
                    return
            self.run_script(script_path_2, dialog)
    def run_script(self, script_path, dialog):
        try:
            command = f"{script_path}"
            self.run_command_in_terminal(command)
            QMessageBox.information(self, "Success", f"The terminal has executed: {script_path}")
            #dialog.accept()  # Close dialog box
        except Exception as e:
            QMessageBox.warning(self, "Script Failed", f"Execution failed: {str(e)}")
        
    def get_unmounted_disks(self):
        try:
            result = subprocess.run("lsblk -o NAME,SIZE,TYPE,MOUNTPOINT | grep 'disk'", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            output = result.stdout.decode().strip()
            
            if result.stderr:
                raise Exception(result.stderr.decode().strip())

            lines = output.splitlines()

            unmounted_disks = []
            for line in lines:
                columns = line.split()
                disk_name = columns[0]
                disk_type = columns[2]
                mount_point = None

                if disk_type == 'disk':
                    root_mount = subprocess.run(['lsblk', '-n', '-o', 'MOUNTPOINT', f"/dev/{disk_name}"], stdout=subprocess.PIPE)
                    mount_point_check = root_mount.stdout.decode().strip()

                    if not mount_point_check:
                        unmounted_disks.append(f"/dev/{disk_name}")

            if not unmounted_disks:
                QMessageBox.warning(self, "Warning", "No unmounted disks found. Please check the system.")

            return unmounted_disks

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to get unmounted disks: {str(e)}")
            return []
    
    def toggle_select_boxes(self):
        selected_script = self.script_combo_box.currentText()
        if selected_script == "Run 2disk-setup.sh":
            self.operation_combo_box.setEnabled(False)
            self.disk_combo_box.setEnabled(False)
        else:
            self.operation_combo_box.setEnabled(True)
            self.disk_combo_box.setEnabled(True)

    def toggle_disk_combo_box(self):
        selected_script = self.script_combo_box.currentText()
        if selected_script == "Run 2disk-setup.sh":
            self.disk_combo_box.setEnabled(False)
        else:
            self.disk_combo_box.setEnabled(True)

    def on_button2_clicked(self):
        self.output_area.clear()
        self.input_dialog = InputDialog()
        self.input_dialog.show()

    def on_button3_clicked(self):
        server_ip = "IP"
        shared_directory = "Shared_directory"
        mount_point = "Mount_directory"
        username = "Username"
        password = "Password"

        message = (
            _("1. Open the terminal and switch to the admin user: su admin\n")
            + _("2. Edit the /etc/fstab file: sudo vim /etc/fstab\n")
            + _("3. Add the following line at the end of the file:\n")
            + _("//{server_ip}/{shared_directory} {mount_point} cifs defaults,auto,username={username},password={password},file_mode=0777,dir_mode=0777,uid=1000,gid=1000 0 0\n\n").format(
                server_ip=server_ip,
                shared_directory=shared_directory,
                mount_point=mount_point,
                username=username,
                password=password)
            + _("e.g. Replace IP, Shared_directory, mount_directory, Username, and Password with actual values.\n")
            + _("//192.168.10.2/shared /home/unitx/windows_data cifs defaults,auto,username=test,password=test,file_mode=0777,dir_mode=0777,uid=1000,gid=1000 0 0\n\n")
            + _("4. After saving and exiting the editor, run `sudo mount -a` to mount the shared directory.\n")
            + _("5. After completing this, the shared directory will be automatically mounted to {mount_point}.").format(mount_point=mount_point)
        )
        self.output_area.append(message)
