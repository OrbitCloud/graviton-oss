define table_list = &1

set echo off
set verify off

prompt Updating rows that will be sent to the Event Hub Queues
declare
  l_queue  oqf_eventhub_queues.id%type;
  l_arr    apex_t_varchar2;
  l_rowkey all_cons_columns.column_name%type;
begin
  l_arr := apex_string.split(p_str => '&table_list', p_sep => ',');
  for i in 1 .. l_arr.count loop
    case l_arr(i)
      when 'FTTEST.FYRIRTAEKI' then
        select id into l_queue from oqf_eventhub_queues where queue_name = 'orbit-cqn-events-tests';
        az_change_notifications.register_table(p_table             => l_arr(i),
                                               p_queue             => l_queue,
                                               p_initial_data_push => false,
                                               p_updated_column    => 'DAGS_SIDASTBREYTT',
                                               p_rowkey            => 'KENNITALA',
                                               p_partition_key     => q'{case substr(kennitala, -1, 1)
                            when '9' then
                                '19'
                            when '8' then
                                '18'
                            else
                                '20'
                            end || substr(kennitala, 5, 2)}',
                                               p_column_list       => null);
        commit;
      when 'FTTEST.ISATSKRA' then
        select id into l_queue from oqf_eventhub_queues where queue_name = 'orbit-cqn-events-tests2';
        az_change_notifications.register_table(p_table             => l_arr(i),
                                               p_queue             => l_queue,
                                               p_initial_data_push => false,
                                               p_updated_column    => null,
                                               p_rowkey            => 'ISAT',
                                               p_partition_key     => null,
                                               p_column_list       => null);
        commit;
      else
        select id into l_queue from oqf_eventhub_queues where queue_name = 'orbit-cqn-events-tests';
        <<rowkey>>
        begin
          select listagg(cols.column_name, '||')
            into l_rowkey
            from all_constraints cons, all_cons_columns cols
           where cols.owner || '.' || cols.table_name = l_arr(i)
             and cons.constraint_type = 'P'
             and cons.constraint_name = cols.constraint_name
             and cons.owner = cols.owner
           order by cols.table_name, cols.position;
        exception
          when NO_DATA_FOUND then
            /* Missing Primary key */
            select cols.column_name
              into l_rowkey
              from all_constraints cons, all_cons_columns cols
             where cols.owner || '.' || cols.table_name = l_arr(i)
               and cons.constraint_type = 'P'
               and cons.constraint_name = cols.constraint_name
               and cons.owner = cols.owner
               and cols.position = 1;
        end rowkey;
        az_change_notifications.register_table(p_table             => l_arr(i),
                                               p_queue             => l_queue,
                                               p_initial_data_push => false,
                                               p_updated_column    => null,
                                               p_rowkey            => l_rowkey,
                                               p_partition_key     => null,
                                               p_column_list       => null);
    end case;

  end loop;
end;

/

exit;
