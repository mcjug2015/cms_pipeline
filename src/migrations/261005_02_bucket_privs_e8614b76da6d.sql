-- revision_id:e8614b76da6d;
-- prev_revision_id:db357bc27b12;
{% if is_dbr %}
begin
grant READ FILES on external location `manipulator-bucket` to `users_and_sps`;
end;
{% endif %}