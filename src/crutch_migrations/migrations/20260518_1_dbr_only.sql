begin
create catalog if not exists {{cat}};
grant ALL PRIVILEGES on catalog {{cat}} to `users_and_sps`;
end;