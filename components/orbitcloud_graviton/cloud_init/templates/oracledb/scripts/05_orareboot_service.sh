#!/bin/bash

ORAREBOOT_SERVICE=/etc/systemd/system/orareboot.service
echo "[Unit]"									 > ${ORAREBOOT_SERVICE}
echo "Description=Run script at startup after network becomes reachable"	>> ${ORAREBOOT_SERVICE}
echo ""										>> ${ORAREBOOT_SERVICE}
echo "[Service]"								>> ${ORAREBOOT_SERVICE}
echo "Type=simple"								>> ${ORAREBOOT_SERVICE}
echo "RemainAfterExit=yes"							>> ${ORAREBOOT_SERVICE}
echo "ExecStart=/root/orareboot.sh"						>> ${ORAREBOOT_SERVICE}
echo "TimeoutStartSec=0"							>> ${ORAREBOOT_SERVICE}
echo ""										>> ${ORAREBOOT_SERVICE}
echo "[Install]"								>> ${ORAREBOOT_SERVICE}
echo "WantedBy=default.target"							>> ${ORAREBOOT_SERVICE}

chmod 755 /root/orareboot.sh

systemctl enable orareboot.service
systemctl start orareboot.service
