import argparse
import datetime
import json
import os
import sys
import tempfile
import uuid
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from openpyxl import load_workbook
from pyspark.sql import SparkSession

from src import custom_logging
from src.crutch_migrations.run_crutch_migrations import (
    get_ascending_letters_within_minute,
)
from src.harness.manipulator.unwrapper import TotOrigMeMaOhpEnrollUnwrapper
from src.spark_utils import get_spark

logger = custom_logging.setup_logging().getLogger(__name__)

SOURCE_S3_URI = (
    "s3://manipulator-bucket/program_stat_me_total_enroll/"
    "CMS Program Statistics - Medicare Total Enrollment.zip"
)

# "sheet #2" -> second worksheet in the workbook, zero-based index 1.
SHEET_INDEX = 1

# Positional mapping of a detected data row onto tot_orig_me_ma_ohp_enroll columns.
DATA_COLUMNS = [
    "row_yr",
    "tot_enroll",
    "tot_enroll_pct_increase_prior_yr",
    "tot_orig_me_enroll",
    "tot_orig_me_enroll_pct_increase_prior_yr",
    "tot_orig_me_pct_of_tot_enroll",
    "tot_ma_ohp_enroll",
    "tot_ma_ohp_enroll_pct_increase_prior_yr",
    "tot_ma_ohp_enroll_pct_of_tot_enroll",
]


def download_s3_zip(spark: SparkSession, s3_uri: str, dest_dir: str) -> str:
    parsed = urlparse(s3_uri)
    dest_path = os.path.join(dest_dir, os.path.basename(parsed.path))
    logger.info(f"downloading {s3_uri} -> {dest_path}")
    row = spark.read.format("binaryFile").load(s3_uri).select("content").first()
    assert row is not None
    with open(dest_path, "wb") as f:
        f.write(row["content"])
    return dest_path


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "").replace("%", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _as_year(value: Any) -> Optional[int]:
    as_float = _to_float(value)
    if as_float is None or not as_float.is_integer():
        return None
    as_int = int(as_float)
    return as_int if 1900 <= as_int <= 2100 else None


def parse_sheet(
    xlsx_path: str,
) -> Tuple[str, List[Dict[str, str]], List[Dict[str, Any]]]:
    """Split sheet #2 into preamble key/value rows and enrollment data rows.

    CMS report sheets open with title/subtitle/source-note text above the
    actual table, so rows are classified by shape rather than position: a row
    whose first cell is a plausible 4-digit calendar year is treated as
    enrollment data and mapped positionally onto DATA_COLUMNS, while every
    other non-blank row is kept as a generic key/value pair so none of the
    preamble or footnotes are silently dropped.
    """
    workbook = load_workbook(xlsx_path, data_only=True, read_only=True)
    worksheet = workbook.worksheets[SHEET_INDEX]

    kvp_rows: List[Dict[str, str]] = []
    data_rows: List[Dict[str, Any]] = []
    for row in worksheet.iter_rows(values_only=True):
        cells = [c for c in row if c is not None and str(c).strip() != ""]
        if not cells:
            continue
        year = _as_year(cells[0])
        if year is not None and len(cells) > 1:
            record: Dict[str, Any] = {"row_yr": year}
            for col_name, raw_value in zip(DATA_COLUMNS[1:], cells[1:]):
                record[col_name] = _to_float(raw_value)
            data_rows.append(record)
        else:
            key = str(cells[0]).strip()
            value = " | ".join(str(c).strip() for c in cells[1:])
            kvp_rows.append({"table_key": key, "table_value": value})

    return worksheet.title, kvp_rows, data_rows


def _sql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def _common_literals(
    load_id: str,
    zip_name: str,
    unzipped_paths_json: str,
    unzipped_name: str,
    sheet_name: str,
) -> List[str]:
    # Inline literals rather than :named params: pyspark's local session does
    # not bind spark.sql(..., args=...) parameters.
    return [
        _sql_literal(load_id),
        _sql_literal(zip_name),
        f"parse_json('{unzipped_paths_json}')",
        _sql_literal(unzipped_name),
        _sql_literal(sheet_name),
    ]


def insert_kvp_rows(
    spark: SparkSession,
    cat: str,
    schema: str,
    load_id: str,
    zip_name: str,
    unzipped_paths_json: str,
    unzipped_name: str,
    sheet_name: str,
    kvp_rows: List[Dict[str, str]],
) -> None:
    if not kvp_rows:
        return
    common = _common_literals(
        load_id, zip_name, unzipped_paths_json, unzipped_name, sheet_name
    )
    values = [
        "("
        + ", ".join(
            common
            + [
                _sql_literal(row["table_key"]),
                _sql_literal(row["table_value"]),
                "current_timestamp()",
                "current_timestamp()",
            ]
        )
        + ")"
        for row in kvp_rows
    ]
    spark.sql(
        f"""
        insert into {cat}.{schema}.open_cms_data_kvp
        (load_id, zip_name, unzipped_paths, unzipped_name, sheet_name, table_key, table_value, created_at, updated_at)
        values {", ".join(values)}
        """  # noqa: E501
    )


def insert_data_rows(
    spark: SparkSession,
    cat: str,
    schema: str,
    load_id: str,
    zip_name: str,
    unzipped_paths_json: str,
    unzipped_name: str,
    sheet_name: str,
    data_rows: List[Dict[str, Any]],
) -> None:
    if not data_rows:
        return
    common = _common_literals(
        load_id, zip_name, unzipped_paths_json, unzipped_name, sheet_name
    )
    values = [
        "("
        + ", ".join(
            common
            + [_sql_literal(row.get(col)) for col in DATA_COLUMNS]
            + ["current_timestamp()", "current_timestamp()"]
        )
        + ")"
        for row in data_rows
    ]
    spark.sql(
        f"""
        insert into {cat}.{schema}.tot_orig_me_ma_ohp_enroll
        (load_id, zip_name, unzipped_paths, unzipped_name, sheet_name, {", ".join(DATA_COLUMNS)}, created_at, updated_at)
        values {", ".join(values)}
        """  # noqa: E501
    )


def load(
    spark: SparkSession, cat: str, schema: str, s3_uri: str = SOURCE_S3_URI
) -> Dict[str, int]:
    with tempfile.TemporaryDirectory(prefix="cms_enroll_dl_") as tmp_dir:
        zip_path = download_s3_zip(spark, s3_uri, tmp_dir)
        unwrapper = TotOrigMeMaOhpEnrollUnwrapper(zip_path)
        with unwrapper.unwrap() as xlsx_path:
            sheet_name, kvp_rows, data_rows = parse_sheet(xlsx_path)

            load_id = f"{datetime.datetime.today().strftime('%Y%m%d_%H%M')}_{get_ascending_letters_within_minute()}_{uuid.uuid4()}"  # noqa: E501
            zip_name = os.path.basename(zip_path)
            unzipped_name = unwrapper.inner_file_name
            unzipped_paths_json = json.dumps([zip_path, xlsx_path]).replace("'", "''")

            insert_kvp_rows(
                spark,
                cat,
                schema,
                load_id,
                zip_name,
                unzipped_paths_json,
                unzipped_name,
                sheet_name,
                kvp_rows,
            )
            insert_data_rows(
                spark,
                cat,
                schema,
                load_id,
                zip_name,
                unzipped_paths_json,
                unzipped_name,
                sheet_name,
                data_rows,
            )

    logger.info(
        f"load_id:{load_id} loaded {len(kvp_rows)} kvp rows and "
        f"{len(data_rows)} enrollment rows from sheet '{sheet_name}'"
    )
    return {"kvp_rows": len(kvp_rows), "data_rows": len(data_rows)}


def main(*args, **kwargs):
    logger.info("loader main begins")
    cat = kwargs.get("cat", None)
    schema = kwargs.get("schema", None)
    if not cat or not schema:
        cat = sys.argv[1]
        schema = sys.argv[2]
    if not cat or not schema:
        raise ValueError(
            f"Expecting both cat and schema but got {args}, {kwargs}, {sys.argv};"
        )
    logger.info(f"will be using cat:{cat}; schema:{schema};")
    spark = get_spark()
    load(spark, cat, schema, SOURCE_S3_URI)
    sql_result = spark.sql("select 1")
    results = [x.asDict() for x in sql_result.toLocalIterator()]
    logger.info(f"loader main end {results}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="loader params")
    parser.add_argument(
        "--cat",
        help="catalog name to use",
        default="spark_catalog",
    )
    parser.add_argument(
        "--schema",
        help="schema name to use",
        default="default",
    )
    args = parser.parse_args()
    main(cat=args.cat, schema=args.schema)
