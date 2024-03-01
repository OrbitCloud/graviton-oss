create or replace package body az_change_notifications is
  e_message_too_large exception;
  pragma exception_init(e_message_too_large, -20101);
  e_send_error exception;
  pragma exception_init(e_send_error, -20102);

  function get_queue_table return varchar2 is
  begin
    return SYS_CONTEXT('userenv', 'current_schema') || '.QUEUE_DML';
  end get_queue_table;

  procedure log_action(p_title in varchar2, p_message in clob) is
    pragma autonomous_transaction;
  begin
    insert into oqf_log (created, text, message) values (systimestamp, substr(p_title, 1, 200), p_message);
    commit;
  end log_action;

  procedure dequeue_and_send(p_queue in varchar2) is
    e_end_of_fetch exception;
    pragma exception_init(e_end_of_fetch, -25228);
    l_dequeue_options    SYS.dbms_aq.dequeue_options_t;
    l_message_properties SYS.dbms_aq.message_properties_t;
    l_message_handle     raw(16);
    l_message            t_table_changes;
  begin
    <<dequeue_loop>>
    loop
      l_dequeue_options.VISIBILITY   := SYS.dbms_aq.ON_COMMIT;
      l_dequeue_options.DEQUEUE_MODE := SYS.dbms_aq.REMOVE;
      l_dequeue_options.WAIT         := SYS.dbms_aq.NO_WAIT;
      SYS.dbms_aq.DEQUEUE(queue_name         => p_queue,
                          dequeue_options    => l_dequeue_options,
                          message_properties => l_message_properties,
                          payload            => l_message,
                          msgid              => l_message_handle);
      -- log_action(p_title => 'Dequeue and send', p_message => l_message.data);
      az_event_hubs.send(p_evh_queue => l_message.queue_id, p_payload => l_message.data);
      commit;
    end loop dequeue_loop;
  exception
    when e_end_of_fetch then
      null; -- allt komi�
  end dequeue_and_send;

  procedure aq_callback(context in raw, reginfo in SYS.AQ$_REG_INFO, descr in SYS.AQ$_DESCRIPTOR, payload in raw, payloadl in number) is
  begin
    dequeue_and_send(p_queue => descr.queue_name);
    if 1 = 0 then
      sys.dbms_output.put_line('Content: ' || sys.utl_raw.cast_to_varchar2(context));
      sys.dbms_output.put_line('Registration Name: ' || reginfo.name);
      sys.dbms_output.put_line('Payload length: ' || sys.dbms_lob.getlength(payload) || ' - Registered length: ' || to_char(payloadl));
    end if;
  end aq_callback;

  procedure enqueue(p_queue_id in number, p_table in varchar2, p_azure_queue in varchar2, p_data in clob) is
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

  function append_row(p_table in varchar2, p_owner in varchar2, p_rowid in varchar2) return clob is
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
  
    return l_object.to_clob();
  end append_row;

  function changed_rows(p_table in varchar2, p_owner in varchar2, p_dags in date) return sys.chnf$_rdesc_array is
    l_table       all_tables.table_name%type;
    l_owner       all_tables.owner%type;
    l_col_updated all_tab_columns.column_name%type;
    l_dags        date := p_dags;
    l_rowids      sys.chnf$_rdesc_array;
    l_where       varchar2(32767 char);
    l_sql         varchar2(32767 char);
  begin
    l_table := sys.dbms_assert.simple_sql_name(upper(p_table));
    l_owner := sys.dbms_assert.schema_name(upper(p_owner));
  
    <<get_updated_column>>
    begin
      select column_name
        into l_col_updated
        from oqf_table_columns
       where table_name = l_table
         and owner = l_owner
         and is_updated_date = 1;
    exception
      when no_data_found then
        l_col_updated := null;
    end get_updated_column;
  
    case
      when l_col_updated is not null then
        l_where := ' where ' || l_col_updated || ' >= :1';
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
  
    log_action(p_title => 'changed_rows: ' || l_owner || '.' || l_table || ' result: ' || l_rowids.count || ' rows', p_message => null);
  
    return l_rowids;
  
  end changed_rows;

  function get_update_column(p_table_name in varchar2, p_owner in varchar2) return varchar2 is
    l_col oqf_table_columns.column_name%type;
  begin
    select column_name
      into l_col
      from oqf_table_columns c
     where c.table_name = p_table_name
       and c.owner = p_owner
       and c.is_updated_date = 1;
  
    return l_col;
  exception
    when no_data_Found then
      return null;
  end get_update_column;

  procedure enqueue_rowids(p_rowids in sys.chnf$_rdesc_array, p_regid in number, p_table in oqf_tables%rowtype) is
    l_userprop  clob;
    l_payload   clob;
    l_sql       varchar2(32767 char);
    l_json      clob;
    l_cursor    sys_refcursor;
    l_maxrows   pls_integer;
    l_maxsize   pls_integer;
    l_rowcount  pls_integer := 0;
    l_schema    oqf_tables.owner%type;
    l_upd_col   oqf_table_columns.column_name%type;
    l_trunked   date;
    l_evh       oqf_event_hubs%rowtype;
    l_evh_queue oqf_eventhub_queues%rowtype;
    l_fullname  varchar2(dbms_standard.ORA_MAX_NAME_LEN + dbms_standard.ORA_MAX_NAME_LEN + 1);
  begin
    select * into l_evh_queue from oqf_eventhub_queues q where q.id = p_table.queue;
    select e.* into l_evh from oqf_event_hubs e where e.namespace = l_evh_queue.namespace;
  
    l_fullname := upper(p_table.owner || '.' || p_table.table_name);
  
    l_maxrows := l_evh.max_rows;
    l_maxsize := l_evh.max_size_kb * 1024; -- kb -> bytes
  
    l_schema  := lower(p_table.owner || '.' || p_table.table_name || '.' || p_table.version);
    l_upd_col := get_update_column(p_table_name => p_table.table_name, p_owner => p_table.owner);
  
    l_trunked := trunc(sysdate);
    select json_object('table' value l_fullname,
                       'dbcommit' value l_trunked,
                       'change_notification' value p_regid,
                       'dbname' value sys_context('USERENV', 'DB_NAME'),
                       'tenant' value - 1,
                       'machine' value sys_context('USERENV', 'SERVER_HOST'),
                       'type' value 'table',
                       'schema' value l_schema,
                       'updateColumn' value nvl(l_upd_col, '-1'),
                       'send_operation' value s_az_send_op.nextval)
      into l_userprop
      from dual;
  
    /*
    0 = upsert / Init
    2 = sys. dbms_change_notification.insertop
    4 = sys. dbms_change_notification.updateop
    8 = sys. dbms_change_notification.deleteop
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
                                                                        ) returning clob)
                                                                   returning clob) as obj
        from ' || l_fullname || ' t join table(:rowids) r on t.rowid = r.row_id';

    open l_cursor for l_sql
      using p_table.owner, p_table.table_name, l_userprop, p_rowids;
  
    l_json     := '[]';
    l_rowcount := 0;
    <<json_loop>>
    loop
      fetch l_cursor
        into l_payload;
      exit json_loop when l_cursor%notfound;
      l_rowcount := l_rowcount + 1; --  ## Using "l_rowcount" to skip the json parsing overhead of json_array_t.parse(l_json).get_size() 
    
      if l_rowcount >= l_maxrows or sys.dbms_lob.getlength(l_json) + sys.dbms_lob.getlength(l_payload) + length(',') > l_maxsize then
      
        enqueue(p_queue_id => l_evh_queue.id, p_table => p_table.table_name, p_azure_queue => l_evh_queue.queue_name, p_data => l_json);
        l_json     := '[]';
        l_rowcount := 1;
      end if;
    
      select json_transform(l_json, append '$' = l_payload format json returning clob) into l_json from dual;
    
    end loop json_loop;
    /* l_json will always have data since queuing is only done when limits are reached */
    enqueue(p_queue_id => l_evh_queue.id, p_table => p_table.table_name, p_azure_queue => l_evh_queue.queue_name, p_data => l_json);
  end enqueue_rowids;

  procedure cqn_callback(ntfnds in SYS.chnf$_desc) is
    l_regid      user_subscr_registrations.reg_id%type;
    l_table_name oqf_tables.table_name%type;
    l_event_type pls_integer;
    l_numtables  pls_integer;
    --l_numrows    pls_integer;
    l_dags date;
  
    l_empty     boolean := false;
    l_rowids    SYS.CHNF$_RDESC_ARRAY;
    l_table     oqf_tables%rowtype;
    l_evh       oqf_event_hubs%rowtype;
    l_evh_queue oqf_eventhub_queues%rowtype;
  begin
    l_dags       := sysdate - (1 / (24 * 60));
    l_regid      := ntfnds.registration_id;
    l_numtables  := ntfnds.numtables;
    l_event_type := ntfnds.event_type;
  
    if l_event_type = sys. dbms_change_notification.event_objchange then
      <<t_table_loop>>
      for t in 1 .. l_numtables loop
        l_table_name := ntfnds.table_desc_array(t).table_name;
        declare
          l_tarr apex_t_varchar2;
        begin
          l_tarr := apex_string.split(p_str => l_table_name, p_sep => '.');
        
          select *
            into l_table
            from oqf_tables
           where owner = l_tarr(1)
             and table_name = l_tarr(2);
        exception
          when no_data_found then
            null; -- No Azure Table Storage defined, data logged but not pushed to queue
        end;
        select * into l_evh_queue from oqf_eventhub_queues q where q.id = l_table.queue;
        select e.* into l_evh from oqf_event_hubs e where e.namespace = l_evh_queue.namespace;
      
        if (bitand(ntfnds.table_desc_array(t).Opflags, sys. dbms_change_notification.ALL_ROWS) != 0) then
          l_empty := true;
        end if;
      
        if l_empty then
          /* No rowids - cache invalidation initiated - gather rowids from update data columns */
          l_rowids := changed_rows(p_table => l_table.table_name, p_owner => l_table.owner, p_dags => l_dags);
        else
          l_rowids := ntfnds.table_desc_array(t).row_desc_array;
        end if;
      
        /* Rowid list,  */
        enqueue_rowids(p_rowids => l_rowids, p_regid => l_regid, p_table => l_table);
      
      end loop t_table_loop;
    end if;
  
  exception
    when others then
      log_action(p_title   => 'Table Callback ERROR ' || sqlcode,
                 p_message => sqlerrm || sys.utl_tcp.crlf || sys.dbms_utility.format_error_stack || sys.utl_tcp.crlf ||
                              sys.dbms_utility.format_error_backtrace);
      raise;
  end cqn_callback;

  procedure change_registration(p_owner in varchar2, p_table in varchar2) is
    l_tbl      oqf_tables%rowtype;
    l_fullname varchar2(dbms_standard.ORA_MAX_NAME_LEN + dbms_standard.ORA_MAX_NAME_LEN + 1);
    l_regds    sys.chnf$_reg_info;
    l_regid    user_subscr_registrations.reg_id%type;
    l_qosflags user_subscr_registrations.qosflags%type;
    l_check    pls_integer;
  begin
    select *
      into l_tbl
      from oqf_tables
     where owner = p_owner
       and table_name = p_table;
    l_fullname := upper(l_tbl.owner || '.' || l_tbl.table_name);
  
    for x in (select r.regid
                from user_change_notification_regs r
               where r.regid = l_tbl.regid
                  or replace(r.table_name, '"', null) = l_fullname) loop
      sys.dbms_change_notification.DEREGISTER(regid => x.regid);
    end loop;
  
    /***  Change Notification registration ***/
    l_qosflags := sys. dbms_change_notification.qos_reliable + sys.dbms_change_notification.qos_rowids;
    l_regds    := sys.chnf$_reg_info(callback          => sys_context('USERENV', 'CURRENT_SCHEMA') || '.' || $$plsql_unit || '.cqn_callback',
                                     qosflags          => l_qosflags,
                                     timeout           => 0,
                                     operations_filter => 0,
                                     transaction_lag   => 0);
  
    l_regid := sys. dbms_change_notification.new_reg_start(l_regds);
    execute immediate 'select 1 from ' || l_fullname || ' where 1 = 1 fetch next 1 row only'
      into l_check;
    sys.dbms_change_notification.reg_end;
    sys.dbms_change_notification.set_rowid_threshold(tbname => l_fullname, threshold => 1000);
  
    /* Since we now have a new registration ID, we need to update the table no matter if p_populate_work_tables is false or true */
    update oqf_tables t set t.regid = l_regid where t.table_name = l_tbl.table_name;
    commit;
  end change_registration;

  procedure register_table(p_table             in varchar2,
                           p_queue             in number,
                           p_initial_data_push in boolean default false,
                           p_updated_column    in varchar2 default null,
                           p_rowkey            in varchar2 default null,
                           p_partition_key     in varchar2 default null,
                           p_column_list       in varchar2 default null) is
    l_table       varchar2(dbms_standard.ora_max_name_len + dbms_standard.ora_max_name_len + 1 char);
    l_schema_name oqf_tables.owner%type;
    l_table_name  oqf_tables.table_name%type;
    l_ctab        oqf_tables%rowtype;
    l_jarr        json_array_t;
    l_colarr      apex_t_varchar2;
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
      l_ctab.version       := 'v1';
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
          select column_name
            into l_ctab.rowkey
            from all_tab_columns tc
           where tc.owner = l_schema_name
             and tc.table_name = l_table_name
             and column_id = 1;
        end if;
      end if;
    
      insert into oqf_tables values l_ctab;
    
      if p_column_list is null or json_array_t.parse(p_column_list).get_size = 0 then
        insert into oqf_table_columns
          (owner, table_name, column_name, is_updated_date, column_order)
          select c.owner,
                 c.table_name,
                 c.column_name,
                 case
                   when p_updated_column is null then
                    0
                   when p_updated_column = c.column_name then
                    1
                   else
                    0
                 end,
                 c.column_id
            from all_tab_columns c
           where c.owner = l_schema_name
             and c.table_name = l_table_name;
      else
        l_jarr   := json_array_t.parse(p_column_list);
        l_colarr := apex_t_varchar2();
        for i in 0 .. l_jarr.get_size - 1 loop
          l_colarr.extend;
          l_colarr(l_colarr.count) := l_jarr.get_String(i);
        end loop;
      
        forall i in 1 .. l_colarr.count
          insert into oqf_table_columns
            (owner, table_name, column_name, is_updated_date, column_order)
          values
            (l_schema_name,
             l_table_name,
             l_colarr(i),
             case when p_updated_column is null then 0 when p_updated_column = l_colarr(i) then 1 else 0 end,
             rownum);
      end if;
    exception
      when dup_val_on_index then
        /* Table already present */
        null;
    end populate_working_tables;
  
    /***  Register Event Hub Queue + initial load ***/
  
    if p_initial_data_push then
      <<data_push>>
      declare
        l_cur    sys_refcursor;
        l_sql    varchar2(32767 char);
        l_rowids sys.chnf$_rdesc_array;
      begin
        l_sql := 'select sys.chnf$_rdesc(-1, rowid) as rid from ' || l_schema_name || '.' || l_table_name;
        open l_cur for l_sql;
        fetch l_cur bulk collect
          into l_rowids;
        close l_cur;
      
        enqueue_rowids(p_rowids => l_rowids, p_regid => -1, p_table => l_ctab);
      end data_push;
    end if;
  
    change_registration(p_owner => l_Schema_name, p_table => l_table_name);
    commit;
  end register_table;

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
      begin
        select *
          into l_tabconf
          from oqf_tables t
         where t.owner = l_owner
           and t.table_name = l_table;
      exception
        when no_data_found then
          select r.regid
            into l_tabconf.regid
            from user_change_notification_regs r
           where replace(r.table_name, '"', null) = l_owner || '.' || l_table;
      end change_registration;
    
      if l_tabconf.regid is null then
        /* Record exists in oqf_TABLES but regid is null */
        select r.regid into l_tabconf.regid from user_change_notification_regs r where r.table_name = l_owner || '.' || l_table;
      end if;
    
      sys. dbms_change_notification.deregister(regid => l_tabconf.regid);
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
    l_tab      oqf_tables%rowtype;
    l_schema   json_object_t := json_object_t();
    l_required json_array_t := json_array_t();
    l_obj      json_object_t := json_object_t();
    l_string   json_object_t := json_object_t();
    l_number   json_object_t := json_object_t();
    l_uri      varchar2(2000 char);
  begin
    <<table_setup>>
    begin
      select * into l_tab from oqf_tables where owner || '.' || table_name = p_table;
    exception
      when no_data_found then
        raise_application_error(-20404, 'Table ' || p_table || ' is not defined in oqf_TABLES');
    end table_setup;
  
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
