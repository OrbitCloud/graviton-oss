create table oqf_logs (
  id             number default on null to_number(sys_guid(),'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX') primary key,
  created        timestamp default on null systimestamp,
  transaction_id varchar2(64 char),
  owner          varchar2(128 char),
  table_name     varchar2(128 char),
  evh_namespace  varchar2(256 char),
  evh_queue      varchar2(256 char),
  num_rows       number(10,0),
  bytes          number(20,0),
  send_time      number(12,2),
  response_code varchar2(3 char),
  text           varchar2(200 char),
  message        clob
) pctfree 0;


create index idx_oqflogs_ownname on oqf_logs (owner,table_name);
create index idx_oqflogs_created on oqf_logs (created);

create table oqf_log_settings (
  log_table           varchar2(128 char) primary key,
  credential          number references oqf_credentials(id),
  collection_endpoint varchar2(256 char),
  rule_immutable_id   varchar2(128 char),
  stream              varchar2(128 char),
  scope               varchar2(256 char),
  tenant              varchar2(128 char),
  created             date default on null sysdate
);

begin
  insert into oqf_log_settings
    (LOG_TABLE)
  values
    ('OQF_LOGS');
  commit;
end;
/

create or replace type t_logger as object (
  credential          number(38,0),
  collection_endpoint varchar2(256 char),
  rule_immutable_id   varchar2(128 char),
  stream              varchar2(128 char),
  scope               varchar2(256 char),
  tenant              varchar2(128 char),
  data                blob
);
/

declare
  l_schema      all_tables.owner%type;
  l_type_name   all_types.type_name%type := 'T_LOGGER';
  l_queue_table all_tables.table_name%type := 'QTABLE_LOGGER';
  l_queue_name  all_queues.name%type := 'QUEUE_LOGGER';
begin
  l_schema := SYS_CONTEXT('userenv', 'current_schema');
  sys.dbms_output.put_line('... Creating log queue');
  sys.dbms_aqadm.create_queue_table(queue_table => l_schema || '.' || l_queue_table, queue_payload_type => l_schema || '.' || l_type_name);
  sys.dbms_aqadm.create_queue(queue_name     => l_schema || '.' || l_queue_name,
                          queue_table    => l_schema || '.' || l_queue_table,
                          queue_type     => sys.dbms_aqadm.normal_queue,
                          max_retries    => 3,
                          retry_delay    => 10,
                          retention_time => 0,
                          comment        => 'Event Queue for sending log data to Azure');
  sys.dbms_output.put_line( '### Remember to start Logger queue when endpoints have been created');
  sys.dbms_output.put_line( 'begin sys.dbms_aqadm.start_queue(queue_name => '''|| l_schema || '.' || l_queue_name||'''); end;');

  sys.dbms_aq.register(reg_list => sys.aq$_reg_info_list(sys.aq$_reg_info(name      => l_schema || '.' || l_queue_name,
                                                                      namespace => sys.dbms_aq.namespace_aq,
                                                                      callback  => 'plsql://' || l_schema ||'.orb_log.log_callback',
                                                                      context   => null)),
                  reg_count => 1);
  commit;
end;
/