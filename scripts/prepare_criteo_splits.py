"""Create or validate the deterministic splits used by the analysis notebook."""

import argparse
import math
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPLITS = ("train", "validation", "test")
EXPECTED_COLUMNS = [f"f{i}" for i in range(12)] + [
    "treatment", "conversion", "visit", "exposure"
]


def summarize_splits(output: Path, expected_rows: int, chunksize: int) -> pd.DataFrame:
    """Check partition coverage, schema and row counts before reusing local data."""
    expected_parts = {f"part-{i:03d}.parquet" for i in range(math.ceil(expected_rows / chunksize))}
    counts = []
    for split in SPLITS:
        files = sorted((output / split).glob("*.parquet"))
        if {file.name for file in files} != expected_parts:
            raise ValueError(f"Incomplete or unexpected partitions in {output / split}")
        for file in files:
            if set(pq.read_schema(file).names) != set(EXPECTED_COLUMNS):
                raise ValueError(f"Unexpected schema in {file}")
            rows = pd.read_parquet(file, columns=["treatment", "conversion"])
            if not rows.isin([0, 1]).all().all():
                raise ValueError(f"Invalid treatment or conversion flags in {file}")
            counts.append(rows.assign(split=split).groupby(
                ["split", "treatment", "conversion"]
            ).size())

    totals = pd.concat(counts).groupby(level=["split", "treatment", "conversion"]).sum()
    if int(totals.sum()) != expected_rows:
        raise ValueError(f"Expected {expected_rows:,} rows, found {totals.sum():,}")
    return totals.unstack(["treatment", "conversion"], fill_value=0).reindex(SPLITS)


def prepare_splits(
    source: Path,
    output: Path,
    *,
    expected_rows: int = 13_979_592,
    chunksize: int = 500_000,
    seed: int = 42,
) -> pd.DataFrame:
    """Use 70% train, 15% validation and 15% test, preserving CSV row order.

    Existing splits are checked and reused. They must come from this source and
    seed; coverage checks alone cannot establish provenance. Use a new output
    directory when changing the source, seed or splitting method.
    """
    source, output = Path(source), Path(output)
    if not source.is_file():
        raise FileNotFoundError(f"Place the Criteo CSV at {source}; see data/README.md")
    if expected_rows <= 0 or chunksize <= 0:
        raise ValueError("expected_rows and chunksize must be positive")
    if set(pd.read_csv(source, nrows=0).columns) != set(EXPECTED_COLUMNS):
        raise ValueError("Unexpected input CSV columns")
    if output.exists():
        return summarize_splits(output, expected_rows, chunksize)

    output.parent.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    # Publish only a complete, validated set of splits. Failed runs clean up
    # their staging directory and leave existing data untouched.
    with tempfile.TemporaryDirectory(prefix=".criteo-splits-", dir=output.parent) as temporary:
        staging = Path(temporary) / "splits"
        for split in SPLITS:
            (staging / split).mkdir(parents=True)
        for part, chunk in enumerate(pd.read_csv(source, chunksize=chunksize)):
            labels = np.asarray(SPLITS)[np.searchsorted([0.70, 0.85], rng.random(len(chunk)))]
            for split in SPLITS:
                chunk.loc[labels == split].to_parquet(
                    staging / split / f"part-{part:03d}.parquet", index=False, engine="pyarrow"
                )
        summary = summarize_splits(staging, expected_rows, chunksize)
        staging.rename(output)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=PROJECT_ROOT / "data/raw/criteo-research-uplift-v2.1.csv.gz")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data/processed/criteo_splits")
    parser.add_argument("--expected-rows", type=int, default=13_979_592)
    parser.add_argument("--chunksize", type=int, default=500_000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    print(prepare_splits(args.input, args.output, expected_rows=args.expected_rows,
                         chunksize=args.chunksize, seed=args.seed).to_string())


if __name__ == "__main__":
    main()
