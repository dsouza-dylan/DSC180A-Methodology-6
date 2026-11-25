"""Guard rails on the ingest contract and the trained model's behaviour."""
import pandas as pd
import pytest
from sklearn.metrics import r2_score

from src.config import (
    ENCODED_COLS,
    FORBIDDEN,
    LAG_WARMUP,
    RAW,
    RAW_FEATURE_COLS,
    RAW_SHA256,
    REDUNDANT_COLS,
    TARGET,
)
from src.features import build_features, feature_columns, reindex_to_calendar
from src.ingest import load_raw, raw_sha256
from src.train import MODELS, temporal_split


@pytest.fixture(scope="module")
def raw():
    return load_raw().sort_values("dteday").reset_index(drop=True)


@pytest.fixture(scope="module")
def feats(raw):
    return build_features(raw)


def test_raw_file_is_unchanged():
    """data/raw/ is write-denied for Edit and Write but not for Bash, and the
    PostToolUse hook never sees a `cp`. The hash is the only guard that does.
    RAW_SHA256 is a literal in src/config.py, not computed from the file, so
    this cannot pass by construction."""
    assert raw_sha256() == RAW_SHA256, "data/raw/bike_daily.csv has changed"


def test_every_raw_column_is_classified():
    """A column added to or renamed in the CSV must be classified in
    src/config.py before it can reach the model.

    "A feature" here means RAW_FEATURE_COLS or ENCODED_COLS, not
    feature_columns(): that admits any numeric column not in FORBIDDEN, so
    an appended column would count as a feature and this would pass by
    construction. Reads the header directly, not through load_raw().
    """
    raw_cols = set(pd.read_csv(RAW, nrows=0).columns)
    classified = {"dteday"} | FORBIDDEN | RAW_FEATURE_COLS | set(ENCODED_COLS) | REDUNDANT_COLS
    unclassified = raw_cols - classified
    assert not unclassified, f"unclassified raw columns: {sorted(unclassified)}"


def test_classified_features_reach_the_model(feats):
    """The classification must match the code: every raw feature, and every
    encoded column's output, is in feature_columns()."""
    expected = RAW_FEATURE_COLS | set(ENCODED_COLS.values())
    missing = expected - set(feature_columns(feats))
    assert not missing, f"classified as features but not in the model: {sorted(missing)}"


def test_calendar_is_complete_before_lagging(raw):
    """The reindexed frame must have no gaps, or the lags are wrong."""
    grid = reindex_to_calendar(raw)
    assert set(grid.dteday.diff().dropna().dt.days.unique()) == {1}


def test_only_expected_rows_are_dropped(raw, feats):
    """Rows may only vanish for the lag warm-up or downstream of a genuinely
    absent day -- never because an encoder produced a silent NaN.

    Accounting: the first LAG_WARMUP days have no complete history. Each
    absent calendar day m costs the LAG_WARMUP rows after it (cnt_lag_1 is
    NaN on m+1, cnt_roll_7 is NaN on m+1..m+7, cnt_lag_7 on m+7; their
    union is 7 rows). Day m itself was never in `raw`, so it is not a loss.
    The bound is exact for the current feature set; add a longer lag and
    LAG_WARMUP in src/config.py must grow with it.
    """
    full = pd.date_range(raw.dteday.min(), raw.dteday.max(), freq="D")
    missing_days = len(full) - len(raw)
    allowed_loss = LAG_WARMUP + LAG_WARMUP * missing_days
    lost = len(raw) - len(feats)
    assert lost <= allowed_loss, f"lost {lost} rows; expected at most {allowed_loss}"


def test_beats_the_mean_baseline(feats):
    """A model that cannot beat predicting the training mean is not a result."""
    cols = feature_columns(feats)
    train, _, test = temporal_split(feats)
    ridge = MODELS["ridge"]
    ridge.fit(train[cols], train[TARGET])
    assert r2_score(test[TARGET], ridge.predict(test[cols])) > 0.4


def test_persistence_baseline_is_reported():
    """The baseline that matters for a lag-driven model is 'yesterday again'.
    It must be in the comparison, whatever its score."""
    assert "baseline_persistence" in MODELS
