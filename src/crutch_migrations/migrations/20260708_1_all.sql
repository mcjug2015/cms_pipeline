begin
create table if not exists {{cat}}.{{schema}}.metrics(
    id string,
    payload variant,
    last_updated TIMESTAMP
);
end;