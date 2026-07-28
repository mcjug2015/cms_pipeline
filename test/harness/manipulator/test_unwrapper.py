import os
from unittest import mock

import pytest  # type: ignore

from src.harness.manipulator.unwrapper import TotOrigMeMaOhpEnrollUnwrapper, Unwrapper

RES_DIR = os.path.join(os.path.dirname(__file__), "res")


@mock.patch("src.harness.manipulator.unwrapper.Unwrapper._find_target")
def test_unwrap_yields_target_and_cleans_up_when_body_raises(find_target):
    """
    invoke unwrap with mocked _find_target. make sure temp dir is created and passed to it. explode in the context
    , make sure _find_target is called and tmp dir is cleaned up.
    """
    find_target.return_value = "/extracted/TARGET.xlsx"

    with pytest.raises(RuntimeError, match="boom"):
        with Unwrapper("outer.zip", "TARGET.xlsx").unwrap() as path:
            assert path == "/extracted/TARGET.xlsx"
            extract_root = find_target.call_args.args[0]
            assert os.path.isdir(extract_root)
            raise RuntimeError("boom")

    find_target.assert_called_once_with(extract_root)
    assert not os.path.exists(extract_root)


def test_find_target_recurses_into_nested_zip_and_subdirs(tmp_path):
    # nested.zip holds wrap/inner.zip, which holds deep/sub/TARGET.xlsx; matching is by
    # bare filename, so neither the nesting nor the enclosing subdirs may matter.
    unwrapper = Unwrapper(os.path.join(RES_DIR, "nested.zip"), "TARGET.xlsx")

    found = unwrapper._find_target(str(tmp_path))

    assert os.path.basename(found) == "TARGET.xlsx"
    with open(found, "rb") as fh:
        assert fh.read() == b"payload-nested"


def test_find_target_raises_when_no_entry_matches(tmp_path):
    # no_target.zip holds a single readme.txt: neither the target nor a nested zip.
    unwrapper = Unwrapper(os.path.join(RES_DIR, "no_target.zip"), "TARGET.xlsx")

    with pytest.raises(FileNotFoundError, match="TARGET.xlsx not found within"):
        unwrapper._find_target(str(tmp_path))


def test_tot_orig_unwrapper_hardcodes_inner_file_name():
    unwrapper = TotOrigMeMaOhpEnrollUnwrapper("/data/cms_enroll.zip")
    assert unwrapper.inner_file_name == "MDCR ENROLL AB 1-8_CPS_02ENR_2023.xlsx"
