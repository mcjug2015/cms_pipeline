-- revision_id:e5ce0039b32b;
-- prev_revision_id:;
begin
{% if is_dbr %}
-- a catalog is a unity catalog object: local spark has spark_catalog and no way to
-- make another, so this statement renders to nothing off databricks.
create catalog if not exists {{cat}};
{% endif %}
create schema if not exists {{cat}}.{{schema}};
create table if not exists {{cat}}.{{schema}}.test_table(int_id bigint, stuff string);
end;