set serveroutput on
begin
  for i in (select id from oqf_eventhub_queues order by id) loop
    az_event_hubs.send(p_evh_queue => i.id,
                       p_payload   => '[{"Body":"Message1", "UserProperties":{"Alert":"Strong Wind"}}, {"Body":"Message2"}, {"Body":"Message3"}]');
  end loop;
end;
/

exit
