@@set_install_params.sql
prompt queue_owner: &&queue_owner queue_password: &&queue_password queue_tablespace: &&queue_tablespace
@@create_queue_owner.sql &&queue_owner &&queue_password &&queue_tablespace
@@install.sql &&queue_owner

exit
