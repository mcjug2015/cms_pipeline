begin
MERGE INTO {{cat}}.{{schema}}.metrics t1
USING {{cat}}.{{schema}}.metrics t2 ON t1.id = t2.id and (trim(t1.metric_batch_id) == '' or t1.metric_batch_id is null)
WHEN MATCHED THEN UPDATE SET t1.metric_batch_id = concat('backfill-', date_format(t2.last_updated, 'yMd_k'));
end;
