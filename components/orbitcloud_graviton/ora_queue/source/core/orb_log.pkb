create or replace package body orb_log is

  procedure log_action(p_title      in varchar2,
                       p_owner      in varchar2 default null,
                       p_table_name in varchar2 default null,
                       p_namespace  in varchar2 default null,
                       p_queue      in varchar2 default null,
                       p_rows       in number default null,
                       p_time       in number default null,
                       p_bytes      in number default null,
                       p_response   in varchar2 default null,
                       p_transid    in varchar2 default null,
                       p_message    in clob default null) is
    pragma autonomous_transaction;
  begin
    insert into oqf_logs
      (created, owner, table_name, evh_namespace, evh_queue, num_rows, text, bytes, send_time, transaction_id, message, response_code)
    values
      (systimestamp,
       substr(p_owner, 1, 128),
       substr(p_table_name, 1, 128),
       substr(p_namespace, 1, 256),
       substr(p_queue, 1, 256),
       p_rows,
       substr(p_title, 1, 200),
       p_bytes,
       p_time,
       substr(p_transid, 1, 64),
       p_message,
       p_response);
    commit;
  end log_action;

  procedure log_action(p_title      in varchar2,
                       p_owner      in varchar2 default null,
                       p_table_name in varchar2 default null,
                       p_namespace  in varchar2 default null,
                       p_queue      in varchar2 default null,
                       p_rows       in number default null,
                       p_time       in number default null,
                       p_bytes      in number default null,
                       p_response   in varchar2 default null,
                       p_transid    in varchar2 default null,
                       p_message    in blob default null) is
    pragma autonomous_transaction;
  begin
    log_action(p_title      => p_title,
               p_owner      => p_owner,
               p_table_name => p_table_name,
               p_namespace  => p_namespace,
               p_queue      => p_queue,
               p_rows       => p_rows,
               p_time       => p_time,
               p_bytes      => p_bytes,
               p_response   => p_response,
               p_transid    => p_transid,
               p_message    => to_clob(p_message));
  end log_action;

  procedure log_callback(context in raw, reginfo in SYS.AQ$_REG_INFO, descr in SYS.AQ$_DESCRIPTOR, payload in raw, payloadl in number) is
    e_end_of_fetch exception;
    pragma exception_init(e_end_of_fetch, -25228);
  
    l_dequeue_options    dbms_aq.dequeue_options_t;
    l_message_properties dbms_aq.message_properties_t;
    l_message_handle     raw(16);
    l_payload            t_logger;
    l_url                oqf_azure_service_uris.uri%type;
    l_token              varchar2(32767 char);
    l_resp               clob;
  begin
    l_dequeue_options.VISIBILITY   := SYS.dbms_aq.ON_COMMIT;
    l_dequeue_options.DEQUEUE_MODE := SYS.dbms_aq.REMOVE;
    l_dequeue_options.WAIT         := SYS.dbms_aq.NO_WAIT;
  
    <<dequeue_loop>>
    loop
      sys.dbms_aq.dequeue(queue_name         => descr.queue_name,
                      dequeue_options    => l_dequeue_options,
                      message_properties => l_message_properties,
                      payload            => l_payload,
                      msgid              => l_message_handle);
    
      l_url := az_event_hubs.azure_request(p_service => 'OAuth2', p_action => 'Authenticate');
      l_url := replace(l_url, '{tenantId}', l_payload.tenant);
    
      l_token := json_value(az_event_hubs.entraAuthenticationToken(p_token_url  => l_url,
                                                                   p_credential => l_payload.credential,
                                                                   p_scope      => l_payload.scope),
                            '$.access_token');
    
      apex_web_service.set_request_headers(p_name_01 => 'Content-Type', p_value_01 => 'application/json', p_reset => true);
    
      apex_web_service.oauth_set_token(p_token => l_token);
      l_resp := apex_web_service.make_rest_request(p_url         => l_payload.collection_endpoint || '/dataCollectionRules/' ||
                                                                    l_payload.rule_immutable_id || '/streams/' || l_payload.stream ||
                                                                    '?api-version=2023-01-01',
                                                   p_http_method => 'POST',
                                                   p_body_blob   => l_payload.data,
                                                   p_scheme      => 'OAUTH_CLIENT_CRED');
      sys.dbms_output.put_line(apex_web_service.g_status_code);
      sys.dbms_output.put_line(l_resp);
    end loop dequeue_loop;
  
    if 1 = 0 then
      /* Hide "Unused Variable hints", since these are required callback variables */
      sys.dbms_output.put_line('Content: ' || sys.utl_raw.cast_to_varchar2(context));
      sys.dbms_output.put_line('Registration Name: ' || reginfo.name);
      sys.dbms_output.put_line('Payload length: ' || sys.dbms_lob.getlength(payload) || ' - Registered length: ' || to_char(payloadl));
    end if;
  exception
    when e_end_of_fetch then
      null; -- Finished dequeuing messages
  end log_callback;

  procedure uploadrows(p_rowids in sys.chnf$_rdesc_array) is
    l_payload            t_logger;
    l_data               blob;
    l_log                oqf_log_settings%rowtype;
    l_enqueue_options    dbms_aq.enqueue_options_t;
    l_message_properties dbms_aq.message_properties_t;
    l_msgid              raw(16);
    l_enqueue            boolean := false;
  begin
    <<check_queue_status>>
    for i in (select name
                from user_queues
               where name = 'QUEUE_LOGGER'
                 and trim(enqueue_enabled)='YES') loop
      l_enqueue := true;
    end loop check_queue_status;
  
    if l_enqueue then
      <<settings>>
      begin
        select * into l_log from oqf_log_settings where log_table = 'OQF_LOGS';
      exception
        when no_data_found then
          raise;
        when too_many_rows then
          raise;
      end settings;
    
      select json_arrayagg(json_object('machine' value sys_context('USERENV', 'SERVER_HOST'),
                                       'dbname' value sys_context('USERENV', 'DB_NAME'),
                                       'schema' value sys_context('USERENV', 'CURRENT_SCHEMA'),
                                       'table' value 'OQF_LOGS',
                                       'data' value json_object('id' value trim(to_char(l.id, '99999999999999999999999999999999999999')),
                                                   l.created,
                                                   l.owner,
                                                   l.table_name,
                                                   l.evh_namespace,
                                                   l.evh_queue,
                                                   l.num_rows,
                                                   l.text,
                                                   l.message,
                                                   l.bytes,
                                                   l.send_time,
                                                   l.response_code,
                                                   l.transaction_id absent on null returning blob) returning blob) returning blob)
        into l_data
        from oqf_logs l
        join table(p_rowids) r
          on l.rowid = r.row_id;
    
      l_payload := t_logger(credential          => l_log.credential,
                            collection_endpoint => l_log.collection_endpoint,
                            rule_immutable_id   => l_log.rule_immutable_id,
                            stream              => l_log.stream,
                            scope               => l_log.scope,
                            tenant              => l_log.tenant,
                            data                => l_data);
    
      sys.dbms_aq.enqueue(queue_name         => 'QUEUE_LOGGER',
                      enqueue_options    => l_enqueue_options,
                      message_properties => l_message_properties,
                      payload            => l_payload,
                      msgid              => l_msgid);
      commit;
    end if;
  end uploadrows;

  procedure callback(ntfnds in SYS.chnf$_desc) is
    /*l_table_name oqf_tables.table_name%type;*/
    l_empty      boolean := false;
  begin
    /* The LOG_ACTION procedure is pragma autonomous and should always just be notifying of a single row insert */
  
    if ntfnds.event_type = sys.dbms_change_notification.event_objchange then
      /* Data change */
      <<t_table_loop>>
      for t in 1 .. ntfnds.numtables loop
        /*l_table_name := ntfnds.table_desc_array(t).table_name;*/
        l_empty      := (bitand(ntfnds.table_desc_array(t).Opflags, sys.dbms_change_notification.ALL_ROWS) != 0);
        if not l_empty then
          uploadrows(p_rowids => ntfnds.table_desc_array(t).row_desc_array);
        end if;
      end loop t_table_loop;
    end if;
  end callback;

  procedure register_log_cqn is
    pragma autonomous_transaction;
    l_regds    sys.chnf$_reg_info;
    l_regid    user_subscr_registrations.reg_id%type;
    l_qosflags user_subscr_registrations.qosflags%type;
    l_check    pls_integer;
    l_sql      varchar2(32767 char);
    l_fullname varchar2(32767 char);
  begin
    l_fullname := sys_context('USERENV', 'CURRENT_SCHEMA') || '.OQF_LOGS';
  
    /* Note, not using qos_reliable:
    QOS_RELIABLE (0x1): Notifications are reliable (persistent) and survive instance death. This means that on an instance death in an Oracle RAC cluster, 
    surviving instances will be able to deliver any queued invalidations. Similarly, pending invalidations can be delivered on instance restart, 
    in a single instance configuration. The disadvantage is that there is a CPU cost/ latency involved in inserting the invalidation message to a 
    persistent store. If this parameter is false, then server side CPU and latency are minimized, because invalidations are buffered into an in memory 
    queue but the client could lose invalidation messages on an instance shutdown.
    */
    l_qosflags := sys.dbms_change_notification.qos_rowids;
    l_regds    := sys.chnf$_reg_info(callback          => sys_context('USERENV', 'CURRENT_SCHEMA') || '.' || $$plsql_unit || '.callback',
                                     qosflags          => l_qosflags,
                                     timeout           => 0,
                                     operations_filter => sys.dbms_change_notification.insertop, /* We only want inserts, not deletes or updates */
                                     transaction_lag   => 0);
  
    l_regid := sys.dbms_change_notification.new_reg_start(l_regds);
    sys.dbms_output.put_line(l_regid);
    l_sql := 'select 1 from ' || l_fullname || ' where 1 = 1 fetch next 1 row only';
    execute immediate l_sql
      into l_check;
    sys.dbms_change_notification.reg_end;
    commit;
  end register_log_cqn;

end orb_log;
/