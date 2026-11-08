"""Small synthetic checks for split creation, reuse and failure handling."""

import tempfile
import unittest
from pathlib import Path
from runpy import run_path

import numpy as np
import pandas as pd

prepare_splits = run_path(str(Path(__file__).resolve().parents[1] / "scripts/prepare_criteo_splits.py"))["prepare_splits"]


class PrepareCriteoSplitsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.source = self.directory / "input.csv.gz"
        rng = np.random.default_rng(7)
        self.rows = pd.DataFrame({f"f{i}": np.arange(1000) + i for i in range(12)})
        for column in ["treatment", "conversion", "visit", "exposure"]:
            self.rows[column] = rng.integers(0, 2, len(self.rows))
        self.rows.to_csv(self.source, index=False)

    def prepare(self, name="splits", expected_rows=1000):
        return prepare_splits(self.source, self.directory / name,
                              expected_rows=expected_rows, chunksize=250)

    def test_partition_membership_is_disjoint_complete_and_deterministic(self):
        first = self.prepare("first")
        second = self.prepare("second")
        pd.testing.assert_frame_equal(first, second)
        frames = []
        for split in ["train", "validation", "test"]:
            left = pd.read_parquet(self.directory / "first" / split)
            right = pd.read_parquet(self.directory / "second" / split)
            pd.testing.assert_frame_equal(left, right)
            self.assertGreater(len(left), 0)
            frames.append(left)
        combined = pd.concat(frames).sort_values("f0").reset_index(drop=True)
        pd.testing.assert_frame_equal(combined, self.rows)

    def test_reuse_preserves_files(self):
        first = self.prepare()
        files = list((self.directory / "splits").rglob("*.parquet"))
        before = {file: file.stat().st_mtime_ns for file in files}
        pd.testing.assert_frame_equal(first, self.prepare())
        self.assertEqual(before, {file: file.stat().st_mtime_ns for file in files})

    def test_incomplete_cache_is_rejected(self):
        self.prepare()
        (self.directory / "splits/train/part-000.parquet").unlink()
        with self.assertRaisesRegex(ValueError, "partitions"):
            self.prepare()

    def test_failed_build_does_not_publish_partial_splits(self):
        with self.assertRaisesRegex(ValueError, "Expected"):
            self.prepare(expected_rows=999)
        self.assertFalse((self.directory / "splits").exists())
        self.assertEqual(list(self.directory.glob(".criteo-splits-*")), [])

    def test_missing_source_explains_where_to_find_instructions(self):
        with self.assertRaisesRegex(FileNotFoundError, "data/README.md"):
            prepare_splits(self.directory / "missing.csv.gz", self.directory / "splits")


if __name__ == "__main__":
    unittest.main()
