-- revision_id:7dc8f7013abd;
-- prev_revision_id:01901ae4fc14;
begin
-- One row per attempt to load a zip out of the watched s3 prefix. Doubles as
-- the idempotency key.
create table if not exists {{cat}}.{{schema}}.open_cms_load_ledger(
    zip_uri string
    , zip_name string
    , load_id string
    , status string
    , sheet_count bigint
    , row_count bigint
    , error_message string
    , created_at TIMESTAMP
    , updated_at TIMESTAMP
);
end;
