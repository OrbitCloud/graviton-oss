cd /opt/oracle/scripts
export ORACLE_PDB_SID=${ORA_PDB_SID}
sqlplus / as sysdba @install_headless.sql
