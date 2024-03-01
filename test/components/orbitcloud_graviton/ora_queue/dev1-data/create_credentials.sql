set echo off
set verify off

declare
  l_sas_creds oqf_credentials.id%type;
  l_client_creds oqf_credentials.id%type;
begin
  insert into oqf_credentials
    (credential_type, client_id, secret)
  values
    ('SAS', 'orbit-cqn-send', '&&1')
  returning id into l_sas_creds;

    insert into oqf_credentials
    (credential_type, client_id, secret)
  values
    ('Entra', '&&2', '&&3')
    returning id into l_client_creds;

  insert into oqf_event_hubs
    (namespace, tenant_id, credential)
  values
    ('ingest-orbit-message', '&&4', l_sas_creds);

  insert into oqf_eventhub_queues (queue_name, namespace) values ('orbit-cqn-events-tests', 'ingest-orbit-message');
  insert into oqf_eventhub_queues (queue_name, namespace, credential) values ('orbit-cqn-events-tests2', 'ingest-orbit-message', l_client_creds);

  commit;
end;
/
exit
