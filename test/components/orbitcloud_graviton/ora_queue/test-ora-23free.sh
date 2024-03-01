
# This script is used to test that the `ora_queue` component fails to compile
# when installed in a database without APEX installed.

# -p 1521:1521

docker run --rm --name ora-tests \
-e ORACLE_RANDOM_PASSWORD="Yes" \
-e ORA_PDB_SID=FREEPDB1 \
-p 1521:1521 \
-v /home/$USER/src/Graviton/components/orbitcloud_graviton/ora_queue/source:/opt/oracle/scripts \
-v /home/$USER/src/Graviton/test/components/orbitcloud_graviton/ora_queue/tests/initdb.d:/container-entrypoint-initdb.d \
gvenzl/oracle-free:23-full-faststart
