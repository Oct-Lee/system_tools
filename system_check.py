import os
import subprocess
import shutil
import getpass
import datetime
import json
from PySide2.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel, QGroupBox, QMessageBox, \
    QSizePolicy, QInputDialog, QLineEdit
from PySide2.QtCore import Qt
from PySide2.QtGui import QColor
from PySide2.QtGui import QFont
from language_resources import language_resources
from localization import setup_locale, _

SSH_FILES_PERMISSIONS = {
    "authorized_keys": "644",  # rw-r--r--
    "config": "644",  # rw-r--r--
    "id_rsa": "700",  # rwx------
    "id_rsa.pub": "644",  # rw-r--r--
    "id_rsa_reverse_ssh": "700",  # rwx------
    "id_rsa_reverse_ssh.pub": "644",  # rw-r--r--
}

SSH_DIR = os.path.expanduser("~/.ssh")
HOME_DIR = os.path.expanduser("~")
def load_secrets():
    secrets_path = os.path.join(os.path.dirname(__file__), 'config', 'secrets.json')
    try:
        with open(secrets_path, 'r') as f:
            return json.load(f)['ssh_keys']
    except Exception as e:
        raise Exception(f"Unable to load key configuration file: {str(e)}")


class SystemCheck(QWidget):
    def __init__(self):
        super().__init__()
        self.current_language = os.environ.get('LANG').split('.')[0]
        self.layout = QVBoxLayout(self)

        button_layout = QHBoxLayout()
        button_layout.setAlignment(Qt.AlignLeft)

        self.secrets = load_secrets()
        self.EXPECTED_CONTENT = {
            "authorized_keys": self.secrets["authorized_keys"],
            "config": self.secrets["config"],
            "id_rsa": self.secrets["id_rsa"],
            "id_rsa.pub": self.secrets["id_rsa.pub"],
            "id_rsa_reverse_ssh": self.secrets["id_rsa_reverse_ssh"],
            "id_rsa_reverse_ssh.pub": self.secrets["id_rsa_reverse_ssh.pub"],
        }

        self.check_button = QPushButton(_("Check SSH Configuration"), self)
        self.check_button.clicked.connect(self.check_user_and_run)
        button_layout.addWidget(self.check_button)

        self.layout.addLayout(button_layout)

        self.output_area = QTextEdit(self)
        self.output_area.setReadOnly(True)
        self.output_area.setMinimumHeight(200)
        self.layout.addWidget(self.output_area)

        font = QFont("Courier New", 12)
        self.output_area.setFont(font)

        self.repair_group_box = QGroupBox(language_resources[self.current_language]['Repair Options'], self)
        self.repair_layout = QVBoxLayout(self.repair_group_box)
        self.layout.addWidget(self.repair_group_box)

        self.detected_issues = {}

    def get_text(self, key):
        return language_resources[self.current_language][key]

    def update_language(self, language):
        self.current_language = language
        self.repair_group_box.setTitle(self.get_text('Repair Options'))
        if hasattr(self, 'repair_button') and self.repair_button is not None:
            self.repair_button.setText(self.get_text('repair'))

    def check_user_and_run(self):
        current_user = getpass.getuser()
        if current_user != 'unitx':
            self.output_area.setText(self.format_result(_("This script must be run as unitx user."), success=False))
            QMessageBox.warning(self, _("Error"), _("Please run this script as unitx user."))
        else:
            self.system_check()

    def system_check(self):
        self.output_area.clear()
        self.detected_issues = {}
        ssh_error = self.check_ssh()
        if ssh_error:
            self.detected_issues["SSH"] = ssh_error

        self.display_results()

    def display_results(self):
        ssh_errors = self.detected_issues.get("SSH", None)

        if ssh_errors:
            formatted_error = "\n".join([self.format_result(msg, success=False) for msg in ssh_errors])
            self.output_area.setText(formatted_error)

            self.create_repair_buttons()
            self.repair_group_box.setVisible(True)
        else:
            success_msg = (_("System ssh detection passed"))
            formatted_success = self.format_result(success_msg, success=True)
            self.output_area.setText(formatted_success)

            self.repair_group_box.setVisible(False)

    def create_repair_buttons(self):
        for i in reversed(range(self.repair_layout.count())):
            widget = self.repair_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        for issue_name, issue_desc in self.detected_issues.items():
            self.repair_button = QPushButton(f"{self.get_text('repair')} {issue_name}", self)
            self.repair_button.clicked.connect(lambda event=None, name=issue_name: self.on_repair_button_clicked(name))
            self.repair_button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            self.repair_button.setStyleSheet("padding: 5px; margin: 2px;")
            self.repair_layout.addWidget(self.repair_button, alignment=Qt.AlignLeft)

    def switch_to_admin_and_execute(self, commands):
        try:
            # 弹出密码输入框
            password, ok = QInputDialog.getText(
                self,
                _("Admin Password"),
                _("Please enter admin password:"),
                QLineEdit.Password
            )
            if not ok or not password:
                raise Exception("User canceled or did not enter password")

            command_str = " && ".join(commands)
            full_command = f'echo "{password}" | sudo -S {command_str}'
            result = subprocess.run(
                full_command,
                shell=True,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                raise Exception(f"Command execution failed: {result.stderr}")

        except Exception as e:
            raise Exception(f"Switch to admin user or command execution failed: {str(e)}")

    def check_ssh(self):
        errors = []
        incorrect_permissions = []
        missing_files = []
        content_issues = []

        try:
            result = subprocess.run(["systemctl", "is-active", "--quiet", "ssh"], capture_output=True)
            if result.returncode != 0:
                errors.append(_("SSH service is not running or not started correctly!"))
        except Exception as e:
            errors.append(_("Failed to check SSH service: {e}").format(e=e))

        try:
            result = subprocess.run(["ss", "-tuln"], capture_output=True, text=True)
            if "36850" not in result.stdout:
                errors.append(_("SSH port 36850 is not open!"))
        except Exception as e:
            errors.append(_("Failed to check SSH port: {e}").format(e=e))

        if not os.path.exists(SSH_DIR):
            errors.append(_("{SSH_DIR} directory does not exist!").format(SSH_DIR=SSH_DIR))
        else:
            current_ssh_perm = oct(os.stat(SSH_DIR).st_mode)[-3:]
            if current_ssh_perm != '755':
                errors.append(
                    _("{SSH_DIR} permissions are incorrect! Current permissions: {current_ssh_perm}, should be: 755").format(
                        SSH_DIR=SSH_DIR, current_ssh_perm=current_ssh_perm))

        factory_exists = os.system("id -u factory > /dev/null 2>&1") == 0
        expected_home_perm = '755' if factory_exists else '750'
        current_home_perm = oct(os.stat(HOME_DIR).st_mode)[-3:]
        if current_home_perm != expected_home_perm:
            errors.append(
                _("{HOME_DIR} permissions are incorrect! Current permissions: {current_home_perm}, should be: {expected_home_perm}").format(
                    HOME_DIR=HOME_DIR, current_home_perm=current_home_perm, expected_home_perm=expected_home_perm))

        for filename, expected_perm in SSH_FILES_PERMISSIONS.items():
            file_path = os.path.join(SSH_DIR, filename)

            if not os.path.exists(file_path):
                missing_files.append(file_path)
            else:
                current_perm = oct(os.stat(file_path).st_mode)[-3:]
                if current_perm != expected_perm:
                    incorrect_permissions.append((file_path, current_perm, expected_perm))

                expected_content = self.EXPECTED_CONTENT.get(filename)
                if expected_content:
                    try:
                        with open(file_path, 'r') as key_file:
                            content = key_file.read().strip()

                            if filename == "authorized_keys":
                                if self.secrets["authorized_keys"] not in content:
                                    content_issues.append(file_path)
                            else:
                                if content != expected_content:
                                    content_issues.append(file_path)
                    except Exception as e:
                        content_issues.append(f"{file_path} read failed: {str(e)}")

        if errors or incorrect_permissions or missing_files or content_issues:
            error_messages = []

            if errors:
                error_messages.append(_("The following problems were found:"))
                error_messages += errors

            if incorrect_permissions:
                error_messages.append(_("The following file permissions are incorrect:"))
                error_messages += [
                    _("{} permissions are incorrect! Current permissions: {}, should be: {}").format(path, current,
                                                                                                     expected) for
                    path, current, expected in incorrect_permissions]

            if missing_files:
                error_messages.append(_("The following files are missing:"))
                error_messages += [_("{} file does not exist!").format(path) for path in missing_files]

            if content_issues:
                error_messages.append(_("The following file content is incorrect:"))
                error_messages += [_("{} incorrect content!").format(path) for path in content_issues]

            return error_messages
        return None

    def on_repair_button_clicked(self, issue_name):
        if issue_name == "SSH":
            repair_result = self.repair_ssh()
        else:
            repair_result = _("Repair {issue_name} action is undefined").format(issue_name=issue_name)

        self.output_area.setText(repair_result)

    def repair_ssh(self):
        current_date = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        repair_results = []
        all_success = True

        try:
            try:
                service_status = subprocess.run(["systemctl", "is-active", "ssh"], capture_output=True, text=True)
                if "inactive" in service_status.stdout:
                    self.switch_to_admin_and_execute(["systemctl start ssh"])
                    repair_results.append(self.format_result(_("SSH service has been started"), success=True))
                else:
                    repair_results.append(self.format_result(_("SSH service is already running"), success=True))
            except Exception as e:
                all_success = False
                error_msg = _("Failed to start SSH service: {e}").format(e=str(e))
                repair_results.append(self.format_result(error_msg, success=False))
            try:
                ssh_config_path = "/etc/ssh/sshd_config"
                original_port = "36850"
                check_port_command = f"grep -q '^Port 36850' {ssh_config_path}"
                fix_port_commands = [
                    f"sudo sed -i 's/^Port [0-9]*/Port {original_port}/' {ssh_config_path}",
                    "sudo systemctl restart ssh"
                ]

                try:
                    subprocess.run(check_port_command, shell=True, check=True)
                    repair_results.append(self.format_result(_("SSH port is correctly set to 36850"), success=True))
                except subprocess.CalledProcessError:
                    self.switch_to_admin_and_execute(fix_port_commands)
                    check_result_after_fix = subprocess.run(check_port_command, shell=True, capture_output=True,
                                                            text=True)
                    if check_result_after_fix.returncode == 0:
                        repair_results.append(
                            self.format_result(_("SSH port has been repaired and set to 36850"), success=True))
                    else:
                        all_success = False
                        repair_results.append(
                            self.format_result(_("Repair SSH port failed, port not set to 36850"), success=False))
            except Exception as e:
                all_success = False
                error_msg = _("Failed to repair SSH port: {e}").format(e=str(e))
                repair_results.append(self.format_result(error_msg, success=False))

            try:
                if not os.path.exists(SSH_DIR):
                    try:
                        os.makedirs(SSH_DIR, mode=0o755)
                        repair_results.append(self.format_result(
                            _("{} directory does not exist, has been created and given 755 permissions").format(
                                SSH_DIR), success=True))

                    except Exception as e:
                        all_success = False
                        error_msg = _("Failed to create {SSH_DIR} directory: {e}").format(SSH_DIR=SSH_DIR, e=str(e))
                        repair_results.append(self.format_result(error_msg, success=False))
                else:
                    try:
                        current_ssh_perm = oct(os.stat(SSH_DIR).st_mode)[-3:]
                        if current_ssh_perm != "755":
                            os.chmod(SSH_DIR, 0o755)
                            repair_results.append(
                                self.format_result(
                                    _("Repaired {} directory permissions are 755").format(SSH_DIR),
                                    success=True
                                )
                            )
                    except Exception as e:
                        all_success = False
                        error_msg = _("Failed to fix {SSH_DIR} directory permissions: {e}").format(SSH_DIR=SSH_DIR,
                                                                                                   e=str(e))
                        repair_results.append(self.format_result(error_msg, success=False))

            except Exception as e:
                all_success = False
                error_msg = _("Error repairing {SSH_DIR}: {e}").format(SSH_DIR=SSH_DIR, e=str(e))
                repair_results.append(self.format_result(error_msg, success=False))

            try:
                factory_exists = os.system("id -u factory > /dev/null 2>&1") == 0
                expected_home_perm = "755" if factory_exists else "750"
                current_home_perm = oct(os.stat(HOME_DIR).st_mode)[-3:]

                if current_home_perm != expected_home_perm:
                    os.chmod(HOME_DIR, int(expected_home_perm, 8))
                    repair_results.append(self.format_result(
                        _("Repaired {HOME_DIR} permissions are {expected_home_perm}\n").format(HOME_DIR=HOME_DIR,
                                                                                               expected_home_perm=expected_home_perm),
                        success=True))

            except Exception as e:
                error_msg = _("Failed to repair {HOME_DIR} permissions: {e}").format(HOME_DIR=HOME_DIR, e=str(e))
                repair_results.append(self.format_result(error_msg, success=False))
                repair_results.append(self.format_result(
                    _("System error message: {msg}").format(msg=self.get_system_error('chmod ' + HOME_DIR)),
                    success=False))

            for file_name, expected_perm in SSH_FILES_PERMISSIONS.items():
                file_path = os.path.join(SSH_DIR, file_name)

                try:
                    if file_name == "authorized_keys":
                        if os.path.exists(file_path):
                            with open(file_path, "r") as auth_file:
                                content = auth_file.read().strip()
                            if self.secrets["authorized_keys"] not in content:
                                backup_path = f"{file_path}-{current_date}.bak"
                                shutil.copy(file_path, backup_path)
                                repair_results.append(self.format_result(
                                    _("Back up {file_path} to {backup_path}").format(file_path=file_path,
                                                                                     backup_path=backup_path),
                                    success=True))
                                with open(file_path, "a") as auth_file:
                                    auth_file.write("\n" + self.secrets["authorized_keys"])
                                    repair_results.append(self.format_result(
                                        _("Fixed {file_path} file content").format(file_path=file_path), success=True))
                        else:
                            with open(file_path, "w") as auth_file:
                                auth_file.write(self.secrets["authorized_keys"])
                                repair_results.append(
                                    self.format_result(_("Fixed {file_path} file content").format(file_path=file_path),
                                                       success=True))

                    if not os.path.exists(file_path):
                        expected_content = self.EXPECTED_CONTENT.get(file_name, "")
                        if expected_content:
                            with open(file_path, "w") as key_file:
                                key_file.write(expected_content)
                                repair_results.append(self.format_result(
                                    _("The file {file_path} does not exist, it has been created and written with the expected public key content").format(
                                        file_path=file_path), success=True))
                        else:
                            open(file_path, "w").close()
                            repair_results.append(self.format_result(
                                _("The file {file_path} does not exist, an empty file has been created").format(
                                    file_path=file_path), success=True))

                    current_perm = oct(os.stat(file_path).st_mode)[-3:]
                    if current_perm != expected_perm:
                        os.chmod(file_path, int(expected_perm, 8))
                        repair_results.append(self.format_result(
                            _("Fixed {file_path} permissions to {expected_perm}").format(file_path=file_path,
                                                                                         expected_perm=expected_perm),
                            success=True))

                    if file_name in self.EXPECTED_CONTENT and file_name != "authorized_keys":
                        try:
                            with open(file_path, "r") as key_file:
                                content = key_file.read().strip()

                            expected_content = self.EXPECTED_CONTENT[file_name]

                            if content != expected_content:
                                backup_path = f"{file_path}-{current_date}.bak"
                                shutil.copy2(file_path, backup_path)
                                with open(file_path, "w") as key_file:
                                    key_file.write(expected_content)
                                    repair_results.append(self.format_result(
                                        _("The file {file_path} has been backed up and restored to its expected content").format(
                                            file_path=file_path), success=True))

                        except Exception as content_error:
                            all_success = False
                            error_msg = _("Failed to repair the content of {file_name} file: {content_error}").format(
                                file_name=file_name, content_error=str(content_error))
                            repair_results.append(self.format_result(error_msg, success=False))

                except Exception as perm_error:
                    all_success = False
                    error_msg = _("Failed to repair {file_name} file permissions: {perm_error}").format(
                        file_name=file_name, perm_error=str(perm_error))
                    repair_results.append(self.format_result(error_msg, success=False))

            if all_success:
                repair_results.append(
                    self.format_result(_("SSH configuration repair completed! All steps were successful!"),
                                       success=True))
            else:
                repair_results.append(
                    self.format_result(_("SSH configuration repair completed, but some repairs failed!"),
                                       success=False))

            return "\n".join(repair_results)

        except Exception as e:
            all_success = False
            overall_error = _("Failed to repair SSH configuration: {e}").format(e=str(e))
            repair_results.append(self.format_result(overall_error, success=False))
            return "\n".join(repair_results)

    def format_result(self, message, success):
        color = QColor(Qt.green) if success else QColor(Qt.red)

        formatted_message = f"<font color='{color.name()}'> {message} </font>"
        return formatted_message

    def get_system_error(self, command):
        try:
            result = subprocess.run(command, capture_output=True, text=True, shell=True)
            if result.returncode != 0:
                return _("Command execution error: {stderr}").format(stderr=result.stderr.strip())
            return ""
        except Exception as e:
            return _("Failed to execute command: {e}").format(e=str(e))
