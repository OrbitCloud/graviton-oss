#!/bin/bash

# Exit and fail on errors
set -e

export ORACLE_BASE=/opt/oracle
export ORA_INVENTORY=/opt/oracle/oraInventory
export SOFTWARE_DIR=/opt/oracle/software
export ORACLE_RELEASE_DIR="${SOFTWARE_DIR}/19.0.0/dbhome"
export UPDATED_RELEASE_DIR="${SOFTWARE_DIR}/19.24.0-on/dbhome"
export DATA_DIR=/opt/oracle/oradata/seprod
export TMPDIR=/tmp

export ORACLE_HOSTNAME=oradb-se
export ORACLE_UNQNAME=seprod
export ORACLE_SID=seprod

export PDB_NAME=pdb1
export ORACLE_HOME="${SOFTWARE_DIR}/19.24.0/dbhome_${ORACLE_SID}"

export PATH=/usr/sbin:/usr/local/bin:$PATH
export PATH=$ORACLE_RELEASE_DIR/bin:$PATH
export LD_LIBRARY_PATH=$ORACLE_RELEASE_DIR/lib:/lib:/usr/lib
export CLASSPATH=$ORACLE_RELEASE_DIR/jlib:$ORACLE_HOME/rdbms/jlib
