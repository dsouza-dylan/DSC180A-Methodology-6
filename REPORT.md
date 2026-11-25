# Bikeshare demand: report

Daily Capital Bikeshare ridership (`cnt`), Washington DC, 2011-2012. Train on
2011 (348 days), validate on H1 2012 (182), test on H2 2012 (184). Every
number below comes from `make all` (`reports/metrics.json`) unless marked
as Exercise 4.

## Results

"Before" is the starter feature set (14 features, commit `dcadd4b`); "after"
adds `temp_change_1` (15 features, `reports/metrics.json`).

| Model | Features | Valid R^2 | Valid MAE | Test R^2 | Test MAE |
|---|---|---:|---:|---:|---:|
| baseline_mean | before | -0.9318 | 2002.2 | -2.1441 | 2847.7 |
| baseline_mean | after | -0.9318 | 2002.2 | -2.1441 | 2847.7 |
| baseline_persistence | before | 0.4507 | 900.6 | 0.5099 | 840.1 |
| baseline_persistence | after | 0.4507 | 900.6 | 0.5099 | 840.1 |
| ridge | before | 0.6475 | 832.9 | 0.5833 | 947.1 |
| ridge | after | 0.6992 | 738.1 | 0.6281 | 866.8 |
| hgb | before | 0.2185 | 1296.6 | -0.4975 | 1972.6 |
| hgb | after | 0.1873 | 1323.3 | -0.5516 | 2011.1 |

The baselines do not use the feature set, so their rows do not change.
`python -m src.train` prints test scores on every run; those printed numbers
were never used to choose or keep anything. Every decision in
`docs/DECISIONS.md` was made on validation.

## Headline finding

Ridge is the only model that beats both baselines on R^2: test R^2 0.628
against 0.510 for persistence and -2.144 for the training mean. Gradient
boosting is negative on test (-0.552, worse than predicting the test period's
own average every day) yet still beats the mean baseline comfortably
(-0.552 against -2.144); it loses to persistence because ridership grew about
65% from 2011 to 2012 and trees cannot predict values above anything in their
training data, while ridge extrapolates the lagged-demand trend linearly.
Ridge's lead over persistence is in R^2 only: on MAE it loses, 866.8 rides a
day against 840.1 (Exercise 5). Adding `temp_change_1`
raised ridge's validation R^2 from 0.6475 to 0.6992 (+0.052, five times the
0.01 noise threshold) while lowering hgb's from 0.2185 to 0.1873, and I kept
it.

## Exercise 4: target transformation

Hgb fails on level, not signal: 2012 sits above all of 2011, so a tree trained
on raw counts cannot reach it. If the target is the deviation from last week's
mean, `cnt - cnt_roll_7`, the growth cancels and the target stays in the range
the tree was trained on. `cnt_roll_7` is the mean of the seven days before d
and is already a feature, so this adds no information unavailable at
prediction time. The code is `RelativeToRoll7` in `src/train.py`, run with
`python -m src.train --diff-roll7`; it only prints, and `reports/metrics.json`
stays the untransformed pipeline.

I chose it on validation from six transformations:

| hgb target | Valid R^2 | Valid MAE |
|---|---:|---:|
| `cnt` (untransformed) | 0.187 | 1323.3 |
| `log(cnt)` | 0.159 | 1351.0 |
| `cnt - cnt_lag_1` | 0.644 | 759.8 |
| `cnt / cnt_lag_1` | 0.618 | 816.7 |
| `cnt - cnt_roll_7` | 0.759 | 663.4 |
| `cnt / cnt_roll_7` | 0.774 | 650.3 |
| `log(cnt / cnt_roll_7)` | 0.765 | 654.8 |

`log(cnt)` does nothing, which supports the diagnosis: the problem is
extrapolation, not skew. The three `cnt_roll_7` variants are within 0.015 of
each other on 182 days, so the data does not pick between them; I took the
difference because it is the simplest. The transformation applies to ridge as
well, so hgb is not compared against an untransformed rival.

I then ran the test set once, on 2026-11-25:

| Model | Test R^2, untransformed -> `cnt - cnt_roll_7` | Test MAE |
|---|---|---|
| hgb | -0.552 -> 0.644 | 2011.1 -> 817.6 |
| ridge | 0.628 -> 0.634 | 866.8 -> 852.7 |
| persistence | 0.510 | 840.1 |

For the argument: it removes exactly the trend the diagnosis blamed, it barely
moves ridge (+0.006 test R^2), which already handles trend, and it uses nothing
a forecaster would not have. Against it: hgb's 0.05 validation lead over ridge
shrank to 0.01 on test, which is what selecting among six variants on 182 days
looks like, so hgb and ridge effectively tie. Transformed hgb is the only model
that beats persistence on test MAE (817.6 against 840.1).

I would say the transformation is defensible: it barely moves ridge's R^2, but
it gets rid of the trend problem without any data leakage. It makes hgb much
better, from -0.552 to 0.644 on test, enough to compete with ridge.

## Exercise 5: ridge vs persistence

On test, ridge beats "yesterday again" on R^2 (0.628 against 0.510) and loses
on MAE (866.8 against 840.1 rides a day). The two metrics disagree because the
errors have different shapes. Persistence is better on a typical day: its
median miss is 507 rides against ridge's 795, and ridge is closer on only 83 of
184 days. But persistence fails badly whenever demand changes abruptly, because
it repeats the change one day late. On its worst 10% of days it misses by 2,909
rides on average, ridge by 1,791; the day after Hurricane Sandy it predicted 22
rides for a day that had 1,096, and on the day after that, 1,096 for a day that
had 5,566. R^2 squares errors, so those misses dominate it; MAE weights every
ride equally, so the typical days dominate. Ridge's RMSE is 13% lower (1,062
against 1,219); transformed hgb (Exercise 4) beats persistence on both R^2 and
MAE.

I feel ridge is better, because we do not care as much about typical days as
about the days when demand changes. So while persistence is better on most
days and on MAE, ridge is better adapted to our study objective, and for that
objective R^2 matters more.

## Attribution

Model: Claude Opus 5.5 (`claude-opus-5-5`, hosted by Anthropic, which does not publish its size) via Claude Code, used throughout with no model switch, in place of the local `bikeshare-coder` (instructor-approved).

**(a) Generated by the agent**

- `src/features.py`: the `temp_change_1` feature, built by following the `/new-feature` skill's steps by hand (the slash command was not loaded in that session).
- `src/train.py`: `RelativeToRoll7` and the `--diff-roll7` flag.
- `src/config.py`: `RAW_SHA256`, `RAW_FEATURE_COLS`, `ENCODED_COLS`, `REDUNDANT_COLS`.
- `src/ingest.py`: `raw_sha256()` and `verify_raw()`.
- `tests/test_leakage.py`: `test_temp_change_1_uses_yesterday_only`, `test_encode_weather_rejects_unknown_labels`.
- `tests/test_contract.py`: `test_raw_file_is_unchanged`, `test_every_raw_column_is_classified`, `test_classified_features_reach_the_model`.
- `.claude/hooks/check_leakage.sh`: the backslash-path fix.
- `.claude/skills/ablation/`: `SKILL.md` and `ablate.py`.
- `.gitignore` edits and `CLAUDE.md` edits.
- `docs/SEEDED_FAULTS.md`, `docs/AUDIT.md` (except the verdict), and the wording of my `docs/DECISIONS.md` lines.
- `REPORT.md`: drafting the object results except interpretations made by me, such as the Exercise 4 verdict, the Exercise 5 conclusion, and list (b).
- `reports/metrics.json` (`make all`) and `reports/audit.jsonl` (`agent/audit.py`) are command output.

**(b) Decisions that were mine**


- Kept the starter's target (`cnt`), leakage rule, date split, and both baselines (the undated starter lines).
- Chose `temp_change_1` as my feature and kept it on its validation gain (2026-11-20).
- Implemented the fault (d) catch as a hash check in `make data` (2026-11-25).
- Chose `cnt - cnt_roll_7` for Exercise 4 and judged it defensible (2026-11-25).
- Chose `/ablation` as my skill (2026-11-25) and approved the `CLAUDE.md` changes (2026-11-25).
- Judged ridge worth deploying over persistence for this study's objective (2026-11-25).
