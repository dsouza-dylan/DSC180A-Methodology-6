# Seeded faults

## Exercise 1: feature test, red before the feature existed

`tests/test_leakage.py::test_temp_change_1_uses_yesterday_only` was written
and run before `temp_change_1` was added to `src/features.py`. It fails because
the column does not exist yet:

```
$ python -m pytest tests/test_leakage.py -q --tb=line
.....F..                                                                 [100%]
================================== FAILURES ===================================
E   KeyError: 'temp_change_1'

The above exception was the direct cause of the following exception:
E   KeyError: 'temp_change_1'
.venv\Lib\site-packages\pandas\core\indexes\base.py:3648: KeyError: 'temp_change_1'
=========================== short test summary info ===========================
FAILED tests/test_leakage.py::test_temp_change_1_uses_yesterday_only - KeyErr...
1 failed, 7 passed in 0.73s
```

<!-- Exercise 2 faults (a)-(d) go below. -->

## Exercise 2 (a): forbidden column added to `feature_columns`

### Exact change

`src/features.py`, `feature_columns()`:

```diff
-    return [c for c in numeric if c not in FORBIDDEN]
+    return [c for c in numeric if c not in FORBIDDEN] + ["registered"]
```

`registered` is in `LEAKAGE_COLS` (`casual + registered == cnt`).

### Red test output

```
$ python -m pytest tests/test_leakage.py -q --tb=line
.F......                                                                 [100%]
================================== FAILURES ===================================
E   AssertionError: forbidden columns in feature set: {'registered'}
    assert not ({'atemp', 'cnt_lag_1', 'cnt_lag_7', 'cnt_roll_7', 'dayofweek', 'hum', ...} & {'casual', 'cnt', 'cnt_2d_bfr', 'days_since_2011', 'instant', 'registered', ...})
C:\Users\dylan\Desktop\Classes\DSC180A\MA6\bikeshare-open\tests\test_leakage.py:31: AssertionError: forbidden columns in feature set: {'registered'}
=========================== short test summary info ===========================
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: fo...
1 failed, 7 passed in 0.76s
```

### Hook stderr

```
PostToolUse:Edit hook blocking error from command: "${CLAUDE_PROJECT_DIR}/.claude/hooks/check_leakage.sh": [${CLAUDE_PROJECT_DIR}/.claude/hooks/check_leakage.sh]: Leakage tests failed after editing c:/Users/dylan/Desktop/Classes/DSC180A/MA6/bikeshare-open/src/features.py:
feats =         dteday  instant  season  ...  cnt_lag_1 cnt_lag_7   cnt_roll_7
0   2011-01-10     10.0  WINTER  ...      822.0...    1787.0  1530.142857
713 2012-12-31    731.0  WINTER  ...     1796.0     920.0  1531.428571

[714 rows x 29 columns]

    def test_no_forbidden_features(feats):
        """Guards the gate, not the data: feature_columns() excludes FORBIDDEN by
        construction, so this cannot discover a *new* leaky column. What it
        catches is someone editing feature_columns() or FORBIDDEN -- which is
        exactly the fault the Step 7 hook demonstrates."""
        cols = set(feature_columns(feats))
>       assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"
E       AssertionError: forbidden columns in feature set: {'registered'}
E       assert not ({'atemp', 'cnt_lag_1', 'cnt_lag_7', 'cnt_roll_7', 'dayofweek', 'hum', ...} & {'casual', 'cnt', 'cnt_2d_bfr', 'days_since_2011', 'instant', 'registered', ...})

tests\test_leakage.py:31: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: fo...
1 failed, 7 passed in 0.90s
```

The hook did not fire on the first attempt: it matched `*src/*.py`, and
Claude Code passes Windows paths with backslashes. Fixed in `f68e8f7`
(`path="${path//\\//}"`); the output above is from after that fix.

### Turns to fix

1

## Exercise 2 (b): `.shift(1)` removed from `cnt_roll_7`

### Exact change

`src/features.py`, `build_features()`:

```diff
-    out["cnt_roll_7"] = out[TARGET].shift(1).rolling(LAG_WARMUP).mean()
+    out["cnt_roll_7"] = out[TARGET].rolling(LAG_WARMUP).mean()
```

### Red test output

```
$ python -m pytest tests/test_leakage.py -q --tb=line
....F...                                                                 [100%]
================================== FAILURES ===================================
E   assert np.float64(4389.0) == 4414.857142857143 ± 0.00441486
      
      comparison failed
      Obtained: 4389.0
      Expected: 4414.857142857143 ± 0.00441486
C:\Users\dylan\Desktop\Classes\DSC180A\MA6\bikeshare-open\tests\test_leakage.py:57: assert np.float64(4389.0) == 4414.857142857143 ± 0.00441486
=========================== short test summary info ===========================
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.fl...
1 failed, 7 passed in 0.90s
```

### Hook stderr

```
PostToolUse:Edit hook blocking error from command: "${CLAUDE_PROJECT_DIR}/.claude/hooks/check_leakage.sh": [${CLAUDE_PROJECT_DIR}/.claude/hooks/check_leakage.sh]: Leakage tests failed after editing c:/Users/dylan/Desktop/Classes/DSC180A/MA6/bikeshare-open/src/features.py:
[714 rows x 29 columns]

    def test_rolling_mean_excludes_today(feats):
        """cnt_roll_7 must be the mean of the 7 calendar days *before* today."""
        by_date = feats.set_index("dteday")[TARGET]
        date = feats.dteday.iloc[200]
        window = [date - pd.Timedelta(days=k) for k in range(1, 8)]
        if all(d in by_date.index for d in window):
            expected = sum(by_date[d] for d in window) / 7
>           assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)
E           assert np.float64(4389.0) == 4414.857142857143 ± 0.00441486
E             
E             comparison failed
E             Obtained: 4389.0
E             Expected: 4414.857142857143 ± 0.00441486

tests\test_leakage.py:57: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.fl...
1 failed, 7 passed in 0.87s
```

### Turns to fix

1

## Exercise 2 (c): `raise` removed from the weather encoder

### Exact change

`src/features.py`, `encode_weather()`:

```diff
-    known = series.dropna()
-    unknown = set(known.unique()) - set(WEATHER_ORDER)
-    if unknown:
-        raise ValueError(f"unmapped weather labels: {sorted(unknown)}")
     return series.map(WEATHER_ORDER).astype(float)
```

No existing test failed and the hook stayed silent, because the data has no
unmapped labels and no test covered `encode_weather`:

```
$ python -m pytest tests/test_leakage.py -q --tb=line
........                                                                 [100%]
8 passed in 0.61s
```

Added `tests/test_leakage.py::test_encode_weather_rejects_unknown_labels`,
then re-seeded the fault.

### Red test output

```
$ python -m pytest tests/test_leakage.py -q --tb=line
........F                                                                [100%]
================================== FAILURES ===================================
E   Failed: DID NOT RAISE ValueError
c:\Users\dylan\Desktop\Classes\DSC180A\MA6\bikeshare-open\tests\test_leakage.py:86: Failed: DID NOT RAISE ValueError
=========================== short test summary info ===========================
FAILED tests/test_leakage.py::test_encode_weather_rejects_unknown_labels - Fa...
1 failed, 8 passed in 0.72s
```

### Hook stderr

```
PostToolUse:Edit hook blocking error from command: "${CLAUDE_PROJECT_DIR}/.claude/hooks/check_leakage.sh": [${CLAUDE_PROJECT_DIR}/.claude/hooks/check_leakage.sh]: Leakage tests failed after editing c:/Users/dylan/Desktop/Classes/DSC180A/MA6/bikeshare-open/src/features.py:
........F                                                                [100%]
================================== FAILURES ===================================
_________________ test_encode_weather_rejects_unknown_labels __________________

    def test_encode_weather_rejects_unknown_labels():
        """An unmapped label must raise, not silently become NaN and get dropped."""
>       with pytest.raises(ValueError, match="unmapped weather labels"):
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE ValueError

tests\test_leakage.py:86: Failed
=========================== short test summary info ===========================
FAILED tests/test_leakage.py::test_encode_weather_rejects_unknown_labels - Fa...
1 failed, 8 passed in 0.69s
```

### Turns to fix

1

## Exercise 2 (d): `cp` into `data/raw/` from Bash

### What happened

A copy of `data/raw/bike_daily.csv` with one label changed was copied over the raw file from Bash:

```
$ diff data/raw/bike_daily.csv /tmp/fault_d/bike_daily.csv
666c666
< 668,"2012-10-29","FALL","2012","OCT","N","MON",12.68,30.9396,88,23.9994,2,20,22,"Y","BAD",667,7852
---
> 668,"2012-10-29","FALL","2012","OCT","N","MON",12.68,30.9396,88,23.9994,2,20,22,"Y","STORMY",667,7852
$ cp /tmp/fault_d/bike_daily.csv data/raw/bike_daily.csv
```

No hook ran. The hook is registered for `Edit|Write` only, and the `deny` rules for `data/raw/**` also cover only `Edit` and `Write`, not Bash.

```
$ git status
On branch main
Your branch is ahead of 'origin/main' by 6 commits.
  (use "git push" to publish your local commits)

Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git restore <file>..." to discard changes in working directory)
        modified:   data/raw/bike_daily.csv

no changes added to commit (use "git add" and/or "git commit -a")
```

`make test` failed (13 identical setup errors; one shown in full, the rest
cut):

```
$ make test
python -m pytest tests/ -q
.EE.EEEEEEEE.EEE                                                                             [100%]
============================================= ERRORS ==============================================
______________________ ERROR at setup of test_only_expected_rows_are_dropped ______________________
[...]
        known = series.dropna()
        unknown = set(known.unique()) - set(WEATHER_ORDER)
        if unknown:
>           raise ValueError(f"unmapped weather labels: {sorted(unknown)}")
E           ValueError: unmapped weather labels: ['STORMY']

src\features.py:30: ValueError
[...]
===================================== short test summary info =====================================
ERROR tests/test_contract.py::test_only_expected_rows_are_dropped - ValueError: unmapped weather labels: ['STORMY']
ERROR tests/test_contract.py::test_beats_the_mean_baseline - ValueError: unmapped weather labels: ['STORMY']
ERROR tests/test_leakage.py::test_leakage_identity_holds - ValueError: unmapped weather labels: ['STORMY']
ERROR tests/test_leakage.py::test_no_forbidden_features - ValueError: unmapped weather labels: ['STORMY']
ERROR tests/test_leakage.py::test_lags_are_true_calendar_lags - ValueError: unmapped weather labels: ['STORMY']
ERROR tests/test_leakage.py::test_lag_is_not_the_target - ValueError: unmapped weather labels: ['STORMY']
ERROR tests/test_leakage.py::test_rolling_mean_excludes_today - ValueError: unmapped weather labels: ['STORMY']
ERROR tests/test_leakage.py::test_temp_change_1_uses_yesterday_only - ValueError: unmapped weather labels: ['STORMY']
ERROR tests/test_leakage.py::test_no_missing_values - ValueError: unmapped weather labels: ['STORMY']
ERROR tests/test_leakage.py::test_dates_are_sorted_and_unique - ValueError: unmapped weather labels: ['STORMY']
ERROR tests/test_split.py::test_splits_non_empty - ValueError: unmapped weather labels: ['STORMY']
ERROR tests/test_split.py::test_splits_are_ordered_in_time - ValueError: unmapped weather labels: ['STORMY']
ERROR tests/test_split.py::test_no_overlapping_dates - ValueError: unmapped weather labels: ['STORMY']
3 passed, 13 errors in 2.37s
make: *** [Makefile:16: test] Error 1
```

Restored with `git checkout -- data/raw/bike_daily.csv`; `make test` then gave `16 passed`.

### What would have caught it

`make test` caught it because `STORMY` reaches the `raise` in
`encode_weather`. With one `temp` value edited instead, nothing fails:

```
$ diff data/raw/bike_daily.csv /tmp/fault_d/bike_daily.csv
666c666
< 668,"2012-10-29","FALL","2012","OCT","N","MON",12.68,30.9396,88,23.9994,2,20,22,"Y","BAD",667,7852
---
> 668,"2012-10-29","FALL","2012","OCT","N","MON",12.69,30.9396,88,23.9994,2,20,22,"Y","BAD",667,7852
$ cp /tmp/fault_d/bike_daily.csv data/raw/bike_daily.csv
$ make test
................                                                         [100%]
16 passed in 4.79s
```

A test comparing the SHA-256 of `data/raw/bike_daily.csv` to a value in
`src/config.py` would catch any change to the file. A `PreToolUse` hook on
`Bash` that rejects commands writing to `data/raw/` would block the `cp`.

### Implemented: hash check in `make data`

`RAW_SHA256` in `src/config.py` holds the file's SHA-256 as a literal.
`src.ingest.verify_raw()` runs in `make data` and raises if the file differs;
`tests/test_contract.py::test_raw_file_is_unchanged` makes `make test` go red
too. The hash is taken after normalising CRLF to LF: with `core.autocrlf=true`
a Windows checkout writes CRLF, and a plain `git checkout` restore does exactly
that, which a raw-byte hash would reject.

The check is not in `load_raw()`, so the other tests still run and fail for
their own reasons when the file changes.

The change (commit `1ef6b45`):

```diff
--- a/src/config.py
+++ b/src/config.py
@@ -20,6 +20,11 @@ DATA_URL = (
     "interpretable-ml-book/master/data/bike.csv"
 )
 
+# SHA-256 of the checked-in raw file. data/raw/ is write-denied for Edit and
+# Write, but not for Bash: a `cp` over the file passes every permission rule
+# and the PostToolUse hook. src/ingest.py refuses to run if this changes.
+RAW_SHA256 = "a6bed1577f6e4de56dcfae6d8315985073cc0ad3446c8c99ed60c86a0b5ad9dc"
+
 TARGET = "cnt"
--- a/src/ingest.py
+++ b/src/ingest.py
@@ -1,13 +1,14 @@
-"""Stage 1: fetch the raw dataset and assert its shape.
+"""Stage 1: fetch the raw dataset, verify its hash, and assert its shape.
 
 Run: python -m src.ingest
 """
+import hashlib
 import sys
 import urllib.request
 
 import pandas as pd
 
-from src.config import DATA_URL, RAW
+from src.config import DATA_URL, RAW, RAW_SHA256
@@ -20,6 +21,30 @@ def download(force: bool = False) -> None:
     urllib.request.urlretrieve(DATA_URL, RAW)
 
 
+def raw_sha256() -> str:
+    """SHA-256 of the raw file with line endings normalised to LF.
+
+    Git with core.autocrlf=true checks the CSV out with CRLF on Windows,
+    which changes the bytes but not the data. Normalising first means a
+    fresh Windows clone matches RAW_SHA256 and any real edit still does not.
+    """
+    return hashlib.sha256(RAW.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
+
+
+def verify_raw() -> None:
+    """Fail loudly if the raw file is not the one the results were built on.
+
+    Shape checks in load_raw() miss a single edited value: one changed
+    `temp` keeps every column and row and passes all the other tests.
+    """
+    actual = raw_sha256()
+    if actual != RAW_SHA256:
+        raise ValueError(
+            f"{RAW.name} has changed: sha256 {actual[:16]}..., expected {RAW_SHA256[:16]}... "
+            "Restore it with `git checkout -- data/raw/bike_daily.csv`."
+        )
+
+
 def load_raw() -> pd.DataFrame:
@@ -32,5 +57,6 @@ def load_raw() -> pd.DataFrame:
 
 if __name__ == "__main__":
     download(force="--force" in sys.argv)
+    verify_raw()
     df = load_raw()
-    print(f"OK ingest: {len(df)} rows, {df.dteday.min().date()} -> {df.dteday.max().date()}")
+    print(f"OK ingest: {len(df)} rows, {df.dteday.min().date()} -> {df.dteday.max().date()}, sha256 {RAW_SHA256[:16]}")
--- a/tests/test_contract.py
+++ b/tests/test_contract.py
@@ -3,9 +3,9 @@
-from src.config import LAG_WARMUP, TARGET
+from src.config import LAG_WARMUP, RAW_SHA256, TARGET
 from src.features import build_features, feature_columns, reindex_to_calendar
-from src.ingest import load_raw
+from src.ingest import load_raw, raw_sha256
@@ -19,6 +19,14 @@ def feats(raw):
     return build_features(raw)
 
 
+def test_raw_file_is_unchanged():
+    """data/raw/ is write-denied for Edit and Write but not for Bash, and the
+    PostToolUse hook never sees a `cp`. The hash is the only guard that does.
+    RAW_SHA256 is a literal in src/config.py, not computed from the file, so
+    this cannot pass by construction."""
+    assert raw_sha256() == RAW_SHA256, "data/raw/bike_daily.csv has changed"
+
+
 def test_calendar_is_complete_before_lagging(raw):
```

Re-seeded with the one-value edit above, which passed every test before:

```
$ cp /tmp/fault_d/bike_daily.csv data/raw/bike_daily.csv
$ make data
python -m src.ingest
    raise ValueError(
ValueError: bike_daily.csv has changed: sha256 01d7202d08d13d23..., expected a6bed1577f6e4de5... Restore it with `git checkout -- data/raw/bike_daily.csv`.
make: *** [Makefile:7: data] Error 1
$ make test
python -m pytest tests/ -q
E       AssertionError: data/raw/bike_daily.csv has changed
E       assert '01d7202d08d1...268046590e11c' == 'a6bed1577f6e...0c86a0b5ad9dc'
E         
E         - a6bed1577f6e4de56dcfae6d8315985073cc0ad3446c8c99ed60c86a0b5ad9dc
E         + 01d7202d08d13d23b34433f4b6b156fcfc1ce7aa1e5fd7b5ba1268046590e11c
FAILED tests/test_contract.py::test_raw_file_is_unchanged - AssertionError: d...
1 failed, 16 passed in 1.88s
make: *** [Makefile:16: test] Error 1
```

Restored; `make data` printed
`OK ingest: 728 rows, 2011-01-03 -> 2012-12-31, sha256 a6bed1577f6e4de5` and
`make test` gave `17 passed`. A CRLF copy of the unchanged file also passes
`make data`.

It detects the change; it does not block the `cp`. Blocking would need the
`PreToolUse` hook on `Bash`.
