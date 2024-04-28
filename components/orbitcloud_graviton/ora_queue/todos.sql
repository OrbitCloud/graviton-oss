-- # BUG : SQL Macro ENV_TABLE_LIST is breaking display of things within Apex Application
-- # BUG : Create Default Environment to fix broken displays
-- # [ ] : PLSQL API - CREATE/UPDATE configuration using scripts
-- # [ ] : Table datatype DATE - Use TIMESTAMP AT LOCAL TIMEZONE (or at least make the application timezone aware)
-- # [ ] : Column CREATED - Set Default if null to SYSTIMESTAMP AT LOCAL TIMEZONE (or at least make the application timezone aware)
-- # [ ] : Column CREATED_BY - Set Default if null to coalesce(sys_context('APEX$SESSION','APP_USER'),user)
-- # [ ] : Column UPDATED - Set Default to SYSTIMESTAMP AT LOCAL TIMEZONE, make sure user never has to think about it.
-- # [ ] : Column UPDATED_BY - Set Default if null to coalesce(sys_context('APEX$SESSION','APP_USER'),user)
-- # [ ] : Tables - All table should have auditing colums (CREATED, CREATED_BY, UPDATED, UPDATED_BY)
-- # TODO : (Future) PLSQL API - EXPORT/IMPORT of configuration settings for a given environment

-- Find all date columns 
/*
select * from user_tab_columns u
where EXISTS
(
    select 1 from user_tab_columns c
    where
    c.DATA_TYPE NOT IN ('BLOB','VARCHAR2','NUMBER','T_LOGGER','T_TABLE_CHANGES','ANYDATA','RAW','ROWID','CHAR')
    and c.TABLE_NAME = u.table_name AND c.COLUMN_NAME = u.COLUMN_NAME
);
*/

-- Find tables with missing auditing columns:
/*
select * from user_tables u
where not EXISTS
(
    select distinct c.table_name from user_tab_columns c
    where c.column_name in ('CREATED','CREATED_BY','UPDATED','UPDATED_BY')
    and c.TABLE_NAME = u.table_name
);
*/