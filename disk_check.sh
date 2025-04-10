#!/bin/bash

CURRENT_LANG=$(echo $LANG | cut -d_ -f1)
SCRIPT_DIR=$(dirname "$0")
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/disk_space_check.log"

if [ ! -d "$LOG_DIR" ]; then
    mkdir -p "$LOG_DIR"
fi

SPACE_USAGE=$(df -hPTl -x tmpfs -x efivarfs | sort | tail -n +2)
INODE_USAGE=$(df -iPTl -x tmpfs -x efivarfs | grep -v "vfat" | sort | tail -n +2)

echo "$SPACE_USAGE" | while read line; do
    PARTITION=$(echo $line | awk '{print $1}')
    SPACE_USAGE_PERCENT=$(echo $line | awk '{print $6}' | sed -e 's/%//g')
    AVAILABLE_SPACE=$(echo $line | awk '{print $5}')

    if [ $SPACE_USAGE_PERCENT -ge 95 ]; then
	if [ "$CURRENT_LANG" == "zh" ]; then
	    echo "$(date) - 临界: 分区 $PARTITION 的磁盘使用率为 $SPACE_USAGE_PERCENT%，剩余空间为 $AVAILABLE_SPACE。" >> $LOG_FILE
	    #zenity --info --title="磁盘使用率临界" --text="分区 $PARTITION 的磁盘使用率为 $SPACE_USAGE_PERCENT%，剩余空间为 $AVAILABLE_SPACE，已超过95%的临界值。" --icon-name="dialog-warning"
	    notify-send "磁盘使用率临界" "分区 $PARTITION 的磁盘使用率为 $SPACE_USAGE_PERCENT%，剩余空间为 $AVAILABLE_SPACE，已超过95%的临界值。" --urgency=critical
	else
	    echo "$(date) - CRITICAL: Disk usage on $PARTITION is at $SPACE_USAGE_PERCENT%, remaining space is $AVAILABLE_SPACE." >> $LOG_FILE
	    #zenity --info --title="Disk Usage Critical" --text="The disk usage of partition $PARTITION is $SPACE_USAGE_PERCENT%, with $AVAILABLE_SPACE of space remaining, which has exceeded the 95% threshold." --icon-name="dialog-warning"
	    notify-send "Disk Usage Critical" "Disk usage on $PARTITION is at $SPACE_USAGE_PERCENT%, remaining space is $AVAILABLE_SPACE, which is above the 95% threshold." --urgency=critical
	fi
    elif [[ $SPACE_USAGE_PERCENT -ge 85 && $SPACE_USAGE_PERCENT -lt 95 ]]; then
	if [ "$CURRENT_LANG" == "zh" ]; then
	    echo "$(date) - 警告: 分区 $PARTITION 的磁盘使用率为 $SPACE_USAGE_PERCENT%，剩余空间为 $AVAILABLE_SPACE。" >> $LOG_FILE
	    notify-send "磁盘使用率警告" "分区 $PARTITION 的磁盘使用率为 $SPACE_USAGE_PERCENT%，剩余空间为 $AVAILABLE_SPACE，介于85%到95%之间。" --urgency=normal
	else
  	    echo "$(date) - WARNING: Disk usage on $PARTITION is at $SPACE_USAGE_PERCENT%, remaining space is $AVAILABLE_SPACE." >> $LOG_FILE
            notify-send "Disk Usage Warning" "Disk usage on $PARTITION is at $SPACE_USAGE_PERCENT%, remaining space is $AVAILABLE_SPACE, which is between 85% and 95%." --urgency=normal
	fi
    fi
done

echo "$INODE_USAGE" | while read line; do
    PARTITION=$(echo $line | awk '{print $1}')
    INODE_USAGE_PERCENT=$(echo $line | awk '{print $6}' | sed -e 's/%//g')
    AVAILABLE_INODES=$(echo $line | awk '{print $5}')

    if [ $INODE_USAGE_PERCENT -ge 95 ]; then
	if [ "$CURRENT_LANG" == "zh" ]; then
	    echo "$(date) - 临界: 分区 $PARTITION 的inode使用率为 $INODE_USAGE_PERCENT%，剩余inode为 $AVAILABLE_INODES。" >> $LOG_FILE
	    notify-send "inode使用率临界" "分区 $PARTITION 的inode使用率为 $INODE_USAGE_PERCENT%，剩余inode为 $AVAILABLE_INODES，超过了95%的阈值。" --urgency=critical
	else
	    echo "$(date) - CRITICAL: Inode usage on $PARTITION is at $INODE_USAGE_PERCENT%, remaining inodes are $AVAILABLE_INODES." >> $LOG_FILE
            notify-send "Inode Usage Critical" "Inode usage on $PARTITION is at $INODE_USAGE_PERCENT%, remaining inodes are $AVAILABLE_INODES, which is above the 95% threshold." --urgency=critical
	fi
    elif [[ $INODE_USAGE_PERCENT -ge 85 && $INODE_USAGE_PERCENT -lt 95 ]]; then
	if [ "$CURRENT_LANG" == "zh" ]; then
	    echo "$(date) - 警告: 分区 $PARTITION 的inode使用率为 $INODE_USAGE_PERCENT%，剩余inode为 $AVAILABLE_INODES。" >> $LOG_FILE
	    notify-send "inode使用率警告" "分区 $PARTITION 的inode使用率为 $INODE_USAGE_PERCENT%，剩余inode为 $AVAILABLE_INODES，介于85%到95%之间。" --urgency=normal
	else
	    echo "$(date) - WARNING: Inode usage on $PARTITION is at $INODE_USAGE_PERCENT%, remaining inodes are $AVAILABLE_INODES." >> $LOG_FILE
            notify-send "Inode Usage Warning" "Inode usage on $PARTITION is at $INODE_USAGE_PERCENT%, remaining inodes are $AVAILABLE_INODES, which is between 85% and 95%." --urgency=normal
	fi
    fi
done

