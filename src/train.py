"""Stage 3: temporal split, fit, evaluate, write metrics.

Two baselines and two models, on purpose.

  baseline_mean         predict the 2011 average for every day
  baseline_persistence  predict yesterday's count (cnt_lag_1)
  ridge                 standardised linear model on the audited features
  hgb                   gradient-boosted trees on the same features

The mean baseline shows what "the distribution moved" costs. Persistence
is the baseline that actually matters: ridge's features are dominated by
lagged demand, so if it cannot beat "yesterday again" it has learned
nothing worth reporting. The booster is there because it fails, and the
reason it fails is the headline result.

Run: python -m src.train
     python -m src.train --diff-roll7   (Exercise 4; prints, never writes)
"""
import json
import sys

import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin, clone
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.config import METRICS, PROCESSED, TARGET, TRAIN_END, VALID_END
from src.features import feature_columns


class PersistenceBaseline(BaseEstimator, RegressorMixin):
    """Predict a single lagged column unchanged. Nothing is fit."""

    def __init__(self, column: str = "cnt_lag_1"):
        self.column = column

    def fit(self, X, y=None):
        if self.column not in X.columns:
            raise ValueError(f"persistence baseline needs column {self.column!r}")
        return self

    def predict(self, X):
        return X[self.column].to_numpy(dtype=float)


class RelativeToRoll7(BaseEstimator, RegressorMixin):
    """Fit `model` on cnt - cnt_roll_7 and add cnt_roll_7 back at predict time.

    Trees cannot predict outside the range of their training targets, and
    2012 ridership sits above all of 2011. Relative to last week's mean the
    growth cancels, so the target the tree sees stays in range. cnt_roll_7
    is the mean of the 7 days before d, already a feature, so this adds no
    information that is not known at prediction time.
    """

    def __init__(self, model, column: str = "cnt_roll_7"):
        self.model = model
        self.column = column

    def fit(self, X, y):
        self.model_ = clone(self.model).fit(X, y - X[self.column])
        return self

    def predict(self, X):
        return self.model_.predict(X) + X[self.column].to_numpy(dtype=float)


MODELS = {
    "baseline_mean": DummyRegressor(strategy="mean"),
    "baseline_persistence": PersistenceBaseline("cnt_lag_1"),
    "ridge": make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
    "hgb": HistGradientBoostingRegressor(random_state=0, max_iter=300),
}


def temporal_split(df: pd.DataFrame):
    """Split by date, never at random. A random split on a time series
    puts tomorrow in train and today in test."""
    train = df[df.dteday <= TRAIN_END]
    valid = df[(df.dteday > TRAIN_END) & (df.dteday <= VALID_END)]
    test = df[df.dteday > VALID_END]
    return train, valid, test


def fit_and_score(diff_roll7: bool = False) -> dict:
    """Score every model. With diff_roll7, ridge and hgb are wrapped in
    RelativeToRoll7; the two baselines are left as they are."""
    models = dict(MODELS)
    if diff_roll7:
        for name in ("ridge", "hgb"):
            models[name] = RelativeToRoll7(MODELS[name])
    df = pd.read_parquet(PROCESSED)
    cols = feature_columns(df)
    train, valid, test = temporal_split(df)

    results = {
        "n_features": len(cols),
        "features": cols,
        "n_train": len(train),
        "n_valid": len(valid),
        "n_test": len(test),
    }
    for name, model in models.items():
        model.fit(train[cols], train[TARGET])
        results[name] = {
            split: {
                "r2": round(float(r2_score(part[TARGET], model.predict(part[cols]))), 4),
                "mae": round(float(mean_absolute_error(part[TARGET], model.predict(part[cols]))), 1),
            }
            for split, part in [("valid", valid), ("test", test)]
        }
    return results


if __name__ == "__main__":
    diff_roll7 = "--diff-roll7" in sys.argv
    res = fit_and_score(diff_roll7=diff_roll7)
    if not diff_roll7:
        # reports/metrics.json is always the untransformed pipeline.
        METRICS.parent.mkdir(parents=True, exist_ok=True)
        METRICS.write_text(json.dumps(res, indent=2))
    print(json.dumps({k: v for k, v in res.items() if k != "features"}, indent=2))
