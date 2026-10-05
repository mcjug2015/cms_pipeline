-- revision_id:01901ae4fc14;
-- prev_revision_id:949db4199eab;
begin
  declare exit handler for sqlstate '42710'
  begin end;
  alter table {{cat}}.{{schema}}.open_cms_data_kvp add columns (
    first_col_key string
    , first_col_val string
  );
end;
