"""Shared test helpers."""

import contextlib
import os
import tempfile

from nimlab import store


@contextlib.contextmanager
def fresh_store():
    """A brand-new, empty data folder for the duration of the block.
    Yields the project-root folder (the data folder's parent), where
    pre-3.1 files can be placed to test the migration."""
    old = os.environ.get("NIMLAB_DATA_DIR")
    with tempfile.TemporaryDirectory() as root:
        os.environ["NIMLAB_DATA_DIR"] = os.path.join(root, "data")
        store.reset()
        try:
            yield root
        finally:
            if old is None:
                os.environ.pop("NIMLAB_DATA_DIR", None)
            else:
                os.environ["NIMLAB_DATA_DIR"] = old
            store.reset()
