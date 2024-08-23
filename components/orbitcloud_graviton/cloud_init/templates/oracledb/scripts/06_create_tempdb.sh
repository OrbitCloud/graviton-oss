#!/bin/bash

export ORACLE_HOME=/opt/oracle/product/19c/dbhome_test
export ORACLE_SID=cdb1
export PATH=${ORACLE_HOME}/bin:$PATH
TEMPDB_DIR=/mnt/resource/oradata/${ORACLE_SID}
unset TNS_ADMIN

# Ensure TEMPDB_DIR exists
if [ ! -d "${TEMPDB_DIR}" ]; then
	echo "TEMPDB_DIR does not exist: ${TEMPDB_DIR}"
	exit 1
fi

sqlplus -S -L / as sysdba << __EOF__
whenever oserror exit failure
whenever sqlerror exit failure
alter session set db_create_file_dest='${TEMPDB_DIR}';
create temporary tablespace temptmptemp tempfile size 10M;
alter database default temporary tablespace temptmptemp;
shutdown immediate
startup
drop tablespace temp including contents and datafiles;
alter session set db_create_file_dest='${TEMPDB_DIR}';
create temporary tablespace temp
	tempfile size 512M autoextend on next 512M maxsize unlimited
	extent management local uniform size 1M;
alter database default temporary tablespace temp;
exit success
__EOF__

sqlplus -S -L / as sysdba << __EOF__
whenever oserror exit failure
whenever sqlerror exit failure
drop tablespace temptmptemp including contents and datafiles;
exit success
__EOF__
