import os
import subprocess
import sys
import re
import logging
from pathlib import Path
from localization import setup_locale, _

SSH_FILES_PERMISSIONS = {
    "authorized_keys": "644",  # rw-r--r--
    "config": "644",  # rw-r--r--
    "id_rsa": "700",  # rwx------
    "id_rsa.pub": "644",  # rw-r--r--
    "id_rsa_reverse_ssh": "700",  # rwx------
    "id_rsa_reverse_ssh.pub": "644",  # rw-r--r--
}

def load_secrets():
    secrets_path = os.path.join(os.path.dirname(__file__), 'config', 'secrets.json')
    try:
        with open(secrets_path, 'r') as f:
            return json.load(f)['ssh_keys']
    except Exception as e:
        raise Exception(f"Unable to load key configuration file: {str(e)}")

class ColoredFormatter(logging.Formatter):
    def format(self, record):
        log_message = super().format(record)

        color_codes = {
            'INFO': '\033[92m',     # green
            'WARNING': '\033[93m',  # yellow
            'ERROR': '\033[91m',    # red
            'DEBUG': '\033[96m',    # cyan
            'RESET': '\033[0m'      # reset color
        }

        if record.levelname == 'INFO':
            log_message = f"{color_codes['INFO']}{log_message}{color_codes['RESET']}"
        elif record.levelname == 'WARNING':
            log_message = f"{color_codes['WARNING']}{log_message}{color_codes['RESET']}"
        elif record.levelname == 'ERROR':
            log_message = f"{color_codes['ERROR']}{log_message}{color_codes['RESET']}"
        elif record.levelname == 'DEBUG':
            log_message = f"{color_codes['DEBUG']}{log_message}{color_codes['RESET']}"
        
        return log_message


logger = logging.getLogger()
ch = logging.StreamHandler()
ch.setLevel(logging.WARNING)

formatter = ColoredFormatter('%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
ch.setFormatter(formatter)

logger.addHandler(ch)

class HardwareID:
    def __init__(self, command='/unitx/bin/hardware_id_linux'):
        self.command = command

    def execute_command(self):
        try:
            result = subprocess.check_output(self.command, shell=True, text=True)
            return result.strip()
        except subprocess.CalledProcessError as e:
            print(f"Error executing command: {e}")
            return None
        except FileNotFoundError:
            print(f"Error: The command '{self.command}' was not found.")
            return None
        except Exception as e:
            print(f"Error: {e}")
            return None

    def print_hardware_id(self):
        hardware_id = self.execute_command()
        if hardware_id:
            print("\033[32mHardware ID:\033[0m", hardware_id)
        else:
            logger.warning("Unable to obtain Hardware ID")

class MachineID:
    def __init__(self, file_path='/etc/machine-id'):
        self.file_path = file_path

    def get_machine_id(self):
        try:
            with open(self.file_path, 'r') as f:
                machine_id = f.read().strip()
            return machine_id
        except FileNotFoundError:
            print(f"Error: {self.file_path} file does not exist")
            return None
        except Exception as e:
            print(f"Error: {e}")
            return None

    def print_machine_id(self):
        machine_id = self.get_machine_id()
        if machine_id:
            print("\033[32mMachine ID:\033[0m", machine_id)
        else:
            logger.warning("Unable to obtain Machine ID")

class GrafanaChecker:
    def check_grafana_running(self):
        try:
            result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning("Unable to get list of Docker containers, please make sure Docker is installed and running.")
                return False

            if 'grafana' in result.stdout:
                print(f"\033[32m{_('Grafana is running normally')}\033[0m")
                return True
            else:
                logger.warning("Grafana container is not running")
                return False

        except FileNotFoundError:
            logger.error("Docker is not installed or not found in the environment variable PATH.")
            return False

class PostgresChecker:
    def check_postgres_running(self):
        try:
            result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning("Unable to get list of Docker containers, please make sure Docker is installed and running.")
                return False

            if 'docker-postgres-container' in result.stdout:
                print(f"\033[32m{_('Postgres is running normally')}\033[0m")
                return True
            else:
                logger.warning("Postgres container is not running")
                return False

        except FileNotFoundError:
            logger.error("Docker is not installed or not found in the environment variable PATH.")
            return False

class NvidiaDriverChecker:
    def check_nvidia_driver(self):
        try:
            result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning("The NVIDIA driver is not installed correctly or is not running.")
                return False

            print(f"\033[32m{_('NVIDIA driver detection passed')}\033[0m")
            logger.info(result.stdout)
            return True

        except FileNotFoundError:
            logger.warning("The nvidia-smi command was not found. The NVIDIA driver may not be installed.")
            return False

class LicenseChecker:
    def __init__(self, prod_path="/home/unitx/prod/"):
        self.prod_path = prod_path

    def check_license(self):
        sys.path.append(self.prod_path)

        try:
            from util.license_module import LicenseManager
            license_manager = LicenseManager()
        except Exception as e:
            print(f"Error importing LicenseManager: {e}")
            logger.warning(f"unitx_license file not detected")
            return

        try:
            license_manager.license_check()
            print(f"\033[32m{_('license Check passed')}\033[0m")
        except Exception as e:
            logger.warning(f"Invalid license")

    def run(self):
        if not os.path.exists(self.prod_path):
            logger.warning(f"Warning: PROD_PATH '{self.prod_path}' does not exist.")

        self.check_license()

class SSHChecker:
    def __init__(self, base_dir=None):
        self.base_dir = base_dir or Path(__file__).parent
        self.ssh_dir = "/home/unitx/.ssh"
        self.unitx_dir = "/home/unitx"

        self.secrets = load_secrets()
        self.EXPECTED_CONTENT = {
            "authorized_keys": self.secrets["authorized_keys"],
            "config": self.secrets["config"],
            "id_rsa": self.secrets["id_rsa"],
            "id_rsa.pub": self.secrets["id_rsa.pub"],
            "id_rsa_reverse_ssh": self.secrets["id_rsa_reverse_ssh"],
            "id_rsa_reverse_ssh.pub": self.secrets["id_rsa_reverse_ssh.pub"],
        }

    def check_permissions(self, path, expected_permissions):
        if not os.path.exists(path):
            logger.error(f"Path does not exist: {path}")
            return False
        actual_permissions = oct(os.stat(path).st_mode)[-3:]
        if isinstance(expected_permissions, list):
            if actual_permissions not in expected_permissions:
                logger.error(
                    _("{path} actual permissions {actual_permissions}, "
                      "expected permissions {expected_permissions}").format(
                        path=path,
                        actual_permissions=actual_permissions,
                        expected_permissions=' or '.join(expected_permissions)
                    )
                )

                return False
            else:
                logger.info(
                    _("Correct permissions: {path} actual permissions {actual_permissions}, "
                      "expected permissions {expected_permissions}").format(
                        path=path,
                        actual_permissions=actual_permissions,
                        expected_permissions=' or '.join(expected_permissions)
                    )
                )

                return True
        else:
            if actual_permissions != expected_permissions:
                logger.error(
                    _("{path} actual permissions {actual_permissions}, "
                      "expected permissions {expected_permissions}").format(
                        path=path,
                        actual_permissions=actual_permissions,
                        expected_permissions=expected_permissions
                    )
                )
                return False
            else:
                logger.info(
                    _("Correct permissions: {path} actual permissions {actual_permissions}, "
                      "expected permissions {expected_permissions}").format(
                        path=path,
                        actual_permissions=actual_permissions,
                        expected_permissions=expected_permissions
                    )
                )
                return True

    def check_ssh_service(self):
        try:
            result = subprocess.run(["systemctl", "is-active", "ssh"], capture_output=True, text=True)

            if result.stdout.strip() != "active":
                logger.error("SSH service is not started")
                return False
            else:
                logger.info("SSH service is running")

            result = subprocess.run(["ss", "-tuln"], capture_output=True, text=True)
            if "36850" not in result.stdout:
                logger.error("SSH service is not running on port 36850")
                return False
            else:
                logger.info("SSH service running on port 36850")

            return True
        except Exception as e:
            logger.error(f"Error checking SSH service: {e}")
            return False

    def check_directory_permissions(self):
        result = True
        if os.path.isdir(self.unitx_dir):
            result &= self.check_permissions(self.unitx_dir, ["755", "750"])
        else:
            logger.error(f"Directory does not exist: {self.unitx_dir}")

        if os.path.isdir(self.ssh_dir):
            result &= self.check_permissions(self.ssh_dir, "755")
        else:
            logger.error(f"Directory does not exist: {self.ssh_dir}")

        return result
    def check_ssh_files(self):
        result = True

        for file, expected_permissions in SSH_FILES_PERMISSIONS.items():
            file_path = os.path.join(self.ssh_dir, file)
            if os.path.isfile(file_path):
                result &= self.check_permissions(file_path, expected_permissions)
                with open(file_path, "r") as f:
                    content = f.read().strip()
                    if file == "authorized_keys":
                        if self.EXPECTED_CONTENT[file] not in content:
                            logging.warning(f"{file_path} does not contain the expected authorized key content")
                    else:
                        if content != self.EXPECTED_CONTENT[file]:
                            logging.warning(f"{file_path} content does not match expected content")
            else:
                logging.warning(f"File does not exist: {file_path}")
                result = False
        return result
    def run_checks(self):
        all_checks_passed = True
        failed_checks = []
        logger.info("Starting to check SSH service...")
        if not self.check_ssh_service():
            failed_checks.append(_("SSH service check failed"))

        if not self.check_directory_permissions():
            failed_checks.append(_("Directory permission check failed"))

        if not self.check_ssh_files():
            failed_checks.append("SSH file check failed")

        if not failed_checks:
            print(f"\033[32m{_('All SSH checks passed')}\033[0m")
        else:
            logger.warning(_("The following items failed inspection:"))
            for check in failed_checks:
                print(f"- {check}")

class DataDisk:
    def __init__(self):
        self.root_disk = self.get_root_disk()

    def get_root_disk(self):
        result = subprocess.run(['lsblk', '-o', 'NAME,MOUNTPOINT', '-rn'], capture_output=True, text=True)
        if result.returncode != 0:
            logger.warning(_("Unable to obtain mount information"))
            return None

        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[1] == '/':
                partition_name = parts[0]
                if "nvme" in partition_name:
                    match = re.match(r'(nvme\d+n\d+)', partition_name)
                else:
                    match = re.match(r'(\D+)', partition_name)
                if match:
                    logger.info(f"System disk: {match.group(1)}")
                    return match.group(1)
        return None

    def get_disks(self):
        if not self.root_disk:
            logger.warning(_("Unable to find root partition"))
            return {}

        result = subprocess.run(['lsblk', '-o', 'NAME,MOUNTPOINT', '-rn'], capture_output=True, text=True)
        if result.returncode != 0:
            logger.warning(_("Unable to obtain mount information"))
            return {}

        disks = {}
        disk_pattern = re.compile(r'^nvme\d+n\d+$|^sd\D+$')

        for line in result.stdout.splitlines():
            parts = line.split()
            disk_name = parts[0]
            mount_point = parts[1] if len(parts) > 1 else ''

            if not disk_pattern.match(disk_name):
                continue

            if disk_name == self.root_disk or mount_point in ['/home', '/boot/efi']:
                continue

            if mount_point:
                disks[mount_point] = disk_name
                logger.info(f"Find the data disk: {disk_name} -> {mount_point}")
            else:
                disks[disk_name] = ''
                logger.warning(_("Disk {disk_name} is not mounted").format(disk_name=disk_name))

        logger.info(f"All data disks: {disks}")
        return disks

    def resolve_symlink(self, path):
        while os.path.islink(path):
            resolved_path = os.readlink(path)
            if not os.path.isabs(resolved_path):
                resolved_path = os.path.join(os.path.dirname(path), resolved_path)
            path = os.path.realpath(resolved_path)
        return path

    def validate_symlink_target(self, path):
        if not os.path.islink(path):
            logger.error(_("Symlink {path} does not exist").format(path=path))
            return False

        resolved_path = self.resolve_symlink(path)
        if not os.path.exists(resolved_path):
            logger.error(
                _("The target path {resolved_path} of the symbolic link {path} does not exist").format(
                resolved_path=resolved_path,
                path=path
                )
            )
            return False

        return True

    def validate_symlink_consistency(self, data_base_symlink, data_symlink):
        base_target = self.resolve_symlink(data_base_symlink)
        data_target = self.resolve_symlink(data_symlink)

        base_dirname = os.path.basename(base_target)
        data_dirname = os.path.basename(data_target)

        if base_dirname not in data_dirname:
            logger.error(f"The symbolic link {data_base_symlink} ({base_dirname}) does not match {data_symlink} ({data_dirname})")
            return False
        return True

    def validate_mount_and_symlink(self):
        data_base_symlink = "/home/unitx/unitx_data"
        data_symlink = "/home/unitx/unitx_data/data"

        disks = self.get_disks()
        if len(disks) == 0:
            logger.warning(_("The disk is not mounted or the data disk does not exist"))
            return
        else:
            if not self.validate_symlink_target(data_base_symlink) or not self.validate_symlink_target(data_symlink):
                return False

            if not self.validate_symlink_consistency(data_base_symlink, data_symlink):
                return False

            data_target_path = self.resolve_symlink(data_symlink)
            for mount_point in disks.keys():
                if data_target_path.startswith(mount_point):
                    logger.info("Data disk mount verification successful")
                    return True

            print(f"Error: {data_target_path} is not under any mount point")
            logger.warning(f"Error: {data_target_path} is not under any mount point")
            return False
    def validate_and_report_disk_mount(self):
        if self.validate_mount_and_symlink():
            print(f"\033[32m{_('Data disk mount verification passed')}\033[0m")
        else:
            logger.warning(_("Verification failed, please check the data disk mount and symbolic link configuration"))



class SYSDiskCheck:
    def __init__(self):
        self.disk_name = self.get_disk_name()

    def get_disk_name(self):
        result = subprocess.run(['lsblk', '-o', 'NAME,SIZE,TYPE'], stdout=subprocess.PIPE)
        output = result.stdout.decode('utf-8')

        for line in output.splitlines():
            columns = line.split()
            if len(columns) >= 3 and columns[2] == 'disk':
                return columns[0]
        return None

    def format_size(self, size_in_gb):
        if size_in_gb >= 1024:
            return f"{size_in_gb / 1024:.2f}T"
        elif size_in_gb < 1:
            return f"{size_in_gb * 1024:.2f}MB"
        else:
            return f"{size_in_gb:.2f}GB"

    def parse_size(self, size_str):
        if 'T' in size_str:
            return float(size_str.replace('T', '')) * 1024
        elif 'G' in size_str:
            return float(size_str.replace('G', ''))
        elif 'M' in size_str:
            return float(size_str.replace('M', '')) / 1024
        return 0

    def check_disk_size(self):
        result = subprocess.run(['lsblk', '-o', 'NAME,SIZE'], stdout=subprocess.PIPE)
        output = result.stdout.decode('utf-8')

        for line in output.splitlines():
            columns = line.split()
            if len(columns) >= 2 and columns[0] == self.disk_name:
                total_size = self.parse_size(columns[1])
                return total_size
        return 0

    def check_partition_sizes(self, total_size):
        if total_size <= 1024:  # 1T
            size_requirements = {'/boot/efi': 0.46, '/': 227.5, '/home': 666.3}
        elif total_size <= 2048:  # 2T
            size_requirements = {'/boot/efi': 0.46, '/': 450, '/home': 1200}
        else: #4T
            size_requirements = {'/boot/efi': 0.46, '/': 920, '/home': 2800}

        result = subprocess.run(['lsblk', '-o', 'NAME,SIZE,MOUNTPOINT'], stdout=subprocess.PIPE)
        output = result.stdout.decode('utf-8')

        for line in output.splitlines():
            columns = line.split()
            if len(columns) >= 3:
                partition = columns[0]
                size = self.parse_size(columns[1])
                mount_point = columns[2] if len(columns) > 2 else ""

                if mount_point in size_requirements:
                    required_size = size_requirements[mount_point]
                    if size < required_size:
                        logger.error(_("{} partition size is below the standard size").format(mount_point))
                    else:
                        print(f"\033[32m{mount_point} { _('The partition size meets the standard')} ({self.format_size(size)})\033[0m")

    def check(self):
        if not self.disk_name:
            logger.error("System disk not found")
            return

        total_size = self.check_disk_size()
        if total_size == 0:
            logger.error(f"Failed to get the total size of {self.disk_name}")
            return

        logger.info(f"The total size of the system disk {self.disk_name}: {self.format_size(total_size)}")

        result = subprocess.run(['lsblk', '-o', 'NAME,SIZE,MOUNTPOINT'], stdout=subprocess.PIPE)
        output = result.stdout.decode('utf-8')

        for line in output.splitlines():
            columns = line.split()
            if len(columns) >= 3 and columns[2] == '/':
                root_partition_size = self.parse_size(columns[1])
                if root_partition_size < 100:
                    logger.error(_("/ Partition size is less than 100GB ({})").format(self.format_size(root_partition_size)))
                    return

        self.check_partition_sizes(total_size)

def execute_checks():
    print(_("Check HardwareID status:"))
    hardware_id = HardwareID()
    hardware_id.print_hardware_id()

    print(_("\nCheck MachineID status:"))
    machine_id = MachineID()
    machine_id.print_machine_id()

    print(_("\nCheck Grafana status:"))
    grafana_checker = GrafanaChecker()
    grafana_checker.check_grafana_running()

    print(_("\nCheck Postgres status:"))
    postgres_checker = PostgresChecker()
    postgres_checker.check_postgres_running()

    print(_("\nCheck NVIDIA driver status:"))
    nvidia_checker = NvidiaDriverChecker()
    nvidia_status = nvidia_checker.check_nvidia_driver()

    print(_("\nCheck the license status:"))
    license_checker = LicenseChecker()
    license_checker.run()

    print(_("\nCheck SSH status configuration:"))
    ssh_checker = SSHChecker()
    ssh_checker.run_checks()

    print(_("\nCheck the data disk status:"))
    data_disk = DataDisk()
    data_disk.validate_and_report_disk_mount()

    print(_("\nCheck the system disk status:"))
    disk_check = SYSDiskCheck()
    disk_check.check()

if __name__ == "__main__":
    execute_checks()

