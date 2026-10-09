import argparse
import logging
import os
import re
import sys
import tempfile
from typing import Any, Dict, Iterable, List, Optional, Sequence
from urllib.parse import unquote, urlparse

from pyspark.sql import Row, SparkSession
from pyspark.sql.functions import col, current_timestamp, lit
from spark_sql_migrations.spark_utils import get_spark

from src.cms_pipeline.unwrapper import Unwrapper
from src.cms_pipeline.workbook_formats import Workbook, Worksheet, open_workbook
from src.logging_config import setup_logging
from src.utils import convert_to_key, download_s3_zip, list_s3_files, make_load_id

logger = logging.getLogger(__name__)

# Default only for local/ad-hoc runs; the Databricks job passes its prefix as a
# job parameter (see dab/resources/cms_files_loader_job.yml).
DEFAULT_CMS_ZIP_PREFIX = "s3://manipulator-bucket/cms_files/"
LEDGER_TABLE = "open_cms_load_ledger"
TOC_SHEET_NAME = "Table of Contents"
STATUS_LOADED = "loaded"
STATUS_FAILED = "failed"


def get_non_empty_cells(row: Iterable[Any]) -> List[str]:
    return [str(c).strip() for c in row if c is not None and str(c).strip() != ""]


def is_only_text_cell(non_empty_cells: Sequence[str]) -> bool:
    if len(non_empty_cells) == 1 and bool(re.search(r"[A-Za-z]", non_empty_cells[0])):
        return True
    return False


def get_sheet_info_dict(toc_worksheet: Worksheet) -> Dict[str, str]:
    result = {}
    for row in toc_worksheet.iter_rows():
        cells_w_values = get_non_empty_cells(row)
        if len(cells_w_values) > 1 and cells_w_values[0] != "Table Name":
            result[cells_w_values[0]] = cells_w_values[1]
    return result


def get_workbook_sheet_info_dict(workbook: Workbook) -> Dict[str, str]:
    if TOC_SHEET_NAME not in workbook.sheetnames:
        sheet_info_dict = {sheet_name: "" for sheet_name in workbook.sheetnames}
        logger.info(f"No '{TOC_SHEET_NAME}' sheet in workbook, sheet info will be blank")
    else:
        sheet_info_dict = get_sheet_info_dict(workbook.get_sheet(TOC_SHEET_NAME))
    return sheet_info_dict


def parse_sheet(
    worksheet: Worksheet,
) -> List[Dict[str, Any]]:
    data_rows: List[Dict[str, Any]] = []
    col_index_to_header_col_name = {}
    for header_row_idx, row in enumerate(worksheet.iter_rows()):
        cells = get_non_empty_cells(row)
        if cells and len(cells) > 1:
            for idx, header_cell in enumerate(cells):
                col_index_to_header_col_name[idx] = header_cell
            break

    if not col_index_to_header_col_name:
        return data_rows

    prev_only_text_cell = ""
    for idx, row in enumerate(worksheet.iter_rows(min_row=header_row_idx + 2)):
        cells = get_non_empty_cells(row)

        if len(cells) > 0 and len(cells[0]) > 0 and cells[0] != "BLANK" and is_only_text_cell(cells):
            prev_only_text_cell = cells[0]

        if len(cells) > 0 and len(cells[0]) > 0 and cells[0] != "BLANK" and not is_only_text_cell(cells):
            record = {}
            for idx, value_cell in enumerate(cells[1:]):
                record[str(col_index_to_header_col_name[idx + 1])] = {
                    "value": str(value_cell),
                    "prev_only_text_cell": prev_only_text_cell,
                    "first_col_key": col_index_to_header_col_name[0],
                    "first_col_val": cells[0],
                }
            data_rows.append(record)

    return data_rows


def insert_kvp_rows(
    spark: SparkSession,
    cat: str,
    schema: str,
    load_id: str,
    zip_name: str,
    unzipped_name: str,
    sheet_name: str,
    sheet_index: int,
    data_rows: List[Dict[str, Any]],
) -> int:
    if not data_rows:
        return 0
    rows = []
    for idx, data_row in enumerate(data_rows):
        for the_key, the_val in data_row.items():
            table_key_simple = convert_to_key(the_key)
            rows.append(
                Row(
                    load_id=load_id,
                    zip_name=zip_name,
                    unzipped_name=unzipped_name,
                    sheet_name=sheet_name,
                    sheet_index=sheet_index,
                    table_key=the_key,
                    table_key_simple=table_key_simple,
                    table_row_index=idx,
                    table_val=the_val["value"],
                    heading=the_val["prev_only_text_cell"],
                    first_col_key=the_val["first_col_key"],
                    first_col_val=the_val["first_col_val"],
                )
            )
    df = (
        spark.createDataFrame(rows)
        .withColumn("created_at", current_timestamp())
        .withColumn("updated_at", current_timestamp())
    )
    df.writeTo(f"{cat}.{schema}.open_cms_data_kvp").append()
    return len(rows)


def load_cms_workbook(
    spark: SparkSession,
    cat: str,
    schema: str,
    workbook: Workbook,
    zip_name: str,
    unzipped_name: str,
    load_id: str,
) -> Dict[str, int]:
    sheet_info_dict = get_workbook_sheet_info_dict(workbook)
    row_counts: Dict[str, int] = {}
    for sheet_name, _sheet_desc in sheet_info_dict.items():
        data_rows = parse_sheet(workbook.get_sheet(sheet_name))
        row_counts[sheet_name] = insert_kvp_rows(
            spark,
            cat,
            schema,
            load_id,
            zip_name,
            unzipped_name,
            sheet_name,
            list(sheet_info_dict.keys()).index(sheet_name),
            data_rows,
        )
    return row_counts


def load_zip_workbook(spark: SparkSession, cat: str, schema: str, s3_zip_uri: str, load_id: str) -> Dict[str, int]:
    with tempfile.TemporaryDirectory(prefix="cms_dl_") as tmp_dir:
        zip_path = download_s3_zip(spark, s3_zip_uri, tmp_dir)
        with Unwrapper().unwrap(zip_path) as target_path:
            zip_name = os.path.basename(zip_path)
            unzipped_name = os.path.basename(target_path)
            return load_cms_workbook(
                spark,
                cat,
                schema,
                open_workbook(target_path),
                zip_name,
                unzipped_name,
                load_id,
            )


def get_unloaded_zip_uris(spark: SparkSession, cat: str, schema: str, prefix_uri: str) -> List[str]:
    loaded_rows = spark.table(f"{cat}.{schema}.{LEDGER_TABLE}").where(col("status") == STATUS_LOADED)
    loaded = {row["zip_uri"] for row in loaded_rows.select("zip_uri").toLocalIterator()}
    listed = list_s3_files(spark, prefix_uri, "*.zip").select("path")
    available = {unquote(row["path"]) for row in listed.toLocalIterator()}
    return sorted(available - loaded)


def record_load(
    spark: SparkSession,
    cat: str,
    schema: str,
    zip_uri: str,
    load_id: str,
    status: str,
    row_counts: Dict[str, int],
    error_message: Optional[str],
) -> None:
    row = Row(
        zip_uri=zip_uri,
        zip_name=os.path.basename(urlparse(zip_uri).path),
        load_id=load_id,
        status=status,
        sheet_count=len(row_counts),
        row_count=sum(row_counts.values()),
    )
    df = (
        spark.createDataFrame([row])
        .withColumn("error_message", lit(error_message).cast("string"))
        .withColumn("created_at", current_timestamp())
        .withColumn("updated_at", current_timestamp())
    )
    df.writeTo(f"{cat}.{schema}.{LEDGER_TABLE}").append()


def load_new_zips(spark: SparkSession, cat: str, schema: str, prefix_uri: str) -> Dict[str, int]:
    row_totals: Dict[str, int] = {}
    for zip_uri in get_unloaded_zip_uris(spark, cat, schema, prefix_uri):
        load_id = make_load_id()
        try:
            row_counts = load_zip_workbook(spark, cat, schema, zip_uri, load_id)
        except Exception as exc:
            # One unreadable zip must not cost the rest of the batch; the ledger
            # row carries the error and the next trigger retries this uri.
            # TODO XXX this shouldn't get rerun forever
            logger.exception(f"load failed for {zip_uri}")
            record_load(
                spark=spark,
                cat=cat,
                schema=schema,
                zip_uri=zip_uri,
                load_id=load_id,
                status=STATUS_FAILED,
                row_counts={},
                error_message=str(exc),
            )
            continue
        record_load(
            spark=spark,
            cat=cat,
            schema=schema,
            zip_uri=zip_uri,
            load_id=load_id,
            status=STATUS_LOADED,
            row_counts=row_counts,
            error_message=None,
        )
        row_totals[zip_uri] = sum(row_counts.values())
    logger.info(f"loaded {len(row_totals)} new zips from {prefix_uri}: {row_totals}")
    return row_totals


def main_s3(spark: SparkSession, cat: str, schema: str, prefix_uri: str) -> None:  # pragma: no cover
    logger.info(f"loader main s3 begins for {prefix_uri}")
    load_new_zips(spark, cat, schema, prefix_uri)


def main_local_file(spark: SparkSession, cat: str, schema: str) -> None:  # pragma: no cover
    logger.info("loader main local file begins")
    file_name = "MDCR ENROLL AB 15-20_CPS_02ENR_2023.xlsx"
    local_path = os.path.join(os.path.dirname(__file__), "..", "..", file_name)
    load_cms_workbook(
        spark,
        cat,
        schema,
        open_workbook(local_path),
        "placeholder.zip",
        file_name,
        make_load_id(),
    )


def main(*args, **kwargs) -> None:  # pragma: no cover
    setup_logging()
    logger.info("loader main begins")
    cat = kwargs.get("cat", None)
    schema = kwargs.get("schema", None)
    prefix_uri = kwargs.get("prefix_uri", None)
    if not cat or not schema:
        cat = sys.argv[1]
        schema = sys.argv[2]
    if not prefix_uri and len(sys.argv) > 3:
        prefix_uri = sys.argv[3]
    if not cat or not schema:
        raise ValueError(f"Expecting both cat and schema but got {args}, {kwargs}, {sys.argv};")
    prefix_uri = prefix_uri or DEFAULT_CMS_ZIP_PREFIX
    logger.info(f"will be using cat:{cat}; schema:{schema}; prefix_uri:{prefix_uri};")
    spark = get_spark()
    main_s3(spark, cat, schema, prefix_uri)
    sql_result = spark.sql("select 1")
    results = [x.asDict() for x in sql_result.toLocalIterator()]
    logger.info(f"loader main end {results}")


if __name__ == "__main__":  # pragma: no cover
    parser = argparse.ArgumentParser(description="loader params")
    parser.add_argument(
        "--cat",
        help="catalog name to use",
        default="dbr_dbc_cat",
    )
    parser.add_argument(
        "--schema",
        help="schema name to use",
        default="testing_testing",
    )
    parser.add_argument(
        "--prefix-uri",
        help="s3 prefix scanned for zips that have no 'loaded' ledger row yet",
        default=DEFAULT_CMS_ZIP_PREFIX,
    )
    args = parser.parse_args()
    main(cat=args.cat, schema=args.schema, prefix_uri=args.prefix_uri)
