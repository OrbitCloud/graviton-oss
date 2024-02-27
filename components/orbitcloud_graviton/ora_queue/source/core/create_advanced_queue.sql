/* Queue Table for DML Changes */
create or replace type t_table_changes as object (
  event_time  date,
  queue_id    number(38,0),
  table_name  varchar2(120 char),
  azure_queue varchar2(120 char),
  data        clob
);
/

/* Create and start the queue */
declare
  l_schema      all_tables.owner%type;
  l_type_name   all_types.type_name%type := 'T_TABLE_CHANGES';
  l_queue_table all_tables.table_name%type := 'QTABLE_DML_CHANGES';
  l_queue_name  all_queues.name%type := 'QUEUE_DML';
begin
  l_schema := SYS_CONTEXT('userenv', 'current_schema');
  sys.dbms_output.put_line('... Creating base queue table and default queue');
  sys.dbms_aqadm.create_queue_table(queue_table => l_schema || '.' || l_queue_table, queue_payload_type => l_schema || '.' || l_type_name);
  sys.dbms_aqadm.create_queue(queue_name     => l_schema || '.' || l_queue_name,
                          queue_table    => l_schema || '.' || l_queue_table,
                          queue_type     => sys.dbms_aqadm.normal_queue,
                          max_retries    => 3,
                          retry_delay    => 0,
                          retention_time => 0,
                          comment        => 'Event Queue for Tracking Table DML');
  sys.dbms_aqadm.start_queue(queue_name => l_schema || '.' || l_queue_name);

  sys.dbms_aq.register(reg_list => sys.aq$_reg_info_list(sys.aq$_reg_info(name      => l_schema || '.' || l_queue_name,
                                                                      namespace => sys.dbms_aq.namespace_aq,
                                                                      callback  => 'plsql://' || l_schema ||'.az_change_notifications.aq_callback',
                                                                      context   => null)),
                  reg_count => 1);
  commit;
end;
/
