#!/bin/bash

export ORACLE_HOME=/opt/oracle/product/19c/dbhome_test
export ORACLE_SID=cdb1
export PATH=${ORACLE_HOME}/bin:$PATH
TEMPDB_DIR=/mnt/resource/oradata/${ORACLE_SID}

unset TNS_ADMIN

sqlplus -S -L / as sysdba << __EOF__
whenever oserror exit failure
whenever sqlerror exit failure
variable fcsize varchar2(32)
begin
	select to_char((to_number(value)/1024)*4)||'K' into :fcsize from v\$parameter where name = 'sga_max_size';
end;
/
begin
	execute immediate 'alter system set db_flash_cache_file = ''${TEMPDB_DIR}/flash_cache.dat'' scope=spfile';
end;
/
begin
	execute immediate 'alter system set db_flash_cache_size = '||:fcsize||' scope=spfile';
end;
/
shutdown immediate
startup
exit success
__EOF__
