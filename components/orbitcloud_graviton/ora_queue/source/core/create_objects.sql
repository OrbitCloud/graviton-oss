create table oqf_azure_service_uris (
  id      number default on null to_number(sys_guid(),'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX') primary key,
  service varchar2(80 char) not null,
  action  varchar2(80 char) not null,
  method  varchar2(10 char) not null,
  uri     varchar2(400 char) not null,
  headers blob,
  constraint chk_oqfazrservur_head check (headers is json)
);

insert into oqf_azure_service_uris
  (service, action, method, uri, headers)
values
  ('Microsoft.EventHub',
   'Send event',
   'POST',
   'https://{servicebusNamespace}.servicebus.windows.net/{eventHubPath}/messages',
   '{"Content-Type":"application/vnd.microsoft.servicebus.json"}');

insert into oqf_azure_service_uris
  (service, action, method, uri, headers)
values
  ('OAuth2',
   'Authenticate',
   'POST',
   'https://login.microsoftonline.com/{tenantId}/oauth2/v2.0/token',
   '{"grant_type":"client_credentials","client_id":"{client_id}","client_secret":"{client_secret}", "resource":"{resource}", "scope":"{scope}"}');
commit;

create table oqf_credential_types (
  name        varchar2(60 char) primary key,
  description varchar2(200 char)
);

insert into oqf_credential_types (name, description) values ('Entra','Microsoft Entra credentials');
insert into oqf_credential_types (name, description) values ('SAS','Shared Access Signature');
commit;

create table oqf_credentials (
  id              number default on null to_number(sys_guid(),'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX') primary key,
  credential_type varchar2(60 char) not null references oqf_credential_types(name),
  description     varchar2(200 char),
  client_id       varchar2(256 char) invisible not null,
  secret          varchar2(256 char) invisible not null,
  created         date default on null sysdate
);

create table oqf_entra_tokens (
  id         number default on null to_number(sys_guid(),'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX') primary key,
  credential number references oqf_credentials(id) not null,
  scope      varchar2(256 char),
  payload    blob,
  created    timestamp default on null systimestamp,
  expires    timestamp not null,
  constraint chk_entratok_payloadjson check (payload is json),
  constraint chk_entratok_uq unique (credential, scope)
);
create index idx_entratok_cred on oqf_entra_tokens(credential);

create table oqf_event_hubs (
  namespace   varchar2(128 char) primary key,
  tenant_id   varchar2(128 char),
  created     date default on null sysdate,
  max_rows    number default on null 100,
  max_size_kb number default on null 200,
  credential  number references oqf_credentials(id)
);


create table oqf_eventhub_queues (
  id         number default on null to_number(sys_guid(),'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX') primary key,
  queue_name varchar2(128 char) not null,
  namespace  varchar2(128 char) references oqf_event_hubs(namespace) not null,
  created    date default on null sysdate,
  constraint uq_evh_queues unique (namespace, queue_name),
  credential  number references oqf_credentials(id)
);

create table oqf_tables (
  owner         varchar2(128 char),
  table_name    varchar2(128 char),
  queue         number references oqf_eventhub_queues(id) not null,
  schema        varchar2(128 char) not null,
  version       varchar2(10) default on null 'v1' not null,
  regid         number,
  updcol        varchar2(128 char),
  rowkey        varchar2(400 char),
  partition_key varchar2(400 char),
  sql_filter    varchar2(2000 char),
  created       date default on null sysdate,
  updated       date,
  constraint pk_oqf_tables primary key (owner, table_name)
);

create table oqf_table_columns (
  owner           varchar2(128 char),
  table_name      varchar2(128 char),
  column_name     varchar2(128 char),
  column_order    number,
 constraint pk_oqf_table_columns primary key (owner, table_name, column_name)
);

/* Sequence for Azure Send Operation */
create sequence s_az_send_op;
