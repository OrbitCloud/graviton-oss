#!/bin/bash
set -e
set -o pipefail


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
