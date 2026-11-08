# Data

## Raw input

Obtain v2.1 from the [Criteo dataset page](https://ailab.criteo.com/criteo-uplift-prediction-dataset/)
or [Criteo's dataset download](https://huggingface.co/datasets/criteo/criteo-uplift/blob/main/criteo-research-uplift-v2.1.csv.gz)
and retain its original compressed filename:

```text
data/raw/criteo-research-uplift-v2.1.csv.gz
```

The expected input has **13,979,592 rows** and these 16 columns:

| Columns | Role in this analysis |
| --- | --- |
| `f0`, `f2`, `f7`, `f10` | Continuous model inputs |
| `f1`, `f3`, `f4`, `f5`, `f6`, `f8`, `f9`, `f11` | Categorical model inputs |
| `treatment` | Campaign assignment, 0 for control and 1 for campaign |
| `conversion` | Binary conversion outcome |
| `visit` | Binary visit outcome |
| `exposure` | Binary recorded ad exposure |

The notebook audits the entire CSV for missing and infinite values, invalid
binary flags, exposed controls and conversions without visits. The feature
roles above are modeling choices; the anonymized values have no documented
business meaning within this project.

## Processed splits

Run from the repository root:

```bash
uv run --locked python scripts/prepare_criteo_splits.py
```

The script uses seed 42 to assign each row to training, validation or test with
probabilities 0.70, 0.15 and 0.15. It preserves source order within each
partition and writes `part-000.parquet`, `part-001.parquet`, and so on under:

```text
data/processed/criteo_splits/
├── train/
├── validation/
└── test/
```

The original run produced 28 partitions per split:

| Split | Rows | Control conversions | Campaign conversions |
| --- | ---: | ---: | ---: |
| Train | 9,785,506 | 2,829 | 25,621 |
| Validation | 2,096,322 | 612 | 5,469 |
| Test | 2,097,764 | 622 | 5,621 |

An existing output directory is validated and reused. Incomplete directories
raise an error. Fresh splits are built in a temporary sibling directory and
published only after validation. To change the input or seed, use a new output
directory; existing contents are never overwritten. Coverage and row-count
checks cannot verify the provenance of externally supplied partitions.

`data/processed/legacy_criteo_splits/`, if present locally, preserves the older
empty split layout. The notebook does not use it.

Raw input and processed data stay local and are ignored by Git. Download and
use the source data under its provider's terms; it is not bundled with this
repository.

## License and citation

Dataset attribution: Criteo AI Lab. The dataset is provided under
[Creative Commons Attribution-NonCommercial-ShareAlike 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).
Its terms remain separate from the MIT license covering this project's original
code. See [Criteo's dataset page and terms](https://ailab.criteo.com/criteo-uplift-prediction-dataset/).

This project computes summaries and creates random train/validation/test splits
from the source dataset. The underlying raw and processed records are not
distributed with the repository.

Criteo requests the following paper citation:

```bibtex
@inproceedings{Diemert2018,
  author = {Diemert, Eustache and Betlei, Artem and Renaudin, Christophe and Amini, Massih-Reza},
  title = {A Large Scale Benchmark for Uplift Modeling},
  booktitle = {Proceedings of the AdKDD and TargetAd Workshop, KDD, London, United Kingdom},
  publisher = {ACM},
  year = {2018}
}
```
