
# This script is used to test the Queue Framework with Oracle 21

docker run --rm --name ora-tests \
-e ORACLE_RANDOM_PASSWORD="Yes" \
-e ORA_PDB_SID=XEPDB1 \
-v /home/$USER/src/Graviton/components/orbitcloud_graviton/ora_queue/source:/opt/oracle/scripts \
-v /home/$USER/src/Graviton/test/components/orbitcloud_graviton/ora_queue/tests/initdb.d:/container-entrypoint-initdb.d \
gvenzl/oracle-xe:21-full-faststart
