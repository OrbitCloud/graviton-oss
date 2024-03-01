
cd /tmp
curl -o /tmp/apex-latest.zip https://download.oracle.com/otn_software/apex/apex-latest.zip
unzip -q /tmp/apex-latest.zip -d /tmp
rm -f /tmp/apex-latest.zip
cd /tmp/apex
export ORACLE_PDB_SID=${ORA_PDB_SID}
sqlplus / as sysdba @apexins.sql USERS USERS TEMP /i/
