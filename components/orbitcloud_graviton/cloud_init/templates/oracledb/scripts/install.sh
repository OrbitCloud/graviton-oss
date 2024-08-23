#!/bin/bash

# Exit and fail on errors
set -e

. ./setenv.sh

rm -rf ${UPDATED_RELEASE_DIR}

mkdir -p ${UPDATED_RELEASE_DIR}
cp -r ${ORACLE_RELEASE_DIR}/* ${UPDATED_RELEASE_DIR}
mv ${UPDATED_RELEASE_DIR}/OPatch ${UPDATED_RELEASE_DIR}/OPatch.old
cp -r ${SOFTWARE_DIR}/19.0.0/OPatch ${UPDATED_RELEASE_DIR}/OPatch

# No one-offs right now
export ONE_OFFS_DIR="${SOFTWARE_DIR}/19.0.0/oneoffs"
export RELEASE_UPDATE_DIR="${SOFTWARE_DIR}/19.0.0/release_update"
export RELEASE_UPDATE="{$RELEASE_UPDATE_DIR}/36582781"


chown -R oracle:oinstall ${ORACLE_BASE}

# Set up the environment bash profile
cp ./setenv.sh /etc/profile.d/oracle.sh
cp ./installhome.sh /home/oracle/
chown oracle:oinstall /home/oracle/installhome.sh
chmod 755 /home/oracle/installhome.sh
