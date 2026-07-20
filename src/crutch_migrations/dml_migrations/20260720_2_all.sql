begin
MERGE INTO {{cat}}.{{schema}}.metrics t1
USING {{cat}}.{{schema}}.metrics t2 ON t1.id = t2.id
WHEN MATCHED THEN UPDATE SET t1.metric_batch_id = concat('backfill-', date_format(t2.last_updated, 'YYYYMMDD_HH'));
end;
