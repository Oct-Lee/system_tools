#!/bin/bash

LANGUAGE=$(locale | grep LANG= | cut -d= -f2 | cut -d. -f1)
current_dir=$(dirname "$(readlink -f "$0")")
APP_NAME="Ubuntu Repair Tool"
ICON_PATH="$current_dir/bin/ubuntu_repair_tool.ico"
PYTHON_PATH="/home/unitx/miniconda3/envs/unified_production/bin/python"
MAIN_FILE="$current_dir/main.py"
AUTOSTART_DIR="$HOME/.config/autostart"
AUTOSTART_FILE2="$AUTOSTART_DIR/delayed_run_disk_check.desktop"
CURRENT_USER=$(whoami)

DESKTOP_FILE="$HOME/.local/share/applications/UbuntuRepairTool.desktop"
DESKTOP_FILE_BIN="$current_dir/bin/UbuntuRepairTool.desktop"

if [[ "$LANGUAGE" == "zh_CN" ]]; then
    MESSAGE0="桌面图标已创建: $DESKTOP_FILE"
    MESSAGE1="开机启动脚本已创建: $AUTOSTART_FILE1"
    MESSAGE2="开机启动脚本已创建: $AUTOSTART_FILE2"
    MSG_ADDED="应用程序已添加到收藏夹"
    MSG_ALREADY_EXISTS="应用程序已经在收藏夹中"
    MSG_LINK_DONE="软链接已创建:"
    MSG_PROMPT_FACTORY_PASS="请输入 factory 用户密码以完成软链接操作："
    MSG_PROMPT_UNITX_PASS="请输入 unitx 用户密码以完成软链接操作："
else
    MESSAGE="Desktop icon created: $DESKTOP_FILE"
    MESSAGE2="The startup script has been created: $AUTOSTART_FILE"
    MSG_ADDED="Application has been added to favorites"
    MSG_ALREADY_EXISTS="Application is already in favorites"
    MSG_LINK_DONE="Symlink created:"
    MSG_PROMPT_FACTORY_PASS="Please enter the factory user's password to create the symlink:"
    MSG_PROMPT_UNITX_PASS="Please enter the unitx user's password to create the symlink:"
fi

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Name=$APP_NAME
Exec=$PYTHON_PATH $MAIN_FILE
Icon=$ICON_PATH
Terminal=false
Type=Application
StartupWMClass=ubuntu_repair_tool
EOF

if [ -f "$DESKTOP_FILE" ]; then
    chmod 755 "$DESKTOP_FILE"
    cp "$DESKTOP_FILE" "$DESKTOP_FILE_BIN"
    echo $MESSAGE
else
    echo "Error: Failed to create desktop file at $DESKTOP_FILE"
    exit 1
fi


cat <<EOF > "$AUTOSTART_FILE2"
[Desktop Entry]
Name=Delayed Run Script
Exec=nohup bash "{script_dir}/delayed_run_disk_check.sh" > /dev/null 2>&1 & disown
Type=Application
X-GNOME-Autostart-enabled=true
EOF

if [ -f "$AUTOSTART_FILE2" ]; then
    chmod 755 "$AUTOSTART_FILE2"
    echo $MESSAGE2
else
    echo "Error: Failed to create autostart file at $AUTOSTART_FILE2"
    exit 1
fi

if ! pgrep -f "$script_dir/delayed_run_disk_check.sh" > /dev/null; then
    nohup bash "{script_dir}/delayed_run_disk_check.sh" > /dev/null 2>&1 & disown
    echo "delayed_run_disk_check.sh executed."
else
    echo "delayed_run_disk_check.sh is already running. Skipping execution."
fi

current_launcher=$(gsettings get org.gnome.shell favorite-apps)

current_launcher=$(echo $current_launcher | sed 's/^\[//;s/\]$//')

new_app="UbuntuRepairTool.desktop"

if ! echo "$current_launcher" | grep -q "$new_app"; then
    current_launcher="$current_launcher, '$new_app'"
    gsettings set org.gnome.shell favorite-apps "[$current_launcher]"
    echo "$MSG_ADDED"
else
    echo "$MSG_ALREADY_EXISTS"
fi

if [ "$CURRENT_USER" == "unitx" ] && id factory &>/dev/null; then
    echo "$MSG_PROMPT_FACTORY_PASS"
    su factory -c "ln -sf '$DESKTOP_FILE_BIN' '/home/factory/.local/share/applications/UbuntuRepairTool.desktop'"
    echo "$MSG_LINK_DONE /home/factory/.local/share/applications/UbuntuRepairTool.desktop"

elif [ "$CURRENT_USER" == "factory" ] && id unitx &>/dev/null; then
    echo "$MSG_PROMPT_UNITX_PASS"
    su unitx -c "ln -sf '$DESKTOP_FILE_BIN' '/home/unitx/.local/share/applications/UbuntuRepairTool.desktop'"
    echo "$MSG_LINK_DONE /home/unitx/.local/share/applications/UbuntuRepairTool.desktop"
fi
