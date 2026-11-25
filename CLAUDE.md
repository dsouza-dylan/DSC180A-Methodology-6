# Bikeshare demand capstone

Daily Capital Bikeshare counts, 2011-2012. We forecast `cnt` (total daily
rides) from calendar, weather, and lagged-demand features.

## Commands
- `make data` - verify the raw CSV's hash and assert its shape
- `make features` - build `data/processed/features.parquet`
- `make train` - fit models, write `reports/metrics.json`
- `make test` - pytest; run this before claiming anything works
- `make all` - the three pipeline stages in order. It reproduces
  `reports/metrics.json`, the source of every number in `REPORT.md`;
  re-run it and commit the result after any code change.
- `/new-feature <name>` adds a feature with its test; `/ablation <feature>`
  measures what one feature adds on validation.

## Non-negotiable rules
- **Never** put `casual` or `registered` in a feature set:
  `casual + registered == cnt` exactly. `src/config.py` lists these and the
  other excluded columns (`cnt_2d_bfr`, raw time indexes) with the reason
  for each. Derive feature lists from `FORBIDDEN`; never hand-type them.
- **Never** split this data randomly. Use `src.train.temporal_split`.
  Train = 2011, valid = H1 2012, test = H2 2012. Never tune on test.
- Any new lag, rolling, or difference feature (like `temp_change_1`) must
  be built on a gap-free calendar index (`src.features.reindex_to_calendar`)
  and must `.shift(1)` before it aggregates. Add a test for it in
  `tests/test_leakage.py`.
- `data/raw/bike_daily.csv` is immutable. If `make data` reports a hash
  mismatch, restore it with `git checkout`; **never** update `RAW_SHA256`.
- A new raw column goes into one of the classification sets in
  `src/config.py`, with its reason, before anything uses it.
- `python -m src.train --diff-roll7` is the Exercise 4 experiment and only
  prints. Never make it the default or put its numbers in `metrics.json`.
- Report the mean baseline **and** the persistence baseline (yesterday's
  count) alongside every model. A negative R^2 is a finding, not a bug
  to hide.

## Style
- Standard library, pandas, scikit-learn only. No new dependencies
  without asking. Versions are pinned in `requirements.txt`.
- Modules are runnable: `python -m src.<module>` prints a one-line `OK ...`
  summary.
- Paths and constants live in `src/config.py`. Nothing is hardcoded twice.

## Gotchas
- The mirror in `DATA_URL` is missing 2011-03-10. It is NOT the UCI file:
  728 rows from 2011-01-03, not 731 from 2011-01-01.
- `weather` uses the labels `GOOD` / `MISTY` / `BAD`, not the UCI codes 1-4.
- Ridership grew ~65% from 2011 to 2012, so tree models trained on 2011
  cannot extrapolate to 2012. That is the headline result, not an error.
- 2012-10-29 (Hurricane Sandy, 22 rides) is in the test set. Expect it in
  any residual plot.
- The PostToolUse hook needs the `.venv` Python. If it prints "Python was
  not found" or "No module named pytest", the venv is not active: say so,
  and do not treat the edit as passing.
