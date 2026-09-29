import re
import uuid
from unittest import mock

from src.utils import convert_to_key, download_s3_zip, make_load_id


def test_convert_to_key_applies_all_substitutions():
    result = convert_to_key(
        "Medicare Advantage medicare Total  Enrollment Original Percentage Year " "Without Count Part A/B"
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


@mock.patch("src.utils.uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678"))
@mock.patch("src.utils.get_ascending_letters_within_minute", return_value="ABCDEF")
def test_make_load_id_joins_stamp_letters_and_uuid(mock_letters, mock_uuid4):
    load_id = make_load_id()

    assert re.fullmatch(r"\d{8}_\d{4}_ABCDEF_12345678-1234-5678-1234-567812345678", load_id)
    mock_letters.assert_called_once_with()
    mock_uuid4.assert_called_once_with()
