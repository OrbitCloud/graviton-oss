create or replace package body az_event_hubs is
  e_send_error exception;
  pragma exception_init(e_send_error, -20102);
  e_auth_error exception;
  pragma exception_init(e_send_error, -20103);

  procedure log_action(p_title in varchar2, p_message in clob) is
    pragma autonomous_transaction;
  begin
    insert into oqf_log (created, text, message) values (systimestamp, p_title, p_message);
    commit;
  end log_action;

  function ts_to_epoch_sec(ts_in in timestamp) return number is
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
    for i in 1 .. l_occurs loop
      l_arr.extend;
      l_arr(l_arr.count) := regexp_substr(srcstr => p_uri, pattern => '\{(.*?)\}', position => 1, occurrence => i);
    end loop;

    if l_occurs > 0 then
      raise_application_error(-20000, 'URI still has unsubstituted variables: ' || apex_string.join(p_table => l_arr, p_sep => ', '));
    end if;

    l_arr := apex_string_util.find_links(p_string => p_uri);
    if l_arr.count <> 1 or p_uri <> l_arr(1) then
      raise_application_error(-20000, 'URI is not valid (' || p_uri || ')');
    end if;
  end assert_uri;

  function azure_request(p_service in varchar2, p_action in varchar2) return varchar2 is
    --l_retval json_object_t := json_object_t();
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

  function entraAuthenticationToken(p_token_url in varchar2,
                                    p_clientid  in varchar2,
                                    p_secret    in varchar2,
                                    p_resource  in varchar2 default null) return clob is
    l_response  clob;
    l_multipart apex_web_service.t_multipart_parts;
  begin
    apex_web_service.set_request_headers(p_name_01 => 'Content-Type', p_value_01 => 'application/x-www-form-urlencoded', p_reset => true);

    apex_web_service.append_to_multipart(p_multipart    => l_multipart,
                                         p_name         => 'grant_type',
                                         p_content_type => 'text/plain',
                                         p_body         => to_clob('client_credentials'));

    apex_web_service.append_to_multipart(p_multipart    => l_multipart,
                                         p_name         => 'client_id',
                                         p_content_type => 'text/plain',
                                         p_body         => to_clob(p_clientid));

    apex_web_service.append_to_multipart(p_multipart    => l_multipart,
                                         p_name         => 'client_secret',
                                         p_content_type => 'text/plain',
                                         p_body         => to_clob(p_secret));

    if p_resource is not null then
      apex_web_service.append_to_multipart(p_multipart    => l_multipart,
                                           p_name         => 'resource',
                                           p_content_type => 'text/plain',
                                           p_body         => to_clob(p_resource));
    end if;

    l_response := apex_web_service.make_rest_request(p_url         => p_token_url,
                                                     p_http_method => 'POST',
                                                     p_body_blob   => apex_web_service.generate_request_body(p_multipart => l_multipart));
    if apex_web_service.g_status_code not in (200, 201) then
      log_action(p_title => 'Auth error ' || apex_web_service.g_status_code || ': ' || p_token_url, p_message => l_response);
      raise e_auth_error;
    end if;
    return l_response;
  end entraAuthenticationToken;

  procedure send(p_evh_queue in number, p_payload in clob) is
    l_cred_type  oqf_credentials.credential_type%type;
    l_clientid   oqf_credentials.client_id%type;
    l_secret     oqf_credentials.secret%type;
    l_credential oqf_credentials.id%type;
    l_response   clob;
    l_send_url   varchar2(4000 char);
    l_token_url  varchar2(4000 char);
    l_jt         json_object_t;
    l_namespace  oqf_eventhub_queues.namespace%type;
    l_queue_name oqf_eventhub_queues.queue_name%type;
  begin
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

    select credential_type, client_id, secret into l_cred_type, l_clientid, l_secret from oqf_credentials c where id = l_credential;

    l_token_url := get_token_url(p_evh_queue => p_evh_queue);
    l_send_url  := get_queue_url(p_evh_queue => p_evh_queue);

    sys.dbms_output.put_line('Credentials: ' || l_cred_type);
    <<credential_type>> --
    case l_cred_type
      when 'Entra' then
        l_jt := json_object_t.parse(entraAuthenticationToken(p_token_url => l_token_url,
                                                             p_clientid  => l_clientid,
                                                             p_secret    => l_secret,
                                                             p_resource  => 'https://eventhubs.azure.net'));

        apex_web_service.clear_request_headers;

        apex_web_service.oauth_set_token(p_token   => l_jt.get_string(key => 'access_token'),
                                         p_expires => sysdate + (1 / 86400 * l_jt.get_number('expires_in')));
        apex_web_service.set_request_headers(p_name_01 => 'Content-Type', p_value_01 => 'application/vnd.microsoft.servicebus.json');
        l_response := apex_web_service.make_rest_request(p_url         => l_send_url,
                                                         p_http_method => 'POST',
                                                         p_body        => p_payload,
                                                         p_parm_name   => apex_util.string_to_table(p_string    => 'timeout:api-version',
                                                                                                    p_separator => ':'),
                                                         p_parm_value  => apex_util.string_to_table(p_string    => '60:2014-01',
                                                                                                    p_separator => ':'),
                                                         p_scheme      => 'OAUTH_CLIENT_CRED',
                                                         p_token_url   => l_token_url);
      when 'SAS' then
        apex_web_service.clear_request_headers;
        apex_web_service.g_request_headers(1).name := 'Content-Type';
        apex_web_service.g_request_headers(1).value := 'application/vnd.microsoft.servicebus.json';
        apex_web_service.g_request_headers(2).name := 'Authorization';
        apex_web_service.g_request_headers(2).value := createSharedAccessToken(p_uri => l_send_url, p_name => l_clientid, p_key => l_secret);

        l_response := apex_web_service.make_rest_request(p_url         => l_send_url,
                                                         p_http_method => 'POST',
                                                         p_body        => p_payload,
                                                         p_parm_name   => apex_util.string_to_table('timeout:api-version'),
                                                         p_parm_value  => apex_util.string_to_table('60:2014-01'));
    end case credential_type;

    if apex_web_service.g_status_code not in (200, 201) then
      <<httperror>>
      declare
        l_obj json_object_t;
      begin
        l_obj := json_object_t();
        l_obj.put(key => 'response', val => l_response);
        l_obj.put(key => 'requestBody', val => json_element_t.parse(p_payload));
        log_action(p_title => l_send_url || ' return code ' || apex_web_service.g_status_code, p_message => l_obj.to_Clob());
      end httperror;
      raise e_send_error;
    end if;
    <<success_log>>
    declare
      l_rows_sent pls_integer;
    begin
      l_rows_sent := json_array_t.parse(p_payload).get_size();

      log_action(p_title   => apex_web_service.g_status_code || ' sending ' || l_rows_sent || ' rows.',
                 p_message => 'Event Hub: ' || l_queue_name || sys.utl_tcp.crlf || 'Namespace: ' || l_namespace);
    end success_log;
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
