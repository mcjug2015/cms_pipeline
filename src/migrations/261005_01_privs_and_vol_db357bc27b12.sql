-- revision_id:db357bc27b12;
-- prev_revision_id:7dc8f7013abd;
{% if is_dbr %}
begin
grant ALL PRIVILEGES, MANAGE on catalog {{cat}} to `users_and_sps`;
create volume if not exists {{cat}}.{{schema}}.vol1;
end;
{% endif %}