create or replace package orb_log authid definer is
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
                       p_message    in clob default null);
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
                       p_message    in blob default null);

  procedure log_callback(context in raw, reginfo in SYS.AQ$_REG_INFO, descr in SYS.AQ$_DESCRIPTOR, payload in raw, payloadl in number);
  procedure uploadrows(p_rowids in sys.chnf$_rdesc_array);
  procedure callback(ntfnds in SYS.chnf$_desc);
  procedure register_log_cqn;
end orb_log;
/
