PASSWD=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9-_!@#$%^&*.,;:' | fold -w 24 | head -1)
echo $PASSWD

docker run -it --rm \
-p 1521:1521 \
-p 1522:1522 \
-p 8443:8443 \
-p 27017:27017 \
-e WORKLOAD_TYPE='ATP' \
-e WALLET_PASSWORD=$PASSWD \
-e ADMIN_PASSWORD=$PASSWD \
--cap-add SYS_ADMIN \
--device /dev/fuse \
--name adb-free-tests \
-v /home/$USER/src/Graviton/components/orbitcloud_graviton/ora_queue/source:/opt/oracle/oqf_scripts \
container-registry.oracle.com/database/adb-free:latest
