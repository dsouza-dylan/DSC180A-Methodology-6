---
name: ablation
description: Measure what one feature contributes by dropping it and refitting ridge and hgb on validation. Use when someone asks whether a feature earns its place, or before keeping or removing one.
allowed-tools: Read, Bash(python .claude/skills/ablation/ablate.py*), Bash(make features*)
---

# Ablation: $ARGUMENTS

Work in this order.

1. **Check the argument.** `$ARGUMENTS` must be exactly one feature name.
   If it is empty or more than one word, list the current features (step 2
   prints them on a bad name) and stop.

2. **Run it.** If `data/processed/features.parquet` is missing or older than
   `src/features.py`, run `make features` first. Then:

       python .claude/skills/ablation/ablate.py $ARGUMENTS

   The script scores validation only. Do not compute or report test-set
   numbers here; the test split is touched once, at the end.

3. **Report** the printed table as is: R^2 and MAE with and without the
   feature for ridge and hgb, with both baselines beside them.

4. **Judge it** in one sentence per model. The validation set is 182 days:
   a delta under 0.01 R^2 is noise, so say the feature does not earn its
   place for that model. A negative delta means the model does better
   without it; say so plainly.

5. **Do not change any code.** If the result argues for removing the
   feature, recommend it and stop. Removing it is a decision for
   `docs/DECISIONS.md`, recorded by hand.
