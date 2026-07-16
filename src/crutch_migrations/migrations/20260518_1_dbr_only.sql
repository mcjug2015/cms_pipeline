begin
create catalog if not exists {{cat}};
grant manage on catalog {{cat}} to `users_and_sps`;
end;