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
(`path="${path//\//}"`); the output above is from after that fix.

### Turns to fix

1
