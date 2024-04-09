create or replace package az_change_notifications is

  -- Author  : OLITR
  -- Created : 07.09.2023 1624:6i:26
  -- Purpose : Maintain table Change Notifications sent to Azure

  type t_clob is table of clob;

  procedure dequeue_and_send(p_queue in varchar2);
  procedure aq_callback(context in raw, reginfo in SYS.AQ$_REG_INFO, descr in SYS.AQ$_DESCRIPTOR, payload in raw, payloadl in number);

  procedure enqueue(p_queue_id in number, p_table in varchar2, p_azure_queue in varchar2, p_data in blob);

  function get_rowdata(p_owner in varchar2, p_table in varchar2, p_rowid in varchar2) return clob; -- NOSONAR: non-deterministic
  function append_row(p_table in varchar2, p_owner in varchar2, p_rowid in varchar2) return blob; -- NOSONAR: non-deterministic
  function changed_rows(p_table in varchar2, p_owner in varchar2, p_dags in date) return sys.chnf$_rdesc_array; -- NOSONAR: non-deterministic

  function get_table(p_owner in varchar2, p_table_name in varchar2) return oqf_tables%rowtype;
  function get_table(p_qualified_table_name in varchar2) return oqf_tables%rowtype;

  procedure enqueue_rowids(p_transaction_id in raw, p_rowids in sys.chnf$_rdesc_array, p_regid in number, p_table in oqf_tables%rowtype);
  procedure cqn_callback(ntfnds in SYS.chnf$_desc);

  procedure change_registration(p_owner in varchar2, p_table in varchar2);
  procedure register_table(p_table             in varchar2,
                           p_queue             in number,
                           p_schema            in varchar2,
                           p_initial_data_push in boolean default false,
                           p_updated_column    in varchar2 default null,
                           p_rowkey            in varchar2 default null,
                           p_partition_key     in varchar2 default null,
                           p_column_list       in varchar2 default null);
  procedure deregister_table(p_owner in varchar2, p_table in varchar2, p_cleanup in boolean default true);
  procedure push_all_rows(p_owner in varchar2, p_table in varchar2);

  function generate_schema(p_table in varchar2) return clob; -- NOSONAR: non-deterministic
end az_change_notifications;
/