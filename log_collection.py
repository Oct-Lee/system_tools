import subprocess
import argparse
import os
import re
import shutil
from datetime import datetime, timedelta
import tarfile
from localization import setup_locale, _

home_dir = os.path.expanduser('~')
timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')

log_files = {
    "unitx_cortex.log": "/home/unitx/unitx_data/logs/cortex.log",
    "unitx_optix.log": "/home/unitx/unitx_data/logs/optix.log",
    "unitx_prod.log": "/home/unitx/unitx_data/logs/prod.log",
    "factory_cortex.log": "/home/factory/factory_data/logs/cortex.log",
    "factory_optix.log": "/home/factory/factory_data/logs/optix.log",
    "factory_prod.log": "/home/factory/factory_data/logs/prod.log",
}


system_log_files = {
    "syslog": "/var/log/syslog",
    "kern.log": "/var/log/kern.log"
}

config_dirs = [
    "/home/unitx/unitx_data/config",
    "/home/unitx/unitx_data/db"
]

ATOP_LOG_DIR = "/var/log/atop"

def display_help(script_name):
    current_time = datetime.now()
    one_hour_earlier = current_time - timedelta(hours=1)

    example_start_time = one_hour_earlier.strftime("%Y-%m-%d %H:%M:%S")
    example_end_time = current_time.strftime("%Y-%m-%d %H:%M:%S")

    help_text = f"""
Log Filter Tool - Usage Guide

Usage:
    python log_collection.py -u [user] -t [start_time] [end_time]
    python log_collection.py -u [user] -n [recent_lines] [-f log_file ...]

Options:
    -t            Define the time range for filtering logs.
                  Format: [start_time] [end_time] (e.g., "YYYY-MM-DD HH:MM:SS").
    -n            Show the last n lines from the log files.
    -f            Specify the log file(s) to process. Multiple files can be listed.
                  Available log files: cortex.log, optix.log, prod.log, syslog, kern.log.
                  If omitted, all log files are included by default.

Execution Examples:
    python {script_name} -t "{example_start_time}" "{example_end_time}"  
    # Get logs between "{example_start_time}" and "{example_end_time}"
    
    python {script_name} -t "{example_start_time}" "{example_end_time}" -f syslog  
    # Get logs between "{example_start_time}" and "{example_end_time}" from syslog
    
    python {script_name} -t "{example_start_time}" "{example_end_time}" -f syslog prod.log  
    # Get logs between "{example_start_time}" and "{example_end_time}" from syslog and prod.log
    
    python {script_name} -n 100  
    # Get the latest 100 log lines from all logs
    
    python {script_name} -n 100 -f syslog  
    # Get the last 100 lines from syslog
    
    python {script_name} -n 100 -f syslog prod.log  
    # Get the last 100 lines from syslog and prod.log
    

    Notes:
    - Ensure date-time values follow the correct format.
    - Combining `-f` allows you to target specific logs while limiting the output.
    """
    return help_text

def run_command(command):
    result = subprocess.run(command, shell=True, text=True, capture_output=True)
    return result.stdout.strip()

def gather_system_info(output_dir):
    if not output_dir:
        print("Error: Output directory is not specified.")
        return

    system_info_file = os.path.join(output_dir, "system_info.txt")
    with open(system_info_file, "w") as file:
        file.write("Software Version Information:\n")
        version_files = [
            "/home/unitx/prod/production_src/version.txt",
            "/home/unitx/cortex/cortex_src/version.txt",
            "/home/unitx/optix/optix_src/version.txt"
        ]
        for version_file in version_files:
            try:
                with open(version_file, "r") as f:
                    version = f.read().strip()
                    file.write(f"Version from {version_file}: {version}\n")
            except FileNotFoundError:
                file.write(f"Version file not found: {version_file}\n")

        cpu_info = run_command("lscpu")
        model_name_match = re.search(r'Model name:\s*(.*)|型号名称：\s*(.*)', cpu_info)
        cpu_cores_match = re.search(r'CPU\(s?\):\s*(\d+)|CPU:\s*(\d+)', cpu_info)
        file.write("\nCPU Information:\n")
        if model_name_match:
            model_name = model_name_match.group(1) if model_name_match.group(1) else model_name_match.group(2)
            file.write(f"Model name: {model_name}\n")
        else:
            file.write("Unable to obtain CPU model name")

        if cpu_cores_match:
            cpu_cores = cpu_cores_match.group(1) if cpu_cores_match.group(1) else cpu_cores_match.group(2)
            file.write(f"CPU cores: {cpu_cores}\n")
        else:
            file.write("Unable to obtain the number of CPU cores")

        file.write("\nMemory Usage:\n")
        memory_usage = run_command("free -h")
        file.write(memory_usage + "\n")

        file.write("\nDisk space Usage:\n")
        disk_usage = run_command("df -h")
        file.write(disk_usage + "\n")

        file.write("\nDisk Inode Usage:\n")
        inode_usage = run_command("df -i")
        file.write(inode_usage + "\n")

        file.write("\nDisk Information (lsblk):\n")
        disk_info = run_command("lsblk -o NAME,SIZE,TYPE,MOUNTPOINT")
        file.write(disk_info + "\n")

        file.write("\nOperating System Version:\n")
        os_version = run_command("cat /etc/os-release")
        file.write(os_version + "\n")

        file.write("\nKernel Version:\n")
        kernel_version = run_command("uname -r")
        file.write(kernel_version + "\n")

        file.write("\nGPU Information:\n")
        gpu_info = run_command("lspci | grep -i nvidia")
        file.write(gpu_info + "\n")

        if run_command("command -v nvidia-smi") != "":
            nvidia_smi_info = run_command("nvidia-smi")
            file.write(nvidia_smi_info + "\n")
        else:
            file.write("No NVIDIA GPU detected.\n")

        file.write("\nGrafana Information:\n")
        grafana_running = run_command("docker ps --filter 'name=unitx-grafana' --format '{{.Names}}'")

        if grafana_running:
            file.write(f"Grafana is deployed: {grafana_running}\n")
        else:
            file.write("Grafana not deployed.\n")

    print(f"{_('System information has been saved to {system_info_file}').format(system_info_file=system_info_file)}")

def get_today_atop_log():
    today = datetime.now().strftime("%Y%m%d")
    atop_log_file = os.path.join(ATOP_LOG_DIR, f"atop_{today}")
    if os.path.exists(atop_log_file):
        return atop_log_file
    else:
        print(f"{_('Today atop log {atop_log_file} not found.').format(atop_log_file=atop_log_file)}")

        return None

def filter_software_logs_by_time(start_time=None, end_time=None, selected_files=None):
    timestamp_pattern = r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+"

    if not selected_files:
        selected_files = log_files.keys()
    else:
        selected_files = [file for file in selected_files if file in log_files]

    os.makedirs(output_dir, exist_ok=True)

    for log_key in selected_files:
        input_log_file = log_files[log_key]
        if not os.path.exists(input_log_file):
            print(f"{_('The file {input_log_file} does not exist, skipping.').format(input_log_file=input_log_file)}")
            continue

        output_log_file = os.path.join(output_dir, os.path.basename(log_key))  

        try:
            with open(input_log_file, "r") as infile, open(output_log_file, "w") as outfile:
                current_time = None
                for line in infile:
                    match = re.match(timestamp_pattern, line)
                    if match:
                        log_time_str = match.group().split(".")[0]
                        log_time = datetime.strptime(log_time_str, "%Y-%m-%d %H:%M:%S")

                        current_time = log_time

                    if current_time and (start_time is None or current_time >= start_time) and (end_time is None or current_time <= end_time):
                        outfile.write(line)


            print(f"{_('Log file from {start_time} to {end_time} saved to {output_log_file}.').format(start_time=start_time, end_time=end_time, output_log_file=output_log_file)}")
        except FileNotFoundError:
            print(f"{_('Log file {input_log_file} not found, skipping.').format(input_log_file=input_log_file)}")
        except Exception as e:
            print(f"{_('An error occurred while processing log file {input_log_file}: {e}').format(input_log_file=input_log_file, e=e)}")

def filter_system_logs_by_time(start_time=None, end_time=None, selected_files=None):
    syslog_pattern = r"^\w{3} {1,2}\d{1,2} \d{2}:\d{2}:\d{2}"
    if not selected_files:
        selected_files = system_log_files.values()
    else:
        selected_files = [system_log_files[file] for file in selected_files if file in system_log_files]

    os.makedirs(output_dir, exist_ok=True)

    for input_log_file in selected_files:
        if not os.path.exists(input_log_file):
            print(f"{_('The file {input_log_file} does not exist, skipping.').format(input_log_file=input_log_file)}")
            continue

        output_log_file = os.path.join(output_dir, os.path.basename(input_log_file))

        try:
            with open(input_log_file, "r") as infile, open(output_log_file, "w") as outfile:
                current_time = None
                for line in infile:
                    match = re.match(syslog_pattern, line)
                    if match:
                        log_time_str = match.group()
                        syslog_time = datetime.strptime(f"{datetime.now().year} {log_time_str}", "%Y %b %d %H:%M:%S")

                        current_time = syslog_time

                    if current_time and (start_time is None or current_time >= start_time) and (end_time is None or current_time <= end_time):
                        outfile.write(line)


            print(f"{_('Log file from {start_time} to {end_time} saved to {output_log_file}.').format(start_time=start_time, end_time=end_time, output_log_file=output_log_file)}")
        except FileNotFoundError:
            print(f"{_('Log file {input_log_file} not found, skipping.').format(input_log_file=input_log_file)}")
        except Exception as e:
            print(f"{_('An error occurred while processing log file {input_log_file}: {e}').format(input_log_file=input_log_file, e=e)}")

def display_software_recent_lines(line_count=10, selected_files=None):
    if not selected_files:
        selected_files = log_files.keys()
    else:
        selected_files = [file for file in selected_files if file in log_files]

    os.makedirs(output_dir, exist_ok=True)

    for log_key in selected_files:
        input_log_file = log_files[log_key]
        if not os.path.exists(input_log_file):
            print(f"{_('The file {input_log_file} does not exist, skipping.').format(input_log_file=input_log_file)}")
            continue

        output_log_file = os.path.join(output_dir, os.path.basename(log_key))

        try:
            with open(input_log_file, "r") as infile, open(output_log_file, "w") as outfile:
                lines = infile.readlines()[-line_count:]
                outfile.writelines(lines)

            print(f"{_('Last {line_count} lines saved to {output_log_file}.').format(line_count=line_count, output_log_file=output_log_file)}")
        except Exception as e:
            print(f"{_('Error processing file {input_log_file}: {e}').format(input_log_file=input_log_file, e=e)}")

def display_system_recent_lines(line_count=10, selected_files=None):
    if not selected_files:
        selected_files = system_log_files.keys()
    else:
        selected_files = [file for file in selected_files if file in system_log_files]

    os.makedirs(output_dir, exist_ok=True)

    for log_key in selected_files:
        input_log_file = system_log_files[log_key]
        if not os.path.exists(input_log_file):
            print(f"{_('The file {input_log_file} does not exist, skipping.').format(input_log_file=input_log_file)}")
            continue

        output_log_file = os.path.join(output_dir, os.path.basename(log_key))

        try:
            with open(input_log_file, "r") as infile, open(output_log_file, "w") as outfile:
                lines = infile.readlines()[-line_count:]
                outfile.writelines(lines)

            print(f"{_('Last {line_count} lines saved to {output_log_file}.').format(line_count=line_count, output_log_file=output_log_file)}")
        except Exception as e:
            print(f"{_('Error processing file {input_log_file}: {e}').format(input_log_file=input_log_file, e=e)}")


def create_compressed_archive(output_dir, config_dirs):
    archive_file = os.path.join(home_dir, f"all_logs_{timestamp}.tar.gz")

    if not os.path.exists(output_dir):
        print(f"{_('Error: The directory {output_dir} does not exist.').format(output_dir=output_dir)}")
        return

    for config_dir in config_dirs:
        if not os.path.exists(config_dir):
            print(f"{_('Warning: The directory {config_dir} does not exist, skipping.').format(config_dir=config_dir)}")

    with tarfile.open(archive_file, "w:gz") as tar:
        for input_log_file in os.listdir(output_dir):
            full_path = os.path.join(output_dir, input_log_file)
            if os.path.isfile(full_path):
                tar.add(full_path, arcname=input_log_file)

        for config_dir in config_dirs:
            if os.path.exists(config_dir):
                for root, dirs, files in os.walk(config_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, config_dir)
                        tar.add(file_path, arcname=os.path.join(os.path.basename(config_dir), arcname))
        today_atop_log = get_today_atop_log()
        if today_atop_log:
            tar.add(today_atop_log, arcname=os.path.basename(today_atop_log))
    shutil.move(archive_file, output_dir)
    print(f"{_('Compressed archive created: {output_dir}/all_logs_{timestamp}.tar.gz').format(output_dir=output_dir, timestamp=timestamp)}")
    try:
        subprocess.Popen(['gio', 'open', output_dir], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        print("Note: Failed to open the file manager, but archive was created successfully.")

if __name__ == "__main__":
    script_name = os.path.basename(__file__)
    parser = argparse.ArgumentParser(description="Log Filter Tool", add_help=False)
    parser.add_argument("-t", nargs="+", help="Specify time range: start_time [end_time] (format: YYYY-MM-DD HH:MM:SS)")
    parser.add_argument("-n", type=int, help="Display the last n lines from the log files")
    parser.add_argument(
        "-f",
        nargs="+",
        help="Specify the log files to process. Choices: cortex.log, optix.log, prod.log, syslog, kern.log"
    )

    parser.add_argument("-h", "--help", action="store_true", help="Show help message and examples")

    args = parser.parse_args()

    if args.help:
        print(display_help(script_name))
        exit(0)

    output_dir = os.path.join(home_dir, f"all_logs_{timestamp}")
    
    should_create_archive = False
    
    if args.t:
        try:
            start_time = datetime.strptime(args.t[0], "%Y-%m-%d %H:%M:%S")
            end_time = datetime.strptime(args.t[1], "%Y-%m-%d %H:%M:%S") if len(args.t) > 1 else None
            filter_software_logs_by_time(start_time, end_time, args.f)
            filter_system_logs_by_time(start_time, end_time, args.f)
            should_create_archive = True
        except ValueError:
            print(_("Invalid time format. Please use 'YYYY-MM-DD HH:MM:SS'."))
    elif args.n:
        display_software_recent_lines(args.n, args.f)
        display_system_recent_lines(args.n, args.f)
        should_create_archive = True
    else:
        parser.print_help()

    if should_create_archive:
        if output_dir:
            gather_system_info(output_dir)
            create_compressed_archive(output_dir, config_dirs)

