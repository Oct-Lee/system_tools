import subprocess
import os
import logging
import time
import shutil
import stat
from localization import setup_locale, _

current_directory = os.path.dirname(os.path.realpath(__file__))

SERVICE_FILE = "/home/unitx/.config/systemd/user/file_monitoring.service"
SERVICE_NAME = "file_monitoring.service"
SCRIPT_PATH = os.path.join(current_directory, "deploy_integrity_monitor.sh")
SERVICE_NAME = "file_monitoring.service"

log_dir = os.path.join(current_directory, "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "integrity_monitor.log")
dir_mode = stat.S_IMODE(os.stat(log_dir).st_mode)
if dir_mode != 0o777:
    os.chmod(log_dir, 0o777)
if not os.path.exists(log_file):
    with open(log_file, 'w') as f:
        pass
file_mode = stat.S_IMODE(os.stat(log_file).st_mode)
if file_mode != 0o777:
    os.chmod(log_file, 0o777)
logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s - %(message)s')

def deploy_monitoring(send_to_output):
    if os.path.exists(SERVICE_FILE):
        send_to_output(_("The file monitoring service already exists and will not be created again."))
    else:
        try:
            with open(SERVICE_FILE, "w") as f:
                f.write("""
[Unit]
Description=Start Unitx User Script
After=graphical-session.target

[Service]
Type=simple
ExecStart={script_path}
Environment=DISPLAY=:0.0
WorkingDirectory=/home/unitx

[Install]
WantedBy=default.target
""".format(script_path=SCRIPT_PATH))

            send_to_output(_("The file monitoring service has been created."))
            logging.info(_("The file monitoring service has been created."))
            return 100
        except subprocess.CalledProcessError as e:
            send_to_output(_("Deployment monitoring failed: {e}").format(e=str(e)))
            return 0

def check_deployment_status(send_to_output):
    try:
        enable_result = subprocess.run(
            ["systemctl", "--user", "is-enabled", SERVICE_NAME],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        enable_output = enable_result.stdout.strip()


        if enable_output == "enabled":
            active_result = subprocess.run(
                ["systemctl", "--user", "is-active", SERVICE_NAME],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            active_output = active_result.stdout.strip()


            if active_output == "active":
                send_to_output(_("Monitor service status: Deployed, enabled, and running"))
                return 'active'
            elif active_output == "inactive":
                send_to_output(_("Monitor service status: Deployed and enabled, but not running"))
                return 'inactive'
            else:
                send_to_output(_("Monitoring service status: Unknown active status {active_output}").format(active_output=active_output))
                return 'unknown'

        elif enable_output == "disabled":
            send_to_output(_("Monitoring service status: Deployed but not enabled"))
            return 'deployed_disabled'
        else:
            send_to_output(_("Monitoring status: Service not deployed"))
            return 'not_deployed'

    except subprocess.CalledProcessError as e:
        send_to_output(_("Monitoring status: Unable to determine service status, error: {e}").format(e=str(e)))
        return 'unknown'

def monitor_changes(send_to_output):
    send_to_output(_("File monitoring started..."))
    
    try:
        while True:
            send_to_output(_("Checking for file changes..."))
            time.sleep(1)
    except KeyboardInterrupt:
        send_to_output(_("Monitoring has stopped."))

def start_monitoring(send_to_output):
    send_to_output(_("Starting file monitoring service..."))

    try:
        subprocess.check_call(["systemctl", "--user", "enable", SERVICE_NAME], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.check_call(["systemctl", "--user", "start", SERVICE_NAME], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        send_to_output(_("{} is up and monitoring").format(SERVICE_NAME))
        return 100
    except subprocess.CalledProcessError as e:
        send_to_output(_("Failed to start monitoring: {e}").format(e=str(e)))
        return 0

def stop_monitoring(send_to_output):
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", "file_monitoring.service"],
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            encoding="utf-8"
        )

        status_output = result.stdout.strip()

        if status_output == "active":
            send_to_output(_("Stopping file monitoring..."))

            subprocess.check_call(["systemctl", "--user", "stop", "file_monitoring.service"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.check_call(["systemctl", "--user", "disable", "file_monitoring.service"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            send_to_output(_("The file monitoring service has stopped."))
        elif status_output == "inactive":
            send_to_output(_("The monitoring service is not running."))
        else:
            send_to_output(_("Unable to determine monitoring service status: {status_output}").format(status_output=status_output))
    except subprocess.CalledProcessError as e:
        send_to_output(_("Failed to stop monitoring: {e_output}").format(e_output=e.output))
    except Exception as e:
        send_to_output(f"ERROR: {str(e)}")

def remove_monitoring(send_to_output):
    try:
        send_to_output(_("Starting to remove monitoring..."))

        try:
            result = subprocess.run(["systemctl", "--user", "is-active", SERVICE_NAME], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode == 0:
                subprocess.check_call(["systemctl", "--user", "stop", SERVICE_NAME], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                subprocess.check_call(["systemctl", "--user", "disable", SERVICE_NAME], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                send_to_output(_("The {SERVICE_NAME} service is stopped and disabled.").format(SERVICE_NAME=SERVICE_NAME))
            else:
                send_to_output(_("The {SERVICE_NAME} service is not running or does not exist.").format(SERVICE_NAME=SERVICE_NAME))
        except subprocess.CalledProcessError as e:
            send_to_output(_("Failure while stopping or disabling service: {e}").format(e=str(e)))

        service_deleted = False
        if os.path.exists(SERVICE_FILE):
            os.remove(SERVICE_FILE)
            service_deleted = True

        git_deleted = False
        git_dir = "/home/unitx/.git"
        if os.path.exists(git_dir):
            try:
                shutil.rmtree(git_dir)
                git_deleted = True
            except Exception as e:
                send_to_output(_("Deleting the .git directory failed: {e}").format(e=str(e)))

        gitignore_deleted = False
        gitignore_file = "/home/unitx/.gitignore"
        if os.path.exists(gitignore_file):
            try:
                os.remove(gitignore_file)
                gitignore_deleted = True
            except OSError as e:
                send_to_output(_("Deleting the .gitignore file failed: {e}").format(e=str(e)))

        if not service_deleted and not git_deleted and not gitignore_deleted:
            send_to_output(_("There are no monitoring items that need to be removed, and neither the service files nor the related directories were found."))
        else:
            send_to_output(_("File integrity monitoring removed"))

        return 100

    except subprocess.CalledProcessError as e:
        send_to_output(_("Failed to remove monitoring: {e}").format(e=str(e)))
        return 0
