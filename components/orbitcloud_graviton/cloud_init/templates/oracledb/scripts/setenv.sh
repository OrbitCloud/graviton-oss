# Oracle Settings
if [ -z "${1}" ]; then
  DB="se"
else
  DB="${1}"
fi
echo "DB set to ${DB}prod"


# Oracle Settings
export TMP=/tmp
export TMPDIR=$TMP

export ORACLE_BASE=/opt/oracle
export ORACLE_HOSTNAME=oradb-se
export ORAENV_ASK=NO
export ORA_INVENTORY=/opt/oracle/oraInventory

export ORACLE_UNQNAME=cdb${DB}prod
export ORACLE_HOME=$ORACLE_BASE/product/19c/19.24.0
export ORACLE_BASE_HOME=$ORACLE_BASE/homes/$(cat $ORACLE_HOME/install/orabasetab | grep $ORACLE_HOME | cut -d: -f3)
export ORACLE_SID=cdb${DB}prod
export PDB_NAME=${DB}prod
export DATA_DIR=/oradata/${DB}prod

export BACKUP_DIR=/mnt/stmunuorabackupsswe/${DB}backups


export PATH=/usr/sbin:/usr/local/bin:$HOME/scripts:$PATH
export PATH=$ORACLE_HOME/bin:$ORACLE_HOME/OPatch:$ORACLE_HOME/sqlcl/bin:$PATH

export LD_LIBRARY_PATH=$ORACLE_HOME/lib:/lib:/usr/lib
export CLASSPATH=$ORACLE_HOME/jlib:$ORACLE_HOME/rdbms/jlib

ORAENV=$(which oraenv &> /dev/null)
if [ -f "${ORAENV}" ]; then
      . ${ORAENV}
fi
