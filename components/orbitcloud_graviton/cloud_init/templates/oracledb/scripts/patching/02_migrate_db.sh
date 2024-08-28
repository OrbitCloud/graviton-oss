#!/bin/bash

# TODO - Move to external file or parameters
# Database to patch and patch version
export PATCH_VERSION="19.24.0"
export ORACLE_SID="testdb2"

#
# Ensure required environment variables are set
#
if [ -z "${ORACLE_BASE}" ]; then
    echo "ORACLE_BASE not set"
    exit 1
fi

if [ -z "${ORA_INVENTORY}" ]; then
    echo "ORA_INVENTORY not set"
    exit 1
fi

if [ -z "${ORACLE_HOSTNAME}" ]; then
    echo "ORACLE_HOSTNAME not set"
    exit 1
fi

# Configure PATH
export PATH=/usr/sbin:/usr/local/bin:$PATH
export PATH=${ORACLE_HOME}/bin:$PATH

# Prerequisites for OL9
export LD_LIBRARY_PATH=${ORACLE_HOME}/lib:/lib:/usr/lib
export CLASSPATH=${ORACLE_HOME}/jlib:${ORACLE_HOME}/rdbms/jlib
export CV_ASSUME_DISTID=OL8

export ORAENV_ASK=NO
. $(which oraenv) 

# Shutdown database and change ORACLE_HOME
sqlplus / as sysdba << EOF
    shutdown immediate;
    exit;
EOF

# Change ORACLE_HOME in the following files 
# /etc/oratab
# $ORACLE_BASE/oraInventory/ContentsXML/inventory.xml
# $ORACLE_HOME/network/admin/listener.ora
# $ORACLE_HOME/network/admin/tnsnames.ora
# Since using Oracle read only homes
# $ORACLE_HOME/install/orabasetab





# NewTarget home
export ORACLE_HOME=/opt/oracle/product/19c/${PATCH_VERSION}