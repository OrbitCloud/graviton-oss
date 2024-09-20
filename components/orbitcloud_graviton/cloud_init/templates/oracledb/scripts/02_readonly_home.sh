#!/bin/bash

export ORACLE_HOME=/opt/oracle/product/19c/dbhome_test

cd ${ORACLE_HOME}/bin || exit
./roohctl -enable
