#!/bin/bash

export ORACLE_HOME=/opt/oracle/product/19c/dbhome_test
export PATH=${ORACLE_HOME}/bin:$PATH

export ORACLE_SID=cdb1
export PDB_NAME=pdb1
export DATA_DIR=/opt/oracle/oradata/test
export FRA_DIR=/opt/oracle/oradata/test/FRA
export FRA_SIZE_MB=40960
export LISTENER_PORT=1521

export REDO_LOG_SIZE_MB=4096


# We want to store the archive logs on the azure file share
export ARCHIVE_LOG_MNT=/mnt/storadbtestswe/orabackup
export ARCHIVE_LOG_DEST=${ARCHIVE_LOG_MNT}/archive

# Ensure ARCHIVE_LOG_MNT is mounted
if grep -qs "${ARCHIVE_LOG_MNT}" /proc/mounts; then
    echo "${ARCHIVE_LOG_MNT} already mounted"
else
    echo "Trying to mount ${ARCHIVE_LOG_MNT}"
    mount ${ARCHIVE_LOG_MNT} || exit 1
fi

# Check if ARCHIVE_LOG_DEST exists
if [ ! -d "${ARCHIVE_LOG_DEST}" ]; then
     echo "Creating ${ARCHIVE_LOG_DEST}"
     mkdir -p ${ARCHIVE_LOG_DEST}
     chown -R oracle:oinstall ${ARCHIVE_LOG_DEST}
     ls -ld ${ARCHIVE_LOG_DEST}
else
     echo "${ARCHIVE_LOG_DEST} already exists"
     # Check if it is empty
     if [ "$(ls -A ${ARCHIVE_LOG_DEST} 2>/dev/null)" ]; then
          echo "${ARCHIVE_LOG_DEST} is not empty - cancelling"
          exit 1
     fi
fi

# Ensure Oracle Home is empty
if [ "$(ls -A ${DATA_DIR} 2>/dev/null)" ]; then
    echo "Data Dir is not empty - cancelling"
    exit 1
fi

if [ "$(ls -A ${FRA_DIR} 2>/dev/null)" ]; then
    echo "FRA Dir is not empty - cancelling"
    exit 1
fi

mkdir -p ${FRA_DIR}
mkdir -p ${DATA_DIR}

lsnrctl start

dbca -silent -createDatabase                                                   \
     -templateName General_Purpose.dbc                                         \
     -gdbname ${ORACLE_SID} -sid  ${ORACLE_SID} -responseFile NO_VALUE         \
     -characterSet AL32UTF8                                                    \
     -sysPassword SysPassword1                                                 \
     -systemPassword SysPassword1                                              \
     -createListener LISTENER:${LISTENER_PORT}                                 \
     -createAsContainerDatabase true                                           \
     -numberOfPDBs 1                                                           \
     -pdbName ${PDB_NAME}                                                      \
     -pdbAdminPassword PdbPassword1                                            \
     -databaseType MULTIPURPOSE                                                \
     -memoryMgmtType auto_sga                                                  \
     -memoryPercentage 70                                                      \
     -storageType FS                                                           \
     -datafileDestination "${DATA_DIR}"                                        \
     -recoveryAreaDestination "${FRA_DIR}"                                     \
     -recoveryAreaSize ${FRA_SIZE_MB}                                          \
     -redoLogFileSize ${REDO_LOG_SIZE_MB}                                      \
     -emConfiguration NONE                                                     \
     -ignorePreReqs
