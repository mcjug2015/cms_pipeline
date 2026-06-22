begin
create schema if not exists {{cat}}.{{schema}};
create table if not exists {{cat}}.{{schema}}.test_table(int_id bigint, stuff string);
end;