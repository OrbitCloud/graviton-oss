#!/bin/bash

# Configure PATH
export PATH=/usr/sbin:/usr/local/bin:$PATH
export PATH=${ORACLE_HOME}/bin:$PATH

# Prerequisites for OL9
export LD_LIBRARY_PATH=${ORACLE_HOME}/lib:/lib:/usr/lib
export CLASSPATH=${ORACLE_HOME}/jlib:${ORACLE_HOME}/rdbms/jlib
export CV_ASSUME_DISTID=OL8

# ensure DATA_DIR is set
if [ -z "${DATA_DIR}" ]; then
    echo "DATA_DIR not set"
    exit 1
fi
# make sure the data directory exists
mkdir -p ${DATA_DIR}

# ensure that BACKUP_DIR is set
if [ -z "${BACKUP_DIR}" ]; then
    echo "BACKUP_DIR not set"
    exit 1
fi

# make sure that backupdir fra exists
mkdir -p ${BACKUP_DIR}/fra

# Make sure sys and system password environment variablesa are set
if [ -z "${SYS_PASSWORD}" ]; then
    echo "SYS_PASSWORD not set"
    exit 1
fi
if [ -z "${SYSTEM_PASSWORD}" ]; then
    echo "SYSTEM_PASSWORD not set"
    exit 1
fi

 # Create the CDB
dbca -silent -createDatabase \
 -templateName ${ORACLE_HOME}/assistants/dbca/templates/General_Purpose.dbc \
 -gdbname $ORACLE_UNQNAME \
 -sid $ORACLE_SID \
 -databaseConfigType SINGLE \
 -responseFile NO_VALUE \
 -characterSet AL32UTF8 \
 -sysPassword "${SYS_PASSWORD}" \
 -systemPassword "${SYSTEM_PASSWORD}" \
 -createAsContainerDatabase true \
 -numberOfPDBs 0 \
 -databaseType MULTIPURPOSE \
 -memoryMgmtType auto_sga \
 -totalMemory 20000 \
 -storageType FS \
 -datafileDestination "${DATA_DIR}" \
 -createListener LISTENER:1521 \
 -useOMF true \
 -recoveryAreaSize 200000 \
 -recoveryAreaDestination "${BACKUP_DIR}/fra" \
 -enableArchive true \
 -redoLogFileSize 150 \
 -emConfiguration NONE \
  -initParams db_create_online_log_dest_1="${DATA_DIR}-redo1/", db_create_online_log_dest_2="${DATA_DIR}-redo2/", archive_lag_target=600 \
 -ignorePreReqs
