#!/bin/bash

script_dir=$(dirname "$(realpath "$0")")
log_dir="$script_dir/logs"
mkdir -p "$log_dir"
log_file="$log_dir/task_log.txt"

while true; do
    current_time=$(date +%s)
    
    target_time=$(date -d "10:00" +%s)

    if [ "$current_time" -gt "$target_time" ]; then
        target_time=$(date -d "tomorrow 10:00" +%s)
    fi

    sleep_time=$((target_time - current_time))
    echo "Sleeping for $sleep_time seconds until $(date -d @$target_time)" >> "$log_file"
    
    sleep "$sleep_time"

    echo "Task started: $(date)" >> "$log_file"
    bash "$script_dir/disk_check.sh"
    echo "Task completed: $(date)" >> "$log_file"
done

