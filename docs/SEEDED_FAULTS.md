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
