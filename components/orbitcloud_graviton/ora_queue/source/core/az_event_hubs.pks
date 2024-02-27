create or replace package az_event_hubs is

  -- Author  : OLITR
  -- Created : 2023-10-20 1624:53i:36
  -- Purpose : Manage Azure Event Hub Queues

  function ts_to_epoch_sec(ts_in in timestamp) return number;

  function createSharedAccessToken(p_uri in varchar2, p_name in varchar2, p_key in varchar2, p_expire in number default 180) return varchar2;
  function entraAuthenticationToken(p_token_url in varchar2,
                                    p_clientid  in varchar2,
                                    p_secret    in varchar2,
                                    p_resource  in varchar2 default null) return clob;
  
  procedure assert_uri(p_uri in varchar2);
  function get_queue_url(p_evh_queue in number) return varchar2;
  function get_token_url(p_evh_queue in number) return varchar2;

  procedure send(p_evh_queue in number, p_payload in clob);

end az_event_hubs;
/
