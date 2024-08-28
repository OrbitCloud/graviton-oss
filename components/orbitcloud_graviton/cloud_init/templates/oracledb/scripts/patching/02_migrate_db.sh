#!/bin/bash

# TODO - Move to external file or parameters
# Database to patch and patch version
export PATCH_VERSION="19.24.0"


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

# Make sure that the PATCH_SID is set
if [ -z "${PATCH_SID}" ]; then
    echo "PATCH_SID not set"
    exit 1
fi
# Old Oracle home
export OLD_ORACLE_HOME=$(grep "${PATCH_SID}:" /etc/oratab | cut -d: -f2)

# NewTarget home
export NEW_ORACLE_HOME=/opt/oracle/product/19c/${PATCH_VERSION}

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
# TODO - $ORACLE_BASE/oraInventory/ContentsXML/inventory.xml

# Since using Oracle read only homes
# TODO - $ORACLE_HOME/install/orabasetab

# Make sure the tnsnames.ora and listener.ora files are updated
# TODO - $ORACLE_HOME/network/admin/tnsnames.ora

# TODO - $ORACLE_HOME/network/admin/listener.ora
lsnrctl restart

