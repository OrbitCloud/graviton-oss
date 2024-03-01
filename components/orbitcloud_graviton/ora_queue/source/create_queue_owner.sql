
/*
    NAME
      create_queue_owner.sql

    DESCRIPTION
      This scripts creates the user that will subscribe to table DML changes

    NOTES
      Must be run by a user with DBA privileges.
*/


whenever sqlerror exit failure rollback
whenever oserror exit failure rollback

set echo off
set feedback off
set heading off
set verify off

set serveroutput on

PROMPT This Script will create a user to manage table change notifications and AQ to push changes to Azure

define queue_owner = &1
define queue_password     = &2
define queue_tablespace   = &3


PROMPT ..... Creating Queue user &&queue_owner

create user &queue_owner identified by "&queue_password" default tablespace &queue_tablespace QUOTA unlimited on &queue_tablespace;

grant create session, create sequence, create procedure, create type, create table, create view, create synonym, create trigger to &queue_owner;

PROMPT ..... Granting access to Change Notification and Advanced Queues

grant change notification TO &queue_owner;

grant execute on DBMS_CQ_NOTIFICATION TO &queue_owner;
grant execute on DBMS_AQ TO &queue_owner;
grant execute on DBMS_AQADM TO &queue_owner;
grant execute on DBMS_CRYPTO TO &queue_owner;

grant alter session to &queue_owner;
