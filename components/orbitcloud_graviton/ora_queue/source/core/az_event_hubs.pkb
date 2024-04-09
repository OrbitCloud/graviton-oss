create or replace package body az_event_hubs is

/*
  Enable Debug Mode:
  alter package az_event_hubs compile plsql_ccflags='debug_mode:true' reuse settings;
  Turn off is 'debug_mode:false'
  
     
  Changes in debug mode:
    * JSON Body saved into the log table on sending to Azure Event Hub
*/

  e_send_error exception;
  pragma exception_init(e_send_error, -20102);
  e_auth_error exception;
  pragma exception_init(e_send_error, -20103);

  function ts_to_epoch_sec(ts_in in timestamp) return number deterministic is
    ret_seconds pls_integer;
  begin
    ret_seconds := round((extract(day from(systimestamp - timestamp '1970-01-01 00:00:00 UTC') * 24 * 60) * 60 + extract(second from ts_in)),
                         0);
    return ret_seconds;
  end ts_to_epoch_sec;

  procedure pretty_print_xml(p_clob in clob) is
  begin
    <<pretty>>
    for i in (select xmlserialize(content xmltype(p_clob) as clob indent size = 3) as x from dual) loop
      sys.dbms_output.put_line(i.x);
    end loop pretty;
  end pretty_print_xml;

  procedure assert_uri(p_uri in varchar2) is
    l_arr    apex_t_varchar2;
    l_occurs pls_integer;
  begin
    l_occurs := regexp_count(srcstr => p_uri, pattern => '{');
    l_arr    := apex_t_varchar2();
  
    /* Find all the variables in the URI */
    <<find_vars>>
    for i in 1 .. l_occurs loop
      l_arr.extend;
      l_arr(l_arr.count) := regexp_substr(srcstr => p_uri, pattern => '\{(.*?)\}', position => 1, occurrence => i);
    end loop find_vars;
  
    if l_occurs > 0 then
      raise_application_error(-20000, 'URI still has unsubstituted variables: ' || apex_string.join(p_table => l_arr, p_sep => ', '));
    end if;
  
    l_arr := apex_string_util.find_links(p_string => p_uri);
    if l_arr.count <> 1 or p_uri <> l_arr(1) then
      raise_application_error(-20000, 'URI is not valid (' || p_uri || ')');
    end if;
  end assert_uri;

  function azure_request(p_service in varchar2, p_action in varchar2) return varchar2 is
    -- NOSONAR: non-deterministic
    l_azuri oqf_azure_service_uris%rowtype;
  begin
    <<service_uri>>
    begin
      select *
        into l_azuri
        from oqf_azure_service_uris azu
       where azu.service = p_service
         and azu.action = p_action;
    exception
      when no_data_found then
        raise_application_error(-20000, 'URIs with service: ' || p_service || ' and action: ' || p_action || ' is unknown');
      when too_many_rows then
        raise;
    end service_uri;
  
    return l_azuri.uri;
  end azure_request;

  function get_queue_url(p_evh_queue in number) return varchar2 is
    -- NOSONAR: non-deterministic
    l_evh_queue oqf_eventhub_queues%rowtype;
    l_evh       oqf_event_hubs%rowtype;
    l_uri       oqf_azure_service_uris.uri%type;
  begin
    <<queue>>
    begin
      select * into l_evh_queue from oqf_eventhub_queues q where q.id = p_evh_queue;
    exception
      when no_data_found then
        raise_application_error(-20000, 'Queue with id: ' || p_evh_queue || ' is unknown');
      when too_many_rows then
        raise;
    end queue;
  
    <<event_hub>>
    begin
      select * into l_evh from oqf_event_hubs h where h.namespace = l_evh_queue.namespace;
    exception
      when no_data_found then
        raise_application_error(-20000, 'Event Hub with namespace: ' || l_evh_queue.namespace || ' is unknown');
      when too_many_rows then
        raise;
    end event_hub;
  
    l_uri := replace(replace(azure_request(p_service => 'Microsoft.EventHub', p_action => 'Send event'),
                             '{servicebusNamespace}',
                             l_evh.namespace),
                     '{eventHubPath}',
                     l_evh_queue.queue_name);
  
    assert_uri(p_uri => l_uri);
    return l_uri;
  end get_queue_url;

  function get_token_url(p_evh_queue in number) return varchar2 is
    -- NOSONAR: non-deterministic
    l_evh oqf_event_hubs%rowtype;
    l_url oqf_azure_service_uris.uri%type;
  begin
    <<token>>
    begin
      select e.* into l_evh from oqf_event_hubs e join oqf_eventhub_queues q on e.namespace = q.namespace where q.id = p_evh_queue;
    exception
      when no_data_found then
        raise_application_error(-20000, 'Queue with id: ' || p_evh_queue || ' is unknown');
      when too_many_rows then
        raise;
    end token;
  
    l_url := azure_request(p_service => 'OAuth2', p_action => 'Authenticate');
    l_url := replace(l_url, '{tenantId}', l_evh.tenant_id);
    assert_uri(p_uri => l_url);
    return l_url;
  end get_token_url;

  function createSharedAccessToken(p_uri in varchar2, p_name in varchar2, p_key in varchar2, p_expire in number default 180) return varchar2 is
    -- NOSONAR: non-deterministic
    l_epoch         binary_integer;
    l_raw_signature raw(2000);
    l_hash          varchar2(4000 char);
  begin
    l_epoch := round((extract(day from(systimestamp - timestamp '1970-01-01 00:00:00 UTC') * 24 * 60) * 60 +
                     extract(second from systimestamp)),
                     0);
  
    l_raw_signature := sys.utl_i18n.string_to_raw(data => p_uri || chr(10) || to_char(l_epoch + p_expire), dst_charset => 'UTF8');
  
    l_hash := sys.utl_raw.cast_to_varchar2(sys.utl_encode.base64_encode(sys.dbms_crypto.mac(src => l_raw_signature,
                                                                                            typ => sys.dbms_crypto.hmac_sh256,
                                                                                            key => sys.utl_raw.cast_to_raw(p_key))));
  
    return 'SharedAccessSignature sr=' || p_uri --
    || '&sig=' || sys.utl_url.escape(url => l_hash, escape_reserved_chars => true) --
    || '&se=' || to_char(l_epoch + p_expire) --
    || '&skn=' || p_name;
  end createSharedAccessToken;

  function entraAuthenticationToken(p_token_url  in varchar2, -- NOSONAR: non-deterministic
                                    p_credential in number,
                                    p_scope      in varchar2 default null) return blob is
    pragma autonomous_transaction;
    l_cred        oqf_credentials.description%type;
    l_clientid    oqf_credentials.client_id%type;
    l_secret      oqf_credentials.secret%type;
    l_etok        oqf_entra_tokens%rowtype;
    l_body        clob;
    l_time        binary_integer;
    l_max_retries pls_integer := 5;
  begin
    <<credential>>
    begin
      select client_id, secret, description into l_clientid, l_secret, l_cred from oqf_credentials where id = p_credential;
    exception
      when no_data_found then
        raise;
      when too_many_rows then
        raise;
    end credential;
  
    <<token>>
    begin
      select *
        into l_etok
        from oqf_entra_tokens t
       where t.credential = p_credential
         and ((p_scope is null and scope is null) or (p_scope is not null and scope = p_scope));
    exception
      when no_data_found then
        l_etok.credential := p_credential;
        l_etok.created    := systimestamp;
        l_etok.expires    := systimestamp - 1;
        l_etok.scope      := p_scope;
        insert into oqf_entra_tokens
          (credential, created, expires, scope)
        values
          (l_etok.credential, l_etok.created, l_etok.expires, l_etok.scope);
        commit;
      when too_many_rows then
        raise;
    end token;
  
    if l_etok.expires <= systimestamp then
      l_time := sys.dbms_utility.get_time;
      /* Fetch new authentication token */
    
      <<entra_token>>
      for a in 1 .. l_max_retries loop
        /* The request for entra token tries 5 (l_max_retries) times, the AQ Queue retries 3 times after waiting 5 seconds for a total of 15 times */
        apex_web_service.set_request_headers(p_name_01  => 'Content-Type',
                                             p_value_01 => 'application/x-www-form-urlencoded',
                                             p_reset    => true);
      
        l_body := 'client_id=' || l_clientid || --
                  case
                    when p_scope is not null then
                     '&scope=' || sys.utl_url.escape(url => p_scope, escape_reserved_chars => true)
                    else
                     null
                  end || --
                  '&client_secret=' || l_secret || --
                  '&grant_type=client_credentials';
      
        l_etok.payload := apex_web_service.make_rest_request_b(p_url              => p_token_url,
                                                               p_http_method      => 'POST',
                                                               p_body             => l_body,
                                                               p_transfer_timeout => 5);
        if apex_web_service.g_status_code in (200, 201) then
          exit entra_token;
        end if;
      end loop entra_token;
    
      /* If no token after 5 retries then log error and raise */
      if apex_web_service.g_status_code not in (200, 201) then
        orb_log.log_action(p_title   => 'Auth error ' || apex_web_service.g_status_code || ': ' || p_token_url,
                           p_message => to_clob(l_etok.payload));
        raise e_auth_error;
      end if;
    
      apex_web_service.clear_request_headers;
      l_etok.expires := sysdate + (1 / 86400 * json_object_t.parse(l_etok.payload).get_number('expires_in'));
    
      update oqf_entra_tokens
         set payload = l_etok.payload,
             created = systimestamp,
             expires = l_etok.expires
       where credential = l_etok.credential
         and ((p_scope is null and scope is null) or (p_scope is not null and scope = p_scope));
      commit;
    
      orb_log.log_action(p_title      => 'Entra token refreshed',
                         p_time       => (sys.dbms_utility.get_time - l_time) / 100,
                         p_table_name => l_clientid,
                         p_namespace  => l_cred,
                         p_queue      => p_scope,
                         p_message    => to_clob(l_etok.payload));
    
    end if;
  
    return l_etok.payload;
  end entraAuthenticationToken;

  procedure send(p_evh_queue in number, p_payload in blob) is
    e_no_data        exception;
    l_cred_type      oqf_credentials.credential_type%type;
    l_clientid       oqf_credentials.client_id%type;
    l_secret         oqf_credentials.secret%type;
    l_credential     oqf_credentials.id%type;
    l_response       clob;
    l_send_url       varchar2(4000 char);
    l_token_url      varchar2(4000 char);
    l_jt             json_object_t;
    l_namespace      oqf_eventhub_queues.namespace%type;
    l_queue_name     oqf_eventhub_queues.queue_name%type;
    l_obj            json_object_t;
    l_start          binary_integer;
    l_correlation_id varchar2(400 char);
  begin
    if p_payload is null then
      raise e_no_data;
    end if;
    <<get_credential>>
    begin
      select coalesce(q.credential, e.credential), e.namespace, q.queue_name
        into l_credential, l_namespace, l_queue_name
        from oqf_event_hubs e
        join oqf_eventhub_queues q
          on e.namespace = q.namespace
       where q.id = p_evh_queue;
    exception
      when no_data_found then
        raise_application_error(-20000, 'Queue number unknown');
      when too_many_rows then
        raise;
    end get_credential;
  
    <<credential>>
    begin
      select credential_type, client_id, secret into l_cred_type, l_clientid, l_secret from oqf_credentials c where id = l_credential;
    exception
      when no_data_found then
        raise_application_error(-20000, 'Credential number unknown');
      when too_many_rows then
        raise;
    end credential;
  
    l_start := sys.dbms_utility.get_time;
  
    l_token_url := get_token_url(p_evh_queue => p_evh_queue);
    l_send_url  := get_queue_url(p_evh_queue => p_evh_queue);
  
    l_correlation_id := json_value(p_payload, '$[0].UserProperties.transaction_id' returning varchar2);
  
    --sys.dbms_output.put_line('Credentials: ' || l_cred_type);
    <<credential_type>> --
    case l_cred_type
      when 'Entra' then
        l_jt := json_object_t.parse(entraAuthenticationToken(p_token_url  => l_token_url,
                                                             p_credential => l_credential,
                                                             p_scope      => 'https://eventhubs.azure.net//.default'));
      
        apex_web_service.oauth_set_token(p_token   => l_jt.get_string(key => 'access_token'),
                                         p_expires => sysdate + (1 / 86400 * l_jt.get_number('expires_in')));
      
        apex_web_service.set_request_headers(p_name_01  => 'Content-Type',
                                             p_value_01 => 'application/vnd.microsoft.servicebus.json',
                                             p_name_02  => 'X-Correlation-ID',
                                             p_value_02 => l_correlation_id);
      
        l_response := apex_web_service.make_rest_request(p_url         => l_send_url,
                                                         p_http_method => 'POST',
                                                         p_body_blob   => p_payload,
                                                         p_parm_name   => apex_util.string_to_table(p_string    => 'timeout:api-version',
                                                                                                    p_separator => ':'),
                                                         p_parm_value  => apex_util.string_to_table(p_string    => '60:2014-01',
                                                                                                    p_separator => ':'),
                                                         p_scheme      => 'OAUTH_CLIENT_CRED',
                                                         p_token_url   => l_token_url);
      when 'SAS' then
        apex_web_service.clear_request_headers;
        apex_web_service.set_request_headers(p_name_01  => 'Content-Type',
                                             p_value_01 => 'application/vnd.microsoft.servicebus.json',
                                             p_name_02  => 'X-Correlation-ID',
                                             p_value_02 => l_correlation_id,
                                             p_name_03  => 'Authorization',
                                             p_value_03 => createSharedAccessToken(p_uri  => l_send_url,
                                                                                   p_name => l_clientid,
                                                                                   p_key  => l_secret));
      
        l_response := apex_web_service.make_rest_request(p_url         => l_send_url,
                                                         p_http_method => 'POST',
                                                         p_body_blob   => p_payload,
                                                         p_parm_name   => apex_util.string_to_table('timeout:api-version'),
                                                         p_parm_value  => apex_util.string_to_table('60:2014-01'));
    end case credential_type;
  
    <<logger>>
    declare
      l_rows_sent pls_integer;
      l_fullname  varchar2(256 char);
      l_bytes     binary_integer;
      l_seconds   number(12, 2);
      l_title     oqf_logs.text%type;
      l_message   oqf_logs.message%type;
    begin
      l_bytes   := sys.dbms_lob.getlength(lob_loc => p_payload);
      l_seconds := (sys.dbms_utility.get_time - l_start) / 100;
    
      select json_value(p_payload, '$.size()' returning number), json_value(p_payload, '$[0].UserProperties.table')
        into l_rows_sent, l_fullname
        from dual;
    
      /*l_rows_sent := json_value(p_payload, '$.size()' returning number); -- Does not work in PLSQL
      l_fullname  := json_value(p_payload, '$[0].UserProperties.table');*/
    
      if apex_web_service.g_status_code not in (200, 201) then
        l_obj := json_object_t();
        l_obj.put(key => 'response', val => l_response);
        l_obj.put(key => 'requestBody', val => json_element_t.parse(p_payload));
        l_title   := l_send_url || ' return code ' || apex_web_service.g_status_code;
        l_message := l_obj.to_clob();
      else
        l_title := apex_web_service.g_status_code;
        $if $$debug_mode $then
        l_message := to_clob(p_payload);
        $else
        l_message := null;
        $end
      end if;
    
      orb_log.log_action(p_title      => l_title,
                         p_owner      => substr(l_fullname, 1, instr(l_fullname, '.') - 1),
                         p_table_name => substr(l_fullname, instr(l_fullname, '.') + 1, length(l_fullname)),
                         p_namespace  => l_namespace,
                         p_queue      => l_queue_name,
                         p_rows       => l_rows_sent,
                         p_time       => l_seconds,
                         p_bytes      => l_bytes,
                         p_transid    => l_correlation_id,
                         p_message    => l_message);
    
      if apex_web_service.g_status_code not in (200, 201) then
        raise e_send_error;
      end if;
    end logger;
  exception
    when e_no_data then
      orb_log.log_action(p_title => 'Send called with empty payload. Quitting..', p_message => p_payload);
  end send;

/*
    <<aq_callback>>
    begin
      select r.reg_id
        into l_regcheck
        from user_subscr_registrations r
       where r.namespace = 'AQ'
         and r.subscription_name like '%' || dbms_assert.enquote_name(Str => p_queue_name)
         and r.location_name = 'plsql://' || p_callback;
    exception
      when no_data_found then
        dbms_aq.register(reg_list  => sys.aq$_reg_info_list(sys.aq$_reg_info(name      => p_queue_name,
                                                                             namespace => dbms_aq.namespace_aq,
                                                                             callback  => 'plsql://' || p_callback,
                                                                             context   => null)),
                         reg_count => 1);
    end aq_callback;
*/

end az_event_hubs;
/