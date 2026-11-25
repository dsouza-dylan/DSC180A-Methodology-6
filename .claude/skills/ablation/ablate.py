"""Drop one feature, refit ridge and hgb, print the validation delta.

Validation only: the test split is never scored here.

Run from the repo root: python .claude/skills/ablation/ablate.py <feature>
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pandas as pd
from sklearn.base import clone
from sklearn.metrics import mean_absolute_error, r2_score

from src.config import PROCESSED, TARGET
from src.features import feature_columns
from src.train import MODELS, temporal_split


def score(model, cols, train, valid):
    m = clone(model).fit(train[cols], train[TARGET])
    pred = m.predict(valid[cols])
    return r2_score(valid[TARGET], pred), mean_absolute_error(valid[TARGET], pred)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: ablate.py <feature>")
    feature = sys.argv[1]
    if not PROCESSED.exists():
        sys.exit(f"{PROCESSED.name} not found; run `make features` first")

    df = pd.read_parquet(PROCESSED)
    cols = feature_columns(df)
    if feature not in cols:
        # A typo must fail, not report "no change".
        sys.exit(f"{feature!r} is not a model feature. Features: {', '.join(cols)}")
    without = [c for c in cols if c != feature]
    train, valid, _ = temporal_split(df)

    print(f"Ablation of {feature} (validation, {len(valid)} days; test not scored)")
    print(f"{'model':22} {'R2 with':>8} {'R2 without':>11} {'delta':>8} {'MAE with':>9} {'MAE without':>12}")
    for name, model in MODELS.items():
        r2_in, mae_in = score(model, cols, train, valid)
        if name.startswith("baseline"):
            # Baselines ignore the feature set; shown for context only.
            print(f"{name:22} {r2_in:8.4f} {'-':>11} {'-':>8} {mae_in:9.1f} {'-':>12}")
            continue
        r2_out, mae_out = score(model, without, train, valid)
        print(f"{name:22} {r2_in:8.4f} {r2_out:11.4f} {r2_in - r2_out:+8.4f} {mae_in:9.1f} {mae_out:12.1f}")
    print(f"OK ablation: {feature}")
