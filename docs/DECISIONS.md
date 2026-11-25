# Decisions

One line per methodological decision: what you chose, why, and what it changed.
Agents append here via the `/new-feature` skill; you append here by hand.

- Exclude `casual`, `registered`: they sum to `cnt` exactly. Leaky model R^2 1.000 -> honest ridge 0.583.
- Exclude `cnt_2d_bfr`: a shipped 2-day lag we cannot test the alignment of. Build our own lags instead.
- Exclude `instant`, `yr`, `days_since_2011`: time indexes let a tree predict a flat constant past 2011 and a linear model extrapolate a trend we have no grounds for.
- Split 2011 / H1 2012 / H2 2012 by date. Test set touched once, after all feature work.
- Report mean and persistence baselines with every score. Persistence (test R^2 0.510, MAE 840) is within 0.07 R^2 of ridge and beats it on MAE; that caveat goes in the report.
- 2026-11-20: Added `temp_change_1` = temp(d) - temp(d-1) on the calendar index; same-day temp is already treated as available, so no new leakage. Valid R^2 ridge 0.6475 -> 0.6992, hgb 0.2185 -> 0.1873. Kept (decided on validation only).
- 2026-11-20: Normalised backslashes to `/` in `.claude/hooks/check_leakage.sh` before the `*src/*.py` match. Claude Code passes Windows paths with `\`, so the hook exited 0 on every edit and never fired. Mac/Linux paths are unaffected.
- 2026-11-20: Added `test_encode_weather_rejects_unknown_labels`. Fault (c) (removing the encoder's `raise`) passed every existing test, because the data has no unmapped labels and nothing tested `encode_weather` directly.
- 2026-11-25: Added a SHA-256 check on `data/raw/bike_daily.csv` (`RAW_SHA256` in config, `verify_raw()` in `make data`, `test_raw_file_is_unchanged`): the Bash `cp` in fault (d) bypassed the hook and the deny rules, and a one-value edit passed all 16 tests. Hash taken after CRLF -> LF so a Windows `core.autocrlf` checkout still matches. Kept out of `load_raw()` so other tests still report their own failures.
- 2026-11-25: Ex 4: ridge and hgb predict `cnt - cnt_roll_7` behind `python -m src.train --diff-roll7` (off by default; prints, never writes `metrics.json`). Chosen from 6 transformations on validation only (hgb valid R^2 0.187 -> 0.759; ratio 0.774 within noise, difference chosen as simpler; `log(cnt)` 0.159, so the failure is extrapolation, not skew). Test touched once: hgb -0.552 -> 0.644, ridge 0.628 -> 0.634. Defensible: it removes the growth trees cannot extrapolate and adds no information; it lets hgb tie ridge, not beat it.
- 2026-11-25: Classified every raw column in `src/config.py` (`RAW_FEATURE_COLS`, `ENCODED_COLS`, `REDUNDANT_COLS` for `season`/`mnth`/`weekday`, plus `FORBIDDEN` and `dteday`) and added `test_every_raw_column_is_classified`. Defined against these lists, not `feature_columns()`, which admits any numeric column: with `rides_total = cnt` appended to the CSV, `test_no_forbidden_features` still passed.
- 2026-11-25: Added the `/ablation <feature>` skill (`.claude/skills/ablation/`): drops one feature, refits ridge and hgb, prints the validation delta with both baselines. It automates the with/without comparison done by hand for `temp_change_1` and reproduces it (ridge +0.0517, hgb -0.0311). Validation only; rejects a name that is not a model feature so a typo cannot report "no change".
