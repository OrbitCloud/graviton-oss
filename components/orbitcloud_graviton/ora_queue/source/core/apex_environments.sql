create table oqf_environments (
   id          number default on null to_number(sys_guid(),'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX') primary key,
   name        varchar2(200 char) not null,
   description varchar2(400),
   created     date default on null sysdate,
   created_by  varchar2(256 char),
   updated     date,
   updated_by  varchar2(256 char)
);


create table oqf_environment_schemas (
   id          number default on null to_number(sys_guid(),'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX') primary key,
   environment number references oqf_environments(id) not null,
   owner       varchar2(128 char) not null,
   all_tables  number(1,0) default on null 1,
   tablearr    blob,
   created     date default on null sysdate,
   created_by  varchar2(256 char),
   updated     date,
   updated_by  varchar2(256 char),
   constraint  chk_alltable_bool check (all_tables in (0,1)),
   constraint  chk_tablearr check (tablearr is json)
);

insert into OQF_ENVIRONMENTS (NAME,DESCRIPTION) values ('Default','Default Environment');
commit;

create or replace function env_table_list(p_environment in number) return varchar2 SQL_MACRO is
begin
  return q'{
select s.owner || '.' || t.table_name as fullname
  from oqf_environment_schemas s
  join all_tables t
    on s.owner = t.owner
 where s.all_tables = 1
   and s.environment = env_table_list.p_environment
union all
select s.owner || '.' || j.tabname as fullname
  from oqf_environment_schemas s
  join json_table(s.tablearr, '$[*]' columns(tabname varchar2(128) path '$')) j
    on 1 = 1
 where s.all_tables = 0
  and s.environment = env_table_list.p_environment
}';
end env_table_list;
/