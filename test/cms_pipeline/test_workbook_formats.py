import logging
from unittest import mock

import pytest  # type: ignore

from src.cms_pipeline.workbook_formats import is_supported_workbook, open_workbook

logger = logging.getLogger(__name__)


def test_is_supported_workbook_matches_a_registered_extension_regardless_of_case():
    # Unwrapper feeds this bare zip entry names, which carry whatever case the
    # archive happened to use, so the match may not be case sensitive.
    assert is_supported_workbook("MDCR ENROLL AB 15-20_CPS_02ENR_2023.XLSX")


@mock.patch.dict(
    "src.cms_pipeline.workbook_formats.WORKBOOK_READERS",
    {".fake": lambda path: f"opened {path}"},
    clear=True,
)
def test_open_workbook_dispatches_to_the_reader_for_the_extension():
    result = open_workbook("/tmp/some_dir/thing.FAKE")

    assert result == "opened /tmp/some_dir/thing.FAKE"


@mock.patch.dict(
    "src.cms_pipeline.workbook_formats.WORKBOOK_READERS",
    {".fake": lambda path: f"opened {path}"},
    clear=True,
)
def test_open_workbook_raises_for_an_unregistered_extension():
    with pytest.raises(ValueError, match=r"no reader for \.nope files: /tmp/thing.nope"):
        open_workbook("/tmp/thing.nope")
