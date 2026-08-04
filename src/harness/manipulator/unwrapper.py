import os
import shutil
import tempfile
import zipfile
from contextlib import contextmanager

from src import custom_logging

logger = custom_logging.setup_logging().getLogger(__name__)


class Unwrapper:

    def __init__(self, inner_file_name: str):
        self.inner_file_name = inner_file_name

    @contextmanager
    def unwrap(self, local_zip_path):
        extract_root = tempfile.mkdtemp(prefix="unwrap_")
        try:
            yield self._find_target(local_zip_path, extract_root)
        finally:
            shutil.rmtree(extract_root, ignore_errors=True)

    def _find_target(self, local_zip_path: str, extract_root: str) -> str:
        # zips still to extract; nested zips get appended as they are discovered
        pending = [local_zip_path]
        seq = 0
        while pending:
            zip_path = pending.pop()
            # extract each archive into its own uniquely-named dir so entries from
            # different (possibly identically named) nested zips cannot clobber
            # each other. Prefix with a counter since basenames alone can collide.
            dest = os.path.join(
                extract_root,
                f"{seq}_{os.path.splitext(os.path.basename(zip_path))[0]}",
            )
            seq += 1
            os.makedirs(dest)
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(dest)
            for root, _dirs, files in os.walk(dest):
                for name in files:
                    full_path = os.path.join(root, name)
                    if name == self.inner_file_name:
                        logger.info(f"unwrapped {self.inner_file_name} -> {full_path}")
                        return full_path
                    if name.lower().endswith(".zip"):
                        pending.append(full_path)
        raise FileNotFoundError(
            f"{self.inner_file_name} not found within {local_zip_path}"
        )
