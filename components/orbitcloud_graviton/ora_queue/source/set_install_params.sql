set echo off
set verify off

column 1 new_value "1" noprint;
column 2 new_value "2" noprint;
column 3 new_value "3" noprint;
select null as "1", null as "2" , null as "3" from dual where 1=0;

column queue_owner      new_value queue_owner      noprint
column queue_password   new_value queue_password   noprint
column queue_tablespace new_value queue_tablespace noprint

select coalesce('&&1', 'ORBIT_QUEUE') queue_owner,
       coalesce('&&2',
                replace(sys.dbms_random.string(opt => 'A', len => 14) || floor(sys.dbms_random.value(0, 1) * 100) || sys.dbms_random.string(opt => 'p', len => 6),' ',null)) queue_password,
       coalesce('&&3', 'USERS') queue_tablespace
  from dual;
