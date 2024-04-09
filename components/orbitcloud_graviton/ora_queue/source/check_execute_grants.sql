declare
  type table_arr is table of varchar2(32767 char);
  l_execute_privs table_arr := table_arr(&1);
  l_user_privs    table_arr;
  l_diff          table_arr;
  function string_join(t in table_arr, sep in varchar2) return varchar2 deterministic is
    l_return varchar2(32767 char);
  begin
    <<string_join_loop>>
    for i in 1 .. t.count loop
      l_return := l_return || t(i) || sep;
    end loop string_join_loop;
    return l_return;
  end string_join;
begin
  select p.table_name
    bulk collect
    into l_user_privs
    from user_tab_privs p
   where p.owner = 'SYS'
     and p.privilege = 'EXECUTE'
     and p.type = 'PACKAGE';
  l_diff := l_execute_privs multiset except l_user_privs;
  if l_diff.count > 0 then
    raise_application_error(-20000,
                            'The following EXECUTE grants are missing for user "' || SYS_CONTEXT('userenv', 'current_schema') || '" :' ||
                            sys.utl_tcp.crlf || string_join(l_diff, sys.utl_tcp.crlf) || sys.utl_tcp.crlf);
  end if;
end;
/
