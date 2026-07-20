begin
alter table {{cat}}.{{schema}}.metrics add column metric_batch_id string;
end;
