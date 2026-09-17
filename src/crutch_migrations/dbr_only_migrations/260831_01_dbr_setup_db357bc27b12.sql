-- revision_id:db357bc27b12;
-- prev_revision_id:;
begin
grant ALL PRIVILEGES, MANAGE on catalog {{cat}} to `users_and_sps`;
create volume if not exists {{cat}}.{{schema}}.vol1;
end;