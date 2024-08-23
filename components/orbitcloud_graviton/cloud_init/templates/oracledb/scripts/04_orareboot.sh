#!/bin/bash
# Should reside in /root/orareboot.sh

export ORACLE_SID=cdb1

TEMPDB_DIR=/mnt/resource/oradata/${ORACLE_SID}
ORADATA_MNT=/opt/oracle/oradata/${ORACLE_SID}

# Check if the dir exists
if [ ! -d "${TEMPDB_DIR}" ]; then
    echo "Creating ${TEMPDB_DIR}"
    mkdir -p ${TEMPDB_DIR}
    chown -R oracle:oinstall ${TEMPDB_DIR}
    ls -ld ${TEMPDB_DIR}

else
    echo "$TEMPDB_DIR already exists"
fi

# CHeck if oradata is mounted
if grep -qs "${ORADATA_MNT}" /proc/mounts; then
    echo "${ORADATA_MNT} already mounted"
else
    mount ${ORADATA_MNT}
    df -h ${ORADATA_MNT}
    echo "${ORADATA_MNT} mounted"
fi
