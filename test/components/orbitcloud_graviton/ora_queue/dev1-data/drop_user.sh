#!/bin/bash
sql SYS/${syspasswd}@${dns} as SYSDBA <<EOF
DROP USER ${orbituser} CASCADE;
exit;
EOF
