create or replace package body az_change_notifications is
  /*
    Enable Debug Mode:
    alter package az_change_notifications compile plsql_ccflags='debug_mode:true' reuse settings;
    Turn off is 'debug_mode:false'
    
    Changes in debug mode:
      * JSON Body is validated before being sent
  */

  e_message_too_large exception;
  pragma exception_init(e_message_too_large, -20101);
  e_send_error exception;
  pragma exception_init(e_send_error, -20102);

  c_all_row_minutes constant number(20, 6) := (1 / (24 * 60)) * 5; -- 5 minutes

  function get_queue_table return varchar2 deterministic is
  begin
    return SYS_CONTEXT('userenv', 'current_schema') || '.QUEUE_DML';
  end get_queue_table;

  procedure dequeue_and_send(p_queue in varchar2) is
    e_end_of_fetch exception;
    pragma exception_init(e_end_of_fetch, -25228);
  
    procedure dequeue(p_queue in varchar2) is
      l_dequeue_options    SYS.dbms_aq.dequeue_options_t;
      l_message_properties SYS.dbms_aq.message_properties_t;
      l_message_handle     raw(16);
      l_message            t_table_changes;
    begin
      l_dequeue_options.VISIBILITY   := SYS.dbms_aq.ON_COMMIT;
      l_dequeue_options.DEQUEUE_MODE := SYS.dbms_aq.REMOVE;
      l_dequeue_options.WAIT         := SYS.dbms_aq.NO_WAIT;
      SYS.dbms_aq.DEQUEUE(queue_name         => p_queue,
                          dequeue_options    => l_dequeue_options,
                          message_properties => l_message_properties,
                          payload            => l_message,
                          msgid              => l_message_handle);
      az_event_hubs.send(p_evh_queue => l_message.queue_id, p_payload => l_message.data);
      commit;
    end dequeue;
  begin
    <<dequeue_loop>>
    loop
      dequeue(p_queue => p_queue);
    end loop dequeue_loop;
  exception
    when e_end_of_fetch then
      null; -- Finished dequeuing messages
  end dequeue_and_send;

  procedure aq_callback(context in raw, reginfo in SYS.AQ$_REG_INFO, descr in SYS.AQ$_DESCRIPTOR, payload in raw, payloadl in number) is
  begin
    dequeue_and_send(p_queue => descr.queue_name);
    if 1 = 0 then
      /* Hide "Unused Variable hints", since these are required callback variables */
      sys.dbms_output.put_line('Content: ' || sys.utl_raw.cast_to_varchar2(context));
      sys.dbms_output.put_line('Registration Name: ' || reginfo.name);
      sys.dbms_output.put_line('Payload length: ' || sys.dbms_lob.getlength(payload) || ' - Registered length: ' || to_char(payloadl));
    end if;
  end aq_callback;

  procedure enqueue(p_queue_id in number, p_table in varchar2, p_azure_queue in varchar2, p_data in blob) is
    l_enqueue_options    sys.dbms_aq.enqueue_options_t;
    l_message_properties sys.dbms_aq.message_properties_t;
    l_message_handle     raw(16);
    l_message            t_table_changes;
  begin
    l_message := t_table_changes(event_time  => sysdate,
                                 queue_id    => p_queue_id,
                                 table_name  => p_table,
                                 azure_queue => p_azure_queue,
                                 data        => p_data);
  
    sys.dbms_aq.enqueue(queue_name         => get_queue_table,
                        enqueue_options    => l_enqueue_options,
                        message_properties => l_message_properties,
                        payload            => l_message,
                        msgid              => l_message_handle);
    commit;
  end enqueue;

  function get_rowdata(p_owner in varchar2, p_table in varchar2, p_rowid in varchar2) return clob is
    -- NOSONAR: non-deterministic
    l_table       oqf_tables.table_name%type;
    l_owner       all_tables.owner%type;
    l_columns     apex_t_varchar2;
    l_sql         varchar2(32767 char);
    l_result      clob;
    l_column_list varchar2(32767 char);
  begin
    l_table := sys.dbms_assert.simple_sql_name(upper(p_table));
    l_owner := sys.dbms_assert.schema_name(upper(p_owner));
  
    <<get_columns>>
    begin
      select lower(c.column_name)
        bulk collect
        into l_columns
        from oqf_table_columns c
       where c.table_name = l_table
         and c.owner = l_owner
       order by c.column_order;
    
      if l_columns.count = 0 then
        select lower(c.column_name)
          bulk collect
          into l_columns
          from all_tab_columns c
         where c.table_name = l_table
           and c.owner = l_owner
         order by c.column_id;
      end if;
    end get_columns;
  
    l_column_list := apex_String.join(p_table => l_columns, p_sep => ',');
  
    l_sql := 'select json_object(' || l_column_list || ' returning clob) as cols from ' || l_owner || '.' || l_table || ' where rowid=:1';
  
    execute immediate l_sql
      into l_result
      using p_rowid;
  
    return l_result;
  end get_rowdata;

  function append_row(p_table in varchar2, p_owner in varchar2, p_rowid in varchar2) return blob is
    -- NOSONAR: non-deterministic
    l_row    json_object_t;
    l_keys   json_key_list;
    l_key    varchar2(128 char);
    l_col    json_element_t;
    l_object json_object_t;
  begin
    l_row  := json_object_t.parse(get_rowdata(p_table => p_table, p_owner => p_owner, p_rowid => p_rowid));
    l_keys := l_row.get_Keys;
  
    l_object := json_object_t();
  
    <<cols>>
    for r in 1 .. l_keys.count loop
      l_col := l_row.get(l_keys(r));
      l_key := l_keys(r);
      case
        when l_col.is_String then
          l_object.put(key => lower(l_key), val => l_row.get_String(l_keys(r)));
        when l_col.is_Number then
          l_object.put(key => lower(l_key), val => l_row.get_Number(l_keys(r)));
        when l_col.is_Date then
          l_object.put(key => lower(l_key), val => l_row.get_Date(l_keys(r)));
        when l_col.is_Timestamp then
          l_object.put(key => lower(l_key), val => l_row.get_Timestamp(l_keys(r)));
        when l_row.get(l_keys(r)).is_Null then
          l_object.put_Null(key => lower(l_key));
        else
          l_object.put(key => lower(l_key), val => l_row.get_String(l_keys(r)));
      end case;
    end loop cols;
  
    return l_object.to_blob();
  end append_row;

  function changed_rows(p_table in varchar2, p_owner in varchar2, p_dags in date) return sys.chnf$_rdesc_array is
    -- NOSONAR: non-deterministic
    l_table  all_tables.table_name%type;
    l_owner  all_tables.owner%type;
    l_tabrow oqf_tables%rowtype;
    l_dags   date := p_dags;
    l_rowids sys.chnf$_rdesc_array;
    l_where  varchar2(32767 char);
    l_sql    varchar2(32767 char);
  begin
    l_table  := sys.dbms_assert.simple_sql_name(upper(p_table));
    l_owner  := sys.dbms_assert.schema_name(upper(p_owner));
    l_tabrow := get_table(p_owner => l_owner, p_table_name => l_table);
    case
      when l_tabrow.updcol is not null then
        l_where := ' where ' || l_tabrow.updcol || ' >= :1';
        l_sql   := 'select SYS.CHNF$_RDESC(0, rowid) from ' || l_owner || '.' || l_table || l_where;
        sys.dbms_output.put_line(l_sql);
        execute immediate l_sql bulk collect
          into l_rowids
          using l_dags;
      else
        l_sql := 'select SYS.CHNF$_RDESC(0, rowid) from ' || l_owner || '.' || l_table;
        execute immediate l_sql bulk collect
          into l_rowids;
    end case;
  
    orb_log.log_action(p_title   => 'changed_rows: ' || l_owner || '.' || l_table || ' result: ' || l_rowids.count || ' rows',
                       p_message => empty_clob());
  
    return l_rowids;
  
  end changed_rows;

  function get_update_column(p_table_name in varchar2, p_owner in varchar2) return varchar2 is
    -- NOSONAR: non-deterministic
    l_col oqf_tables.updcol%type;
  begin
    select updcol
      into l_col
      from oqf_tables c
     where c.table_name = p_table_name
       and c.owner = p_owner;
  
    return l_col;
  exception
    when no_data_Found then
      return null;
    when too_many_rows then
      raise;
  end get_update_column;

  function get_table(p_owner in varchar2, p_table_name in varchar2) return oqf_tables%rowtype is
    -- NOSONAR: non-deterministic
    l_table oqf_tables%rowtype;
  begin
    select *
      into l_table
      from oqf_tables
     where owner = p_owner
       and table_name = p_table_name;
    return l_table;
  exception
    when no_data_found then
      raise_application_error(-20000, 'Table ' || p_owner || '.' || p_table_name || ' is not defined in oqf_tables');
    when too_many_rows then
      raise_application_error(-20000, 'Table ' || p_owner || '.' || p_table_name || ' is defined multiple times in oqf_tables');
  end get_table;

  function get_table(p_qualified_table_name in varchar2) return oqf_tables%rowtype is
    -- NOSONAR: non-deterministic
    l_table oqf_tables%rowtype;
  begin
    select * into l_table from oqf_tables where owner || '.' || table_name = p_qualified_table_name;
    return l_table;
  exception
    when no_data_found then
      raise_application_error(-20000, 'Table ' || p_qualified_table_name || ' is not defined in oqf_tables');
    when too_many_rows then
      raise_application_error(-20000, 'Table ' || p_qualified_table_name || ' is defined multiple times in oqf_tables');
  end get_table;

  function get_event_queue(p_queue in number) return oqf_eventhub_queues%rowtype is
    -- NOSONAR: non-deterministic
    l_evh_queue oqf_eventhub_queues%rowtype;
  begin
    select * into l_evh_queue from oqf_eventhub_queues q where q.id = p_queue;
    return l_evh_queue;
  exception
    when no_data_found then
      raise_application_error(-20000, 'No Azure Event Hub Queue defined with id ' || p_queue);
    when too_many_rows then
      raise_application_error(-20000, 'Multiple Azure Event Hub Queues defined with id ' || p_queue);
  end get_event_queue;

  function get_event_hub(p_namespace in varchar2) return oqf_event_hubs%rowtype is
    -- NOSONAR: non-deterministic
    l_evh oqf_event_hubs%rowtype;
  begin
    select e.* into l_evh from oqf_event_hubs e where e.namespace = p_namespace;
    return l_evh;
  exception
    when no_data_Found then
      raise_application_error(-20000, 'No Azure Event Hub defined with namespace ' || p_namespace);
    when too_many_rows then
      raise_application_error(-20000, 'Multiple Azure Event Hubs defined with namespace ' || p_namespace);
  end get_event_hub;

  procedure validate_body(p_data in clob) is
    l_arr  json_array_t;
    l_jsn  json_object_t;
    l_body json_object_t;
  begin
    l_arr := json_array_t.parse(p_data);
    <<validate_rows>>
    for i in 0 .. l_arr.get_size - 1 loop
      l_jsn  := treat(l_arr.get(pos => i) as json_object_t);
      l_body := json_object_t.parse(l_jsn.get_string(key => 'Body'));
    end loop validate_rows;
  end validate_body;

  procedure validate_body(p_data in blob) is
    l_arr  json_array_t;
    l_jsn  json_object_t;
    l_body json_object_t;
  begin
    l_arr := json_array_t.parse(p_data);
    <<validate_rows>>
    for i in 0 .. l_arr.get_size - 1 loop
      l_jsn  := treat(l_arr.get(pos => i) as json_object_t);
      l_body := json_object_t.parse(l_jsn.get_string(key => 'Body'));
    end loop validate_rows;
  end validate_body;

  procedure enqueue_rowids(p_transaction_id in raw, p_rowids in sys.chnf$_rdesc_array, p_regid in number, p_table in oqf_tables%rowtype) is
    l_userprop  blob;
    l_payload   blob;
    l_sql       varchar2(32767 char);
    l_json      blob;
    l_cursor    sys_refcursor;
    l_maxrows   pls_integer;
    l_maxsize   pls_integer;
    l_rowcount  pls_integer;
    l_schema    oqf_tables.owner%type;
    l_upd_col   oqf_table_columns.column_name%type;
    l_trunked   date;
    l_evh       oqf_event_hubs%rowtype;
    l_evh_queue oqf_eventhub_queues%rowtype;
    l_fullname  varchar2(32767 char); -- NOSONAR - Combination of owner and table_name
    l_opnum     number; -- NOSONAR - pls_integer is not a valid type for json_object
  begin
    l_evh_queue := get_event_queue(p_queue => p_table.queue);
    l_evh       := get_event_hub(p_namespace => l_evh_queue.namespace);
  
    l_fullname := upper(p_table.owner || '.' || p_table.table_name);
  
    l_maxrows := l_evh.max_rows;
    l_maxsize := l_evh.max_size_kb * 1024; -- kb -> bytes
  
    l_schema  := lower(p_table.schema || '.' || p_table.table_name || '.' || p_table.version);
    l_upd_col := get_update_column(p_table_name => p_table.table_name, p_owner => p_table.owner);
  
    l_trunked := trunc(sysdate);
    l_opnum   := s_az_send_op.nextval;
    select json_object('transaction_id' value p_transaction_id,
                       'table' value l_fullname,
                       'dbcommit' value l_trunked,
                       'change_notification' value p_regid,
                       'dbname' value sys_context('USERENV', 'DB_NAME'),
                       'tenant' value - 1,
                       'machine' value sys_context('USERENV', 'SERVER_HOST'),
                       'type' value 'table',
                       'schema' value l_schema,
                       'updateColumn' value nvl(l_upd_col, '-1'),
                       'send_operation' value l_opnum returning blob)
      into l_userprop
      from dual;
  
    /*
    0 = upsert / Init
    2 = sys.dbms_change_notification.insertop
    4 = sys.dbms_change_notification.updateop
    8 = sys.dbms_change_notification.deleteop
    */
  
    l_sql := 'select json_object(''Body'' value az_change_notifications.get_rowdata(p_owner => :owner, p_table => :tabname, p_rowid => r.row_id),
                                          ''UserProperties'' value json_mergepatch(
                                                                        :uprop,
                                                                        json_object(
                                                                              ''rowid'' value rowidtochar(t.rowid),
                                                                              ''operation'' value decode(r.opflags, 0,''Upsert'',2,''Insert'',4,''Update'',8,''Delete'',''Init''),
                                                                              ''rowkey'' value ' || p_table.rowkey || ',
                                                                              ''partitionkey'' value ' ||
             nvl(p_table.partition_key, '''' || l_schema || '''') || '
                                                                        ) returning blob)
                                                                   returning blob) as obj
        from ' || l_fullname || ' t join table(:rowids) r on t.rowid = r.row_id' || case
               when p_table.sql_filter is not null then
                ' where ' || p_table.sql_filter
               else
                null
             end;
  
    open l_cursor for l_sql
      using p_table.owner, p_table.table_name, l_userprop, p_rowids;
  
    l_json     := sys.utl_raw.cast_to_raw('[]');
    l_rowcount := 0;
  
    fetch l_cursor
      into l_payload;
    <<json_loop>>
    while l_cursor%found loop
      l_rowcount := l_rowcount + 1; --  ## Using "l_rowcount" to skip the json parsing overhead of json_array_t.parse(l_json).get_size()
    
      if l_rowcount >= l_maxrows or sys.dbms_lob.getlength(l_json) + sys.dbms_lob.getlength(l_payload) + length(',') > l_maxsize then
        $if $$debug_mode $then
        validate_body(p_data => l_json);
        $end
        /* Buffer is full for Azure Event Hub, enqueue and reset */
        enqueue(p_queue_id => l_evh_queue.id, p_table => l_fullname, p_azure_queue => l_evh_queue.queue_name, p_data => l_json);
        l_json     := sys.utl_raw.cast_to_raw('[]');
        l_rowcount := 0;
      end if;
    
      select json_transform(l_json, append '$' = l_payload format json returning blob) into l_json from dual;
      fetch l_cursor
        into l_payload;
    end loop json_loop;
    /* l_json will always have data since queuing is only done when limits are reached */
    $if $$debug_mode $then
    validate_body(p_data => l_json);
    $end
    enqueue(p_queue_id => l_evh_queue.id, p_table => l_fullname, p_azure_queue => l_evh_queue.queue_name, p_data => l_json);
  end enqueue_rowids;

  procedure cqn_callback(ntfnds in SYS.chnf$_desc) is
    l_regid      user_subscr_registrations.reg_id%type;
    l_table_name oqf_tables.table_name%type;
    l_event_type pls_integer;
    l_numtables  pls_integer;
    l_dags       date;
  
    l_empty   boolean := false;
    l_rowids  SYS.CHNF$_RDESC_ARRAY;
    l_table   oqf_tables%rowtype;
    l_transid raw(8);
  begin
    l_dags       := sysdate - c_all_row_minutes;
    l_regid      := ntfnds.registration_id;
    l_numtables  := ntfnds.numtables;
    l_event_type := ntfnds.event_type;
    l_transid    := ntfnds.transaction_id;
  
    if l_event_type = sys.dbms_change_notification.event_objchange then
    
      <<t_table_loop>>
      for t in 1 .. l_numtables loop
        l_table_name := ntfnds.table_desc_array(t).table_name;
        l_table      := get_table(p_qualified_table_name => l_table_name);
      
        if (bitand(ntfnds.table_desc_array(t).Opflags, sys.dbms_change_notification.ALL_ROWS) != 0) then
          l_empty := true;
        end if;
      
        if l_empty then
          /* No rowids - cache invalidation initiated - gather rowids from update data columns */
          orb_log.log_action(p_title      => 'ALL_ROWS: reference date ' || to_char(l_dags, 'yyyy-mm-dd hh24:mi:ss'),
                             p_owner      => l_table.owner,
                             p_table_name => l_table.table_name,
                             p_transid    => l_transid,
                             p_message    => empty_clob());
          l_rowids := changed_rows(p_table => l_table.table_name, p_owner => l_table.owner, p_dags => l_dags);
        else
          l_rowids := ntfnds.table_desc_array(t).row_desc_array;
        end if;
      
        /* Rowid list,  */
        enqueue_rowids(p_transaction_id => l_transid, p_rowids => l_rowids, p_regid => l_regid, p_table => l_table);
      
      end loop t_table_loop;
    end if;
  
  exception
    when others then
      orb_log.log_action(p_title   => 'Table Callback ERROR ' || sqlcode,
                         p_message => sqlerrm || sys.utl_tcp.crlf || sys.dbms_utility.format_error_stack || sys.utl_tcp.crlf ||
                                      sys.dbms_utility.format_error_backtrace);
      raise;
  end cqn_callback;

  procedure change_registration(p_owner in varchar2, p_table in varchar2) is
    l_tablename oqf_tables.table_name%type;
    l_owner     oqf_tables.owner%type;
    l_tbl       oqf_tables%rowtype;
    l_fullname  varchar2(32767 char); -- NOSONAR - Combination of owner and table_name
    l_regds     sys.chnf$_reg_info;
    l_regid     user_subscr_registrations.reg_id%type;
    l_qosflags  user_subscr_registrations.qosflags%type;
    l_check     pls_integer;
    l_sql       varchar2(32767 char);
  begin
    l_tablename := sys.dbms_assert.simple_sql_name(upper(p_table));
    l_owner     := sys.dbms_assert.schema_name(upper(p_owner));
    l_tbl       := get_table(p_owner => l_owner, p_table_name => l_tablename);
  
    l_fullname := upper(l_tbl.owner || '.' || l_tbl.table_name);
  
    /* Deregister any existing registrations */
    <<deregister_loop>>
    for x in (select r.regid
                from user_change_notification_regs r
               where r.regid = l_tbl.regid
                  or replace(r.table_name, '"', null) = l_fullname) loop
      sys.dbms_change_notification.DEREGISTER(regid => x.regid);
    end loop deregister_loop;
  
    /***  Change Notification registration ***/
    l_qosflags := sys.dbms_change_notification.qos_reliable + sys.dbms_change_notification.qos_rowids;
    l_regds    := sys.chnf$_reg_info(callback          => sys_context('USERENV', 'CURRENT_SCHEMA') || '.' || $$plsql_unit || '.cqn_callback',
                                     qosflags          => l_qosflags,
                                     timeout           => 0,
                                     operations_filter => 0,
                                     transaction_lag   => 0);
  
    l_regid := sys.dbms_change_notification.new_reg_start(l_regds);
  
    l_sql := 'select 1 from ' || l_fullname || ' where 1 = 1 fetch next 1 row only';
    execute immediate l_sql
      into l_check;
    sys.dbms_change_notification.reg_end;
    sys.dbms_change_notification.set_rowid_threshold(tbname => l_fullname, threshold => 1000);
  
    /* Since we now have a new registration ID, we need to update the table no matter if p_populate_work_tables is false or true */
    update oqf_tables t set t.regid = l_regid where t.table_name = l_tbl.table_name;
    commit;
  end change_registration;

  procedure register_table(p_table             in varchar2,
                           p_queue             in number,
                           p_schema            in varchar2,
                           p_initial_data_push in boolean default false,
                           p_updated_column    in varchar2 default null,
                           p_rowkey            in varchar2 default null,
                           p_partition_key     in varchar2 default null,
                           p_column_list       in varchar2 default null) is
    l_table       varchar2(32767 char); -- NOSONAR - Table name with schema, can be fully qualified
    l_schema_name oqf_tables.owner%type;
    l_table_name  oqf_tables.table_name%type;
    l_ctab        oqf_tables%rowtype;
    l_jarr        json_array_t;
  begin
    l_table := sys.dbms_assert.QUALIFIED_SQL_NAME(p_table);
  
    if instr(l_table, '.') = 0 then
      l_table_name  := l_table;
      l_schema_name := sys_context('USERENV', 'CURRENT_SCHEMA');
    else
      l_table_name  := substr(l_table, instr(l_table, '.', -1) + 1, 128);
      l_schema_name := substr(l_table, 1, instr(l_table, '.') - 1);
    end if;
  
    /***  Populate Working tables  ***/
    <<populate_working_tables>>
    begin
      l_ctab.table_name := l_table_name;
      l_ctab.owner      := l_Schema_name;
    
      l_ctab.queue         := p_queue;
      l_ctab.schema        := p_schema;
      l_ctab.version       := 'v1';
      l_ctab.updcol        := p_updated_column;
      l_ctab.created       := sysdate;
      l_ctab.updated       := sysdate;
      l_ctab.partition_key := p_partition_key;
    
      if p_rowkey is not null then
        l_ctab.rowkey := p_rowkey;
      else
        select listagg(cc.column_name, ' || ') within group(order by cc.position)
          into l_ctab.rowkey
          from all_constraints c
          join all_cons_columns cc
            on c.constraint_name = cc.constraint_name
         where cc.owner = l_schema_name
           and c.table_name = l_table_name
           and c.constraint_type = 'P';
      
        if l_ctab.rowkey is null then
          <<get_first_column>>
          begin
            select column_name
              into l_ctab.rowkey
              from all_tab_columns tc
             where tc.owner = l_schema_name
               and tc.table_name = l_table_name
               and column_id = 1;
          exception
            when no_data_found then
              raise_application_error(-20404, 'Table ' || l_table_name || ' has no primary key and no columns');
            when too_many_rows then
              raise_application_error(-20404, 'Table ' || l_table_name || ' has no primary key and multiple columns');
          end get_first_column;
        end if;
      end if;
    
      insert into oqf_tables values l_ctab;
    
      if p_column_list is null or json_array_t.parse(p_column_list).get_size = 0 then
        insert into oqf_table_columns
          (owner, table_name, column_name, column_order)
          select c.owner, c.table_name, c.column_name, c.column_id
            from all_tab_columns c
           where c.owner = l_schema_name
             and c.table_name = l_table_name;
      else
        l_jarr := json_array_t.parse(p_column_list);
      
        <<column_list>>
        declare
          l_column sys.all_tab_columns.column_name%type;
        begin
          <<insert_loop>>
          for i in 0 .. l_jarr.get_size - 1 loop
            l_column := l_jarr.get_string(i);
            insert into oqf_table_columns
              (owner, table_name, column_name, column_order)
            values
              (l_schema_name, l_table_name, l_column, i + 1);
          end loop insert_loop;
        end column_list;
      end if;
    exception
      when dup_val_on_index then
        /* Table already present */
        null;
    end populate_working_tables;
  
    /***  Register Event Hub Queue + initial load ***/
  
    change_registration(p_owner => l_Schema_name, p_table => l_table_name);
    commit;
  
    if p_initial_data_push then
      push_all_rows(p_owner => l_schema_name, p_table => l_table_name);
    end if;
  end register_table;

  procedure push_all_rows(p_owner in varchar2, p_table in varchar2) is
    l_ctab   oqf_tables%rowtype;
    l_cur    sys_refcursor;
    l_sql    varchar2(32767 char);
    l_rowids sys.chnf$_rdesc_array;
  begin
    l_ctab := get_table(p_owner => p_owner, p_table_name => p_table);
  
    l_sql := 'select sys.chnf$_rdesc(-1, rowid) as rid from ' || l_ctab.owner || '.' || l_ctab.table_name || case
               when l_ctab.sql_filter is not null then
                ' where ' || l_ctab.sql_filter
               else
                null
             end;
    open l_cur for l_sql;
    fetch l_cur bulk collect
      into l_rowids;
    close l_cur;
  
    enqueue_rowids(p_transaction_id => utl_i18n.string_to_raw(data => 'ALL_ROWS'), p_rowids => l_rowids, p_regid => -1, p_table => l_ctab);
  end push_all_rows;

  procedure deregister_table(p_owner in varchar2, p_table in varchar2, p_cleanup in boolean default true) is
    l_table   oqf_tables.table_name%type;
    l_owner   oqf_tables.owner%type;
    l_tabconf oqf_tables%rowtype;
  begin
    l_table := sys.dbms_assert.simple_sql_name(upper(p_table));
    l_owner := sys.dbms_assert.schema_name(upper(p_owner));
  
    <<table_setup>>
    begin
      <<change_registration>>
      l_tabconf := get_table(p_owner => l_owner, p_table_name => l_table);
      if l_tabconf.regid is null then
        <<subcription>>
        begin
          select r.regid
            into l_tabconf.regid
            from user_change_notification_regs r
           where replace(r.table_name, '"', null) = l_owner || '.' || l_table;
        exception
          when no_data_found then
            null;
          when too_many_rows then
            raise_application_error(-20000, 'Multiple registrations for table ' || l_owner || '.' || l_table);
        end subcription;
      end if;
    
      if l_tabconf.regid is not null then
        sys.dbms_change_notification.deregister(regid => l_tabconf.regid);
      else
        /* Record exists in oqf_TABLES but regid is null */
        null;
      end if;
    exception
      when no_data_found then
        /* Missing entry in oqf_tables and not registered in user_change_notification_regs */
        null;
    end table_setup;
    if p_cleanup then
      delete from oqf_table_columns c where c.table_name in (l_table);
      delete from oqf_tables t where t.table_name in (l_table);
      commit;
    end if;
  
  end deregister_table;

  function generate_schema(p_table in varchar2) return clob is
    -- NOSONAR: non-deterministic
    l_tab      oqf_tables%rowtype;
    l_schema   json_object_t := json_object_t();
    l_required json_array_t := json_array_t();
    l_obj      json_object_t := json_object_t();
    l_string   json_object_t := json_object_t();
    l_number   json_object_t := json_object_t();
    l_uri      varchar2(2000 char);
  begin
    l_tab := get_table(p_qualified_table_name => p_table);
  
    l_uri := az_event_hubs.get_queue_url(p_evh_queue => l_tab.queue);
  
    l_string.put(key => 'type', val => 'string');
    l_number.put(key => 'type', val => 'number');
  
    l_schema.put(key => '$id', val => l_uri);
    l_schema.put(key => '$schema', val => 'https://json-schema.org/draft/2020-12/schema#');
    l_schema.put(key => 'title', val => 'Generated schema for  ' || p_table);
    l_schema.put(key => 'type', val => 'object');
  
    l_obj.put(key => 'rowid', val => l_string);
    l_required.append('rowid');
    l_obj.put(key => 'send_operation', val => l_number);
    l_required.append('send_operation');
    l_obj.put(key => 'operation', val => l_string);
  
    <<table_columns>>
    for i in (select tc.column_name, t.data_type, t.nullable
                from all_tab_columns t
                join oqf_table_columns tc
                  on tc.table_name = t.table_name
                 and tc.column_name = t.column_name
               where t.owner || '.' || t.table_name = sys_context('USERENV', 'CURRENT_SCHEMA') || '.' || l_tab.table_name
               order by tc.column_order) loop
      l_obj.put(key => lower(i.column_name),
                val => case
                         when i.data_type in ('NUMBER', 'FLOAT', 'BINARY_DOUBLE') then
                          l_number
                         else
                          l_string
                       end);
      if i.nullable = 'N' then
        l_required.append(lower(i.column_name));
      end if;
    end loop table_columns;
  
    l_schema.put(key => 'properties', val => l_obj);
    l_schema.put(key => 'required', val => l_required);
  
    return l_schema.to_Clob();
  end generate_schema;

end az_change_notifications;
/