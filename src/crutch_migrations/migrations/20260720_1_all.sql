begin
  -- idempotent add: swallow FIELD_ALREADY_EXISTS (SQLSTATE 42710) if the column
  -- is already present. Databricks has no ADD COLUMN IF NOT EXISTS, so use a
  -- SQL-scripting EXIT handler (CONTINUE handlers are unsupported).
  declare exit handler for sqlstate '42710'
  begin end;
  alter table {{cat}}.{{schema}}.metrics add column metric_batch_id string;
end;
