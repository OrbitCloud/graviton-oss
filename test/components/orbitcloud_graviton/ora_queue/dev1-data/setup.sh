#!/bin/bash
set -e
set -o pipefail

# Database
export dns="20.107.205.202:1521/orbit1"

# User
export orbituser=ORBIT_QUEUE
export orbitts=USERS
export orbitpwd=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9-_!#$%^&*.,;:' | fold -w 24 | head -1)

# Tables
export tables="FTTEST.FYRIRTAEKI,FTTEST.ISATSKRA"

testwd=$(pwd)
cd /home/$USER/src/Graviton/components/orbitcloud_graviton/ora_queue/source

# DBA actions to create the user and grant privileges
sql SYS/"${syspasswd}"@${dns} as SYSDBA @create_queue_owner.sql ${orbituser} ${orbitpwd} ${orbitts} <<EOF
exit;
EOF

sql SYS/"${syspasswd}"@${dns} as SYSDBA @install.sql ${orbituser} <<EOF
exit;
EOF

cd ${testwd}
sql SYS/"${syspasswd}"@${dns} as SYSDBA @table_grants.sql ${orbituser} ${tables}

# User actions to create the credentials and subscribe to granted tables
sql ${orbituser}/"${orbitpwd}"@${dns} @create_credentials.sql $saskey $client $secret $tenant
sql ${orbituser}/"${orbitpwd}"@${dns} @subscribe.sql ${tables}

# DBA update random rows in the tables
sql SYS/${syspasswd}@${dns} as SYSDBA @update_rows.sql
