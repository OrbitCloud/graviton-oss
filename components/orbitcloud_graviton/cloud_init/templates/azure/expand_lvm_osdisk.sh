#!/bin/bash

set -e

# Identify the root logical volume
ROOT_LV=$(findmnt -n -o SOURCE /)
VG_NAME=$(lvdisplay "$ROOT_LV" | grep "VG Name" | awk '{print $3}')
PV=$(pvs --noheadings -o pv_name,vg_name | grep "$VG_NAME" | awk '{print $1}')
DISK=$(lsblk -no pkname "$PV" | head -n 1)
PART_NUM=$(lsblk -no NAME "$PV" | grep -o '[0-9]*$')

growpart "/dev/${DISK}" "$PART_NUM"
partprobe "/dev/${DISK}"
pvresize /dev/"$DISK$PART_NUM"
lvextend -r -l +100%FREE "$ROOT_LV"
