#!/bin/bash

current_time() {
  date "+%Y-%m-%d %H:%M:%S"
}

MONITOR_DIRS=(
  "/home/unitx/cortex"
  "/home/unitx/prod"
  "/home/unitx/optix"
  "/home/unitx/unitx_data"
)

VERSION_FILES=(
  "/home/unitx/cortex/cortex_src/version.txt"
  "/home/unitx/prod/production_src/version.txt"
  "/home/unitx/optix/optix_src/version.txt"
)

current_dir=$(dirname "$(readlink -f "$0")")
logs_dir="$current_dir/logs"
mkdir -p "$logs_dir"
LOG_FILE="$logs_dir/file_change.log"

GITIGNORE_FILE="/home/unitx/.gitignore"

declare -A processed_paths

create_gitignore() {
  if [ ! -f "$GITIGNORE_FILE" ]; then
    echo "$(current_time) - .gitignore file does not exist, creating..." >> $LOG_FILE
    cat <<EOL > "$GITIGNORE_FILE"
# Ignore everything
/*

# Only monitor a specific directory and its subdirectories
!cortex/
!prod/
!optix/
!unitx_data/
!unitx_data_*/

# Ignore the production and data directories and their contents under unitx_data_*/
unitx_data_*/production/
unitx_data_*/data/
unitx_data_*/temp/
unitx_data_*/cache/
unitx_data_*/images_train/
unitx_data_*/experiments/
unitx_data_*/fake_images/

# Ignore all .log files, including .log.* files
*.log*

# Keep the .gitignore file itself
!.gitignore
EOL
    echo "$(current_time) - .gitignore file created" >> $LOG_FILE
  else
    echo "$(current_time) - .gitignore file already exists, skip creation" >> $LOG_FILE
  fi
}

initialize_git() {
  if [ -z "$(git -C /home/unitx rev-parse --is-inside-work-tree 2>/dev/null)" ]; then
    echo "$(current_time) - The current directory is not a Git repository, initializing..." >> $LOG_FILE
    ORIGINAL_PS1="$PS1"
    export PS1="> "

    cd /home/unitx || exit 1
    git config --global init.defaultBranch main
    git init >> "$LOG_FILE" 2>&1
    git config user.email "unitx@example.com" >> "$LOG_FILE" 2>&1
    git config user.name "unitx" >> "$LOG_FILE" 2>&1

    export PS1="$ORIGINAL_PS1"
  else
    echo "$(current_time) - All directories are already Git repositories, no initialization required" >> $LOG_FILE
  fi
}

declare -A previous_versions
read_versions() {
  for version_file in "${VERSION_FILES[@]}"; do
    if [ -f "$version_file" ]; then
      current_version=$(cat "$version_file")

      if [ -z "${previous_versions[$version_file]}" ]; then
        previous_versions["$version_file"]="$current_version"
      fi
    else
      echo "$(current_time) - version file does not exist: $version_file" >> $LOG_FILE
    fi
  done
}

check_and_commit_changes() {
  if git diff --quiet; then
    return 0
  else
    changed_files=$(git diff --name-only)
    detailed_changes=$(git diff)


    git commit -a -m "Automatically commit: monitored directories have changed"
    echo "$(current_time) - Commit changes completed" >> $LOG_FILE

    commit_time=$(git log -1 --format=%cd)

    echo -e "[$commit_time]:\n$detailed_changes" > /tmp/file_diff.log

    echo "Commit time: $commit_time" >> "$LOG_FILE"
    echo "Changed files:" >> "$LOG_FILE"
    echo "$changed_files" >> "$LOG_FILE"
    echo "Changes:" >> "$LOG_FILE"
    echo "$detailed_changes" >> "$LOG_FILE"
    echo "------------------------------------------------------------" >> "$LOG_FILE"

    notify-send -t 10000 "File changes" "View change details: /tmp/file_diff.log"
  fi
}

check_version_changes() {
  local all_versions=()
  local consistent_version=""
  local version_changed=false

  for version_file in "${VERSION_FILES[@]}"; do
    if [ -f "$version_file" ]; then
      current_version=$(cat "$version_file")
      all_versions+=("$current_version")

      if [ -n "${previous_versions[$version_file]}" ]; then
        if [ "${previous_versions[$version_file]}" != "$current_version" ]; then
          version_changed=true
        fi
      fi

      previous_versions["$version_file"]="$current_version"
    else
      echo "$(current_time) - version file does not exist: $version_file" >> $LOG_FILE
    fi
  done

  consistent_version=$(echo "${all_versions[@]}" | tr ' ' '\n' | sort -u | wc -l)

  if [ "$version_changed" = true ] && [ "$consistent_version" -eq 1 ]; then
    echo "$(current_time) - version number changes and is consistent: ${all_versions[0]}" >> "$LOG_FILE"

    git add . >> $LOG_FILE 2>&1
    git commit -m "Automatically commit: version number updated to ${all_versions[0]}" >> $LOG_FILE 2>&1

    commit_time=$(git log -1 --format=%cd)

    echo "Commit time: $commit_time" >> "$LOG_FILE"
    echo "------------------------------------------------------------" >> "$LOG_FILE"
  fi
}

add_untracked_dir() {
  local dir=$1
  if ! git ls-files --error-unmatch "$dir" &>/dev/null; then
    echo "$(current_time) - added untracked directory: $dir" >> $LOG_FILE
    git add "$dir" >> $LOG_FILE
  fi
}

process_unitx_data() {
  real_dir=$1

  if ! git ls-files --error-unmatch "$real_dir" &>/dev/null; then
    echo "$(current_time) - unitx_data is a soft link, the real path is: $real_dir" >> $LOG_FILE
    git add "$real_dir" && echo "Soft link directory added: $real_dir" >> $LOG_FILE
    echo "$(current_time) - All directories initialized" >> $LOG_FILE
  fi
}

monitor_changes() {
  while true; do
    read_versions

    for dir in "${MONITOR_DIRS[@]}"; do
      if [ "$dir" == "/home/unitx/unitx_data" ]; then
        real_dir=$(readlink -f "$dir")
        if [[ -z "${processed_paths[$real_dir]}" ]]; then
          process_unitx_data "$real_dir"
          processed_paths["$real_dir"]=1
        fi
      else
        add_untracked_dir "$dir"
      fi
    done

    check_and_commit_changes

    check_version_changes

    sleep 30
  done
}

main() {
  echo "$(current_time) - start script execution" >> $LOG_FILE

  create_gitignore

  initialize_git

  monitor_changes
}

main
