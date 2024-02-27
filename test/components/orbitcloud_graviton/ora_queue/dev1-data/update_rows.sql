set echo off
set verify off

declare
  l_rows          apex_t_varchar2;
  l_rows_2_update pls_integer := 10;
  l_times         pls_integer := 3;
begin
  for x in 1 .. l_times loop
    select rowid bulk collect into l_rows from fttest.fyrirtaeki order by dbms_random.value fetch next l_rows_2_update rows only;
    forall i in 1 .. l_rows.count
      update fttest.fyrirtaeki i set i.fulltheiti = i.fulltheiti where rowid = l_rows(i);
    commit;
  end loop;

  for x in 1 .. l_times loop
    select rowid bulk collect into l_rows from fttest.isatskra order by dbms_random.value fetch next l_rows_2_update rows only;
    forall i in 1 .. l_rows.count
      update fttest.isatskra i set i.ATVGRHEITI = i.ATVGRHEITI where rowid = l_rows(i);
    commit;
  end loop;
end;
/

exit;
