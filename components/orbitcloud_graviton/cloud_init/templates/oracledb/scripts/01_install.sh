#!/bin/bash

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

# Target home
export ORACLE_HOME=/opt/oracle/product/19c/dbhome_test
export SOFTWARE_DIR=/opt/oracle/software
export BASE_RELEASE_ZIP="${SOFTWARE_DIR}/LINUX.X64_193000_db_home.zip"
export OPATCH_ZIP="${SOFTWARE_DIR}/p6880880_190000_Linux-x86-64.zip"
export PATCH_ZIP="${SOFTWARE_DIR}/p36582781_190000_Linux-x86-64.zip"

# Configure PATH
export PATH=/usr/sbin:/usr/local/bin:$PATH
export PATH=${ORACLE_HOME}/bin:$PATH

# Prerequisites for OL9
export LD_LIBRARY_PATH=${ORACLE_HOME}/lib:/lib:/usr/lib
export CLASSPATH=${ORACLE_HOME}/jlib:${ORACLE_HOME}/rdbms/jlib
export CV_ASSUME_DISTID=OL8


#
# Ensure required software is available
#
if [ ! -f "${BASE_RELEASE_ZIP}" ]; then
    echo "Base release zip not found: ${BASE_RELEASE_ZIP}"
    exit 1
fi

if [ ! -f "${OPATCH_ZIP}" ]; then
    echo "OPatch zip not found: ${OPATCH_ZIP}"
    exit 1
fi

if [ ! -f "${PATCH_ZIP}" ]; then
    echo "Patch zip not found: ${PATCH_ZIP}"
    exit 1
fi

#
# Create Oracle Home and unzip base release software
#

# Ensure Oracle Home is empty
if [ "$(ls -A ${ORACLE_HOME} 2>/dev/null)" ]; then
    echo "Oracle Home is not empty - cancelling"
    exit 1
fi

mkdir -p ${ORACLE_HOME}
cd ${ORACLE_HOME} || exit


echo "Unzipping base release software..."
unzip -oq ${BASE_RELEASE_ZIP}

#
# Update OPatch
#
echo "Moving OPatch to OPatch.orig and unzipping updated OPatch..."
mv OPatch OPatch.orig
unzip -oq ${OPATCH_ZIP}

#
# 19.24.0 Release Update
#
echo "Unzipping release Update..."
unzip -d ${SOFTWARE_DIR} -oq ${PATCH_ZIP}
PATCH_NO=$(echo ${PATCH_ZIP} | grep -oP '(?<=p)\d+(?=_)')
export PATCH_TOP="${SOFTWARE_DIR}/${PATCH_NO}"
RU_VERSION=$(grep -oP '(?<=<title>)(.*?)(?=</title>)' "${PATCH_TOP}/README.html")

#
# Run installer
#
echo "Running Oracle Database installer..."
echo "  RU patch: ${PATCH_TOP}"
echo "  RU version: ${RU_VERSION}"
echo "  ORACLE_BASE: ${ORACLE_BASE}"
echo "  ORACLE_HOME: ${ORACLE_HOME}"
echo "  ORA_INVENTORY: ${ORA_INVENTORY}"
echo "  ORACLE_HOSTNAME: ${ORACLE_HOSTNAME}"

# Time to install

./runInstaller -ignorePrereq -waitforcompletion -silent                        \
    -applyRU "${PATCH_TOP}"                                                    \
    -responseFile ${ORACLE_HOME}/install/response/db_install.rsp               \
    oracle.install.option=INSTALL_DB_SWONLY                                    \
    ORACLE_HOSTNAME="${ORACLE_HOSTNAME}"                                       \
    UNIX_GROUP_NAME=oinstall                                                   \
    INVENTORY_LOCATION="${ORA_INVENTORY}"                                      \
    SELECTED_LANGUAGES=en,en_GB                                                \
    ORACLE_HOME="${ORACLE_HOME}"                                               \
    ORACLE_BASE="${ORACLE_BASE}"                                               \
    oracle.install.db.InstallEdition=EE                                        \
    oracle.install.db.OSDBA_GROUP=dba                                          \
    oracle.install.db.OSBACKUPDBA_GROUP=dba                                    \
    oracle.install.db.OSDGDBA_GROUP=dba                                        \
    oracle.install.db.OSKMDBA_GROUP=dba                                        \
    oracle.install.db.OSRACDBA_GROUP=dba                                       \
    SECURITY_UPDATES_VIA_MYORACLESUPPORT=false                                 \
    DECLINE_SECURITY_UPDATES=true
