begin
create catalog if not exists {{cat}};
grant manage, use catalog, use schema, select on catalog {{cat}} to `users_and_sps`;
end;