#!/bin/bash

DESKTOP_FILE="$HOME/.local/share/applications/UbuntuRepairTool.desktop"

# 删除桌面文件
if [ -f "$DESKTOP_FILE" ]; then
    rm "$DESKTOP_FILE"
    echo "已删除桌面图标"
else
    echo "桌面图标不存在"
fi

