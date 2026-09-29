-- revision_id:e8614b76da6d;
-- prev_revision_id:db357bc27b12;
begin
-- cms_files_loader_job's file-arrival trigger watches an s3 prefix and the run
-- then lists it, so the run-as principal needs READ FILES on the external
-- location covering that url. An external location is a metastore-level
-- securable and sits outside the catalog, so the ALL PRIVILEGES granted on
-- {{cat}} in 260831_01 does not reach it -- this is a separate grant.
--
-- The location is named, not a path, and there is no placeholder for it:
-- spark_sql_migrations renders only cat and schema, so the name is literal.
-- It is metastore-wide, so every per-branch catalog shares this one location.
--
-- grant is idempotent; re-granting a privilege already held is a no-op.
grant READ FILES on external location `manipulator-bucket` to `users_and_sps`;
end;
