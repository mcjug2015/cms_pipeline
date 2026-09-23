import logging
import os
from typing import Any, Callable, Dict

from openpyxl import load_workbook

from src.cms_pipeline.csv_workbook import CsvWorkbook

logger = logging.getLogger(__name__)


# The one place the file format is decided. Everything downstream works against
# the openpyxl workbook interface, which CsvWorkbook also presents, so a new
# format is an entry here rather than a branch in the parsing functions.
# Unwrapper picks the file out of the zip off this same table, via
# is_supported_workbook, so a new format needs no change there either.
WORKBOOK_READERS: Dict[str, Callable[[str], Any]] = {
    ".xlsx": lambda path: load_workbook(path, data_only=True, read_only=True),
    ".csv": CsvWorkbook,
}


def is_supported_workbook(name: str) -> bool:
    return os.path.splitext(name)[1].lower() in WORKBOOK_READERS


def open_workbook(target_path: str) -> Any:
    extension = os.path.splitext(target_path)[1].lower()
    if extension not in WORKBOOK_READERS:
        raise ValueError(f"no reader for {extension} files: {target_path}")
    return WORKBOOK_READERS[extension](target_path)
