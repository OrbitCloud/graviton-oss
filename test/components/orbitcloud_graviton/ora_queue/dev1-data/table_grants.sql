define queue_owner = &1
define table_list = &2
set echo off
set verify off

DECLARE
     l_Arr apex_t_varchar2;
BEGIN
    l_arr := apex_string.split('&&table_list', ',');
    FOR i IN 1..l_arr.count LOOP
        DBMS_OUTPUT.PUT_LINE('Granting SELECT on ' || l_arr(i));
        EXECUTE IMMEDIATE 'GRANT SELECT ON ' || l_arr(i) || ' TO ' || '&&queue_owner';
    END LOOP;
END;
/

exit;
