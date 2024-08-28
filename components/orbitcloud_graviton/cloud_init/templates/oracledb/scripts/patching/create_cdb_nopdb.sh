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

# Create the postcdb.sql script
cat > /tmp/postcdb.sql <<EOF
alter system set db_create_online_log_dest_1="${DATA_DIR}-redo1/" scope=both;
alter system set db_create_online_log_dest_2="${DATA_DIR}-redo2/" scope=both;

alter database add logfile group 4 size 150m blocksize 4096;
alter database add logfile group 5 size 150m blocksize 4096;
alter database add logfile group 6 size 150m blocksize 4096;

set serveroutput on 
declare
  l_curr pls_integer;
begin
  select group# into l_curr from v\$log where status = 'CURRENT';
  if l_curr in (1, 2, 3) then
    for x in l_curr .. 3 loop
      execute immediate 'alter system ARCHIVE LOG CURRENT';
      dbms_session.sleep(1);
    end loop;
  end if;
  for g in 1 .. 3 loop
    begin
      execute immediate 'drop logfile group :group'
        using g;
      execute immediate 'alter database add logfile group :group size 150m'
        using g;
      sys.dbms_output.put_line('Dropped logfile group ' || g || ' and recreated with correct parameters');
    exception
      when others then
        sys.dbms_output.put_line('Error: Unable to drop logfile group ' || g || '. Error: ' || sqlerrm);
    end;
  end loop;
end;
/
EOF



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
 -initParams archive_lag_target=600 \
 -customScripts /tmp/postcdb.sql \
 -ignorePreReqs
