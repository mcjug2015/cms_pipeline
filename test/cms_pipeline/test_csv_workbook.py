import logging
from unittest import mock

import pytest  # type: ignore

from src.cms_pipeline.csv_workbook import CsvSheet, CsvWorkbook

logger = logging.getLogger(__name__)


def test_iter_rows_values_only_skips_rows_before_min_row(tmp_path):
    # min_row is 1-based and counts the header, so min_row=2 drops it and yields the
    # remaining rows as plain tuples of strings.
    csv_path = tmp_path / "claims.csv"
    csv_path.write_text("code,label\n001,alpha\n002,beta\n", encoding="utf-8")
    sheet = CsvSheet(str(csv_path), "claims")

    rows = list(sheet.iter_rows(min_row=2, values_only=True))

    assert rows == [("001", "alpha"), ("002", "beta")]


def test_iter_rows_wraps_values_in_cells_when_not_values_only(tmp_path):
    # The default call shape yields every row, each value wrapped in a CsvCell whose
    # number_format is always "General" because CSV carries no formatting.
    csv_path = tmp_path / "claims.csv"
    csv_path.write_text("code,label\n001,alpha\n", encoding="utf-8")
    sheet = CsvSheet(str(csv_path), "claims")

    rows = list(sheet.iter_rows())

    assert [tuple(cell.value for cell in row) for row in rows] == [
        ("code", "label"),
        ("001", "alpha"),
    ]
    # the values 001 and alpha have formats general as expected
    assert [data_row.number_format for data_row in rows[1:][0]] == [
        "General",
        "General",
    ]


def test_init_derives_truncated_sheet_name_from_filename():
    # The basename minus its extension becomes the only sheet name, cut to the 31
    # characters an xlsx sheet title allows; the directory and ".csv" play no part.
    workbook = CsvWorkbook("/data/extracts/a_very_long_cms_claims_extract_2024.csv")

    assert workbook.path == "/data/extracts/a_very_long_cms_claims_extract_2024.csv"
    assert workbook.sheetnames == ["a_very_long_cms_claims_extract_"]


@mock.patch("src.cms_pipeline.csv_workbook.CsvWorkbook.__init__", return_value=None)
def test_contains_is_true_for_the_single_sheet(init):
    workbook = CsvWorkbook("claims.csv")
    workbook.sheetnames = ["claims"]

    assert "claims" in workbook

    init.assert_called_once()


@mock.patch("src.cms_pipeline.csv_workbook.CsvWorkbook.__init__", return_value=None)
def test_getitem_returns_a_sheet_over_the_same_csv(init):
    workbook = CsvWorkbook("claims.csv")
    workbook.path = "/data/claims.csv"
    workbook.sheetnames = ["claims"]

    sheet = workbook["claims"]

    assert (sheet.path, sheet.title) == ("/data/claims.csv", "claims")
    init.assert_called_once()


@mock.patch("src.cms_pipeline.csv_workbook.CsvWorkbook.__init__", return_value=None)
def test_getitem_raises_for_a_sheet_name_the_csv_does_not_have(init):
    workbook = CsvWorkbook("claims.csv")
    workbook.path = "/data/claims.csv"
    workbook.sheetnames = ["claims"]

    with pytest.raises(KeyError, match="/data/claims.csv has no sheet named other"):
        workbook["other"]

    init.assert_called_once()
