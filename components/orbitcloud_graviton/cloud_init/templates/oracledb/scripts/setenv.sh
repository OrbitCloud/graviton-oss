# Oracle Settings
export TMP=/tmp
export TMPDIR=$TMP

export ORACLE_BASE=/opt/oracle
export ORACLE_HOSTNAME=oradb-se
export ORAENV_ASK=NO
export ORA_INVENTORY=/opt/oracle/oraInventory

function seprod() (
  export ORACLE_UNQNAME=cdbseprod
  export ORACLE_HOME=$ORACLE_BASE/product/19c/dbhome_se
  export ORACLE_SID=cdbseprod
  export PDB_NAME=seprod
  export DATA_DIR=${ORACLE_BASE}/oradata/seprod
)

function dkprod() (
  export ORACLE_UNQNAME=cdbdkprod
  export ORACLE_HOME=$ORACLE_BASE/product/19c/dbhome_dk
  export ORACLE_SID=cdbdkprod
  export PDB_NAME=prod
  export DATA_DIR=${ORACLE_BASE}/oradata/seprod
)

export PATH=/usr/sbin:/usr/local/bin:$PATH
export PATH=$ORACLE_HOME/bin:$PATH

export LD_LIBRARY_PATH=$ORACLE_HOME/lib:/lib:/usr/lib
export CLASSPATH=$ORACLE_HOME/jlib:$ORACLE_HOME/rdbms/jlib


seprod

ORAENV=$(which oraenv &> /dev/null)
if [ -f "${ORAENV}" ]; then
    . ${ORAENV}
fi
