"""An openpyxl-shaped, read-only view of a CSV file.

CMS zips hold either a workbook or a CSV, and the parsing in `loader` only ever
touches a small slice of openpyxl's interface: membership and item access on the
workbook, `sheetnames`, and `iter_rows(min_row=..., values_only=...)` on a sheet.
Presenting a CSV through that same slice keeps the format check in one place -
the reader mapping in `loader` - instead of branching in every parsing function.
"""

import csv
import logging
import os
from typing import Iterator, Tuple

logger = logging.getLogger(__name__)

# Sheet titles are capped at 31 characters in xlsx, so a CSV-derived title is
# truncated the same way rather than growing past what a workbook could hold.
MAX_SHEET_TITLE_LEN = 31


class CsvCell:
    """The two attributes `loader.get_display_value` reads off a cell.

    Every CSV value is text, so the format is always "General", which makes
    `get_decimal_places` return None and leaves the value untouched.
    """

    __slots__ = ("value", "number_format")

    def __init__(self, value: str) -> None:
        self.value = value
        self.number_format = "General"


class CsvSheet:
    """A single sheet backed by a CSV file."""

    def __init__(self, path: str, title: str) -> None:
        self.path = path
        self.title = title

    def iter_rows(self, min_row: int = 1, values_only: bool = False) -> Iterator[Tuple]:
        """Yield rows from `min_row` on, as value tuples or as `CsvCell` tuples."""
        with open(self.path, newline="", encoding="utf-8-sig") as handle:
            for row_num, row in enumerate(csv.reader(handle), start=1):
                if row_num < min_row:
                    continue
                yield tuple(row) if values_only else tuple(CsvCell(v) for v in row)


class CsvWorkbook:
    """A one-sheet workbook whose only sheet is a CSV file.

    A CSV carries no table of contents, so `__contains__` is False for it and
    `get_workbook_sheet_info_dict` takes its existing no-TOC path.
    """

    def __init__(self, path: str) -> None:
        self.path = path
        title = os.path.splitext(os.path.basename(path))[0][:MAX_SHEET_TITLE_LEN]
        self.sheetnames = [title]
        logger.info(f"reading csv {path} as single sheet {title}")

    def __contains__(self, sheet_name: str) -> bool:
        return sheet_name in self.sheetnames

    def __getitem__(self, sheet_name: str) -> CsvSheet:
        if sheet_name not in self.sheetnames:
            raise KeyError(f"{self.path} has no sheet named {sheet_name}")
        return CsvSheet(self.path, sheet_name)
