from src.utils import convert_to_key, download_s3_zip


def test_convert_to_key_applies_all_substitutions():
    result = convert_to_key(
        "Medicare Advantage medicare Total  Enrollment Original Percentage Year "
        "Without Count Part A/B"
    )
    assert result == "ma_me_tot_enroll_orig_pct_yr_wo_ct_part_a_b"


def test_download_s3_zip_writes_file_content(tmp_path, test_spark):
    src_file = tmp_path / "src" / "payload.zip"
    src_file.parent.mkdir()
    src_file.write_bytes(b"dummy zip payload")
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()

    dest_path = download_s3_zip(test_spark, str(src_file), str(dest_dir))

    assert dest_path == str(dest_dir / "payload.zip")
    with open(dest_path, "rb") as fh:
        assert fh.read() == b"dummy zip payload"
