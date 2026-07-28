begin
create table if not exists {{cat}}.{{schema}}.open_cms_data_kvp(
    load_id string
    , zip_name string
    , unzipped_paths variant
    , unzipped_name string
    , sheet_name string
    , table_key string
    , table_value string
    , created_at TIMESTAMP
    , updated_at TIMESTAMP
);
create table if not exists {{cat}}.{{schema}}.tot_orig_me_ma_ohp_enroll(
    load_id string
    , zip_name string
    , unzipped_paths variant
    , unzipped_name string
    , sheet_name string
    , row_yr int
    , tot_enroll double
    , tot_enroll_pct_increase_prior_yr double
    , tot_orig_me_enroll double
    , tot_orig_me_enroll_pct_increase_prior_yr double
    , tot_orig_me_pct_of_tot_enroll double
    , tot_ma_ohp_enroll double
    , tot_ma_ohp_enroll_pct_increase_prior_yr double
    , tot_ma_ohp_enroll_pct_of_tot_enroll double
    , created_at TIMESTAMP
    , updated_at TIMESTAMP
);
end;
