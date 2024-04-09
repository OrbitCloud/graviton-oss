set echo off
set verify off


define queue_owner = &1

column line_separator new_value line_separator noprint
select '--------------------------------------------------------------' as line_separator from dual;

prompt &&line_separator
prompt Installing Orbit Queue framework into &&queue_owner schema
prompt &&line_separator

whenever sqlerror exit failure rollback
whenever oserror exit failure rollback

prompt Switching current schema to &&queue_owner
prompt &&line_separator
alter session set current_schema = &&queue_owner;

@@check_sys_grants.sql "'CHANGE NOTIFICATION','CREATE SESSION','CREATE SEQUENCE','CREATE PROCEDURE','CREATE TYPE','CREATE TABLE','CREATE VIEW','CREATE TRIGGER'"
@@check_execute_grants.sql "'DBMS_CHANGE_NOTIFICATION', 'DBMS_AQ', 'DBMS_AQADM', 'DBMS_CRYPTO'"
@@check_select_grants.sql "'DBA_SUBSCR_REGISTRATIONS'"


-- Objects
prompt core/create_objects.sql
@@core/create_objects.sql
@@core/create_logger.sql
prompt core/create_advanced_queue.sql &&queue_owner
@@core/create_advanced_queue.sql

-- Packages
set define off
prompt .....Package Specifications
@@core/orb_log.pks
@@core/az_event_hubs.pks
@@core/az_change_notifications.pks

prompt .....Package Bodies
@@core/az_event_hubs.pkb
@@core/orb_log.pkb
@@core/az_change_notifications.pkb

prompt .....APEX Environments
@@core/apex_environments.sql


-- Check for compilation errors
declare
  l_compile_errors boolean := false;
begin
  <<compile_errors>>
  for i in (select e.type, e.name, e.line, e.position, e.text
              from all_errors e
              where owner = SYS_CONTEXT('userenv', 'current_schema')
                and name not like 'BIN$%' --not recycled
                and attribute = 'ERROR' -- errors only. ignore warnings
              order by e.type, e.name, e.line, e.position) loop
    l_compile_errors := true;
    sys.dbms_output.put_line(i.type || ': ' || i.name || ' --> ' || i.text || ' Line ' || i.line || ' column ' || i.position);
  end loop compile_errors;

  if l_compile_errors then
    raise_application_error(-20000, 'Not all sources were successfully installed.');
  else
    sys.dbms_output.put_line('##########################################');
    sys.dbms_output.put_line('... Installation completed successfully ...');
  end if;
end;
/
