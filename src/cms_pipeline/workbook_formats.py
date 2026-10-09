"""The one place a file format is decided, and the interface every format presents.

`loader` needs two things of a workbook: the names of its sheets, and a sheet's rows
as values it can write straight into a table. `Workbook` and `Worksheet` below are
exactly that, deliberately not a copy of openpyxl's shape. A number format is the one
thing a CSV cannot answer for, so the rounding it implies happens inside
`XlsxWorksheet` and never reaches the loader, which is what lets a CSV row be a plain
tuple of strings rather than a tuple of pretend cells.

A new format is therefore a `Workbook`/`Worksheet` pair plus an entry in
`WORKBOOK_READERS`, never a branch in a parsing function. `Unwrapper` picks the file
out of the zip off that same table, via `is_supported_workbook`, so a new format needs
no change there either.
"""

import csv
import logging
import os
import re
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

from openpyxl import load_workbook
from openpyxl.workbook.workbook import Workbook as OpenpyxlWorkbook

logger = logging.getLogger(__name__)

# Sheet titles are capped at 31 characters in xlsx, so a CSV-derived title is
# truncated the same way rather than growing past what a workbook could hold.
MAX_SHEET_TITLE_LEN = 31


class Worksheet(ABC):
    """A single sheet of a workbook."""

    @abstractmethod
    def iter_rows(self, min_row: int = 1) -> Iterator[Tuple[Any, ...]]:
        """Yield rows from `min_row` on, each one a tuple of display values."""


class Workbook(ABC):
    """A workbook of named sheets.

    `sheetnames` is a plain attribute rather than a property: both formats know their
    sheets at construction, and nothing here reorders or renames them. Membership is a
    question about that list, so there is no `__contains__` to go with it.
    """

    sheetnames: List[str]

    @abstractmethod
    def get_sheet(self, sheet_name: str) -> Worksheet:
        """The sheet by that name, or KeyError if there is none."""


class CsvSheet(Worksheet):
    """A single sheet backed by a CSV file."""

    def __init__(self, path: str, title: str) -> None:
        self.path = path
        self.title = title

    def iter_rows(self, min_row: int = 1) -> Iterator[Tuple[Any, ...]]:
        """Yield rows from `min_row` on; a CSV value is text, so it is its own display value."""
        with open(self.path, newline="", encoding="utf-8-sig") as handle:
            for row_num, row in enumerate(csv.reader(handle), start=1):
                if row_num < min_row:
                    continue
                yield tuple(row)


class CsvWorkbook(Workbook):
    """A one-sheet workbook whose only sheet is a CSV file.

    A CSV carries no table of contents, so its one sheet name is never the one
    `get_workbook_sheet_info_dict` looks for and it takes its existing no-TOC path.
    """

    def __init__(self, path: str) -> None:
        self.path = path
        title = os.path.splitext(os.path.basename(path))[0][:MAX_SHEET_TITLE_LEN]
        self.sheetnames = [title]
        logger.info(f"reading csv {path} as single sheet {title}")

    def get_sheet(self, sheet_name: str) -> Worksheet:
        if sheet_name not in self.sheetnames:
            raise KeyError(f"{self.path} has no sheet named {sheet_name}")
        return CsvSheet(self.path, sheet_name)


def get_decimal_places(number_format: Optional[str]) -> Optional[int]:
    if not number_format or number_format in ("General", "@"):
        return None
    fmt = number_format.split(";")[0]
    fmt = re.sub(r'"[^"]*"', "", fmt)
    fmt = re.sub(r"\[[^\]]*\]", "", fmt)
    match = re.search(r"\.(0+)", fmt)
    if match:
        return len(match.group(1))
    if re.search(r"[0#]", fmt):
        return 0
    return None


def get_display_value(cell: Any) -> Any:
    value = cell.value
    if isinstance(value, float):
        decimals = get_decimal_places(cell.number_format)
        if decimals is not None:
            value = round(value, decimals)
            if decimals == 0:
                value = int(value)
    return value


class XlsxWorksheet(Worksheet):
    """A single sheet of an openpyxl workbook, yielding what the sheet displays.

    The wrapped sheet is Any because openpyxl types item access on a workbook as a
    private worksheet-or-chartsheet union, which is not a name to depend on.
    """

    def __init__(self, sheet: Any) -> None:
        self.sheet = sheet

    def iter_rows(self, min_row: int = 1) -> Iterator[Tuple[Any, ...]]:
        """Yield rows from `min_row` on, each cell rounded to the decimals its format shows."""
        for row in self.sheet.iter_rows(min_row=min_row):
            yield tuple(get_display_value(cell) for cell in row)


class XlsxWorkbook(Workbook):
    """An already-opened openpyxl workbook, presented as a `Workbook`."""

    def __init__(self, workbook: OpenpyxlWorkbook) -> None:
        self.workbook = workbook
        self.sheetnames = workbook.sheetnames

    def get_sheet(self, sheet_name: str) -> Worksheet:
        # openpyxl raises KeyError for a name it does not have, which is the contract.
        return XlsxWorksheet(self.workbook[sheet_name])


WORKBOOK_READERS: Dict[str, Callable[[str], Workbook]] = {
    ".xlsx": lambda path: XlsxWorkbook(load_workbook(path, data_only=True, read_only=True)),
    ".csv": CsvWorkbook,
}


def is_supported_workbook(name: str) -> bool:
    return os.path.splitext(name)[1].lower() in WORKBOOK_READERS


def open_workbook(target_path: str) -> Workbook:
    extension = os.path.splitext(target_path)[1].lower()
    if extension not in WORKBOOK_READERS:
        raise ValueError(f"no reader for {extension} files: {target_path}")
    return WORKBOOK_READERS[extension](target_path)
