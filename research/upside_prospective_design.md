# Independent prospective upside evaluation — frozen 2026-10-12

## Why a fresh future window is necessary
The previous study already inspected 2018-01 through 2026-07, so those observations cannot be called untouched test data. The future shadow study starts with the **2026-08 prediction**, whose subsequent 2026-09 monthly sale price has not appeared in the trusted source at freeze time.

Production monthly master ends at 2026-07 because ECOS M2 ends there. The independent price-only R-ONE long-cycle source extends to 2026-08. Its 2006-01 through 2026-07 price prefix exactly matches the monthly master. R-ONE status=full, collected 2026-10-07T01:28:36Z, 2026-08 index=102.331049252088.

**Previously unscored but already realized context (not prospective):** July 2026 forecast had rising probabilities 84.6% baseline uniform K10, 84.6% inverse K10, 88.9% inverse K15. August index gained 1.0519% over July, a rise. One realized observation is not meaningful independent validation.

## Frozen 2026-08 prediction for the next month

| Model | Rise | Flat | Fall |
| --- | ---: | ---: | ---: |
| Certified uniform K10 | 84.62% | 7.69% | 7.69% |
| Inverse distance K10 | 84.62% | 7.69% | 7.69% |
| Inverse distance K15 | 88.89% | 5.56% | 5.56% |

August price momentum: 1 month +1.0519%, 3 months +3.5702%.

## Predeclared protocol
- Freeze candidate definitions, historical flat-band, outputs, required sample size, and source provenance before observing 2026-09 prices.
- Train only with targets matured at the prediction month. Never use future price or labels for a forecast.
- Archive every forecast before its next monthly observation arrives. Archive each first observed outcome once; never rewrite prior predictions or first published labels after source revision.
- A monthly source update appends newly mature outcomes and the *newest unmatured* prediction; if any month was missed, record a gap rather than manufacturing a retrospective forecast.
- Use only R-ONE monthly price index for the 1-month model; do not substitute weekly estimates.
- Require **24 independently matured months**, six rising and six non-rising months, and no gaps before a separate certification review. This is a minimum, not an automatic promotion threshold.
- Compare paired Brier, AUC, calibration ECE, accuracy, macro-F1, monthly jumps, transition detection, and block-bootstrap intervals at review. Preserve the currently certified production model until convincing independent performance improvement is demonstrated.
- The current certified 3/6-month models and rejected 12-month model remain untouched.
- At the protocol freeze (2026-10-12), there are **0 independently matured months**. This is not evidence of either superiority or inferiority.

## Files and commands
- scripts/evaluate_upside_prospective.py --check : read-only guard.
- scripts/test_upside_prospective_evaluation.py : no-future-label and append-only regression tests.
- scripts/evaluate_upside_prospective.py --update --source-commit SHA : append source-backed forecasts and outcomes.
- research/upside_prospective_protocol.json : fixed definitions.
- research/upside_prospective_journal.json : append-only evidence log.
- research/upside_prospective_report.json : descriptive research-only status.
- .github/workflows/upside-prospective-evaluation.yml : lightweight source-update hook, no external collection or heavy data pipelines.

Scope is metadata from the REB source, not a geographic formula constant. The R-ONE monthly source collection itself must keep running for new data to arrive.

## Future source receipt automation (2026-10-12 addition)
Scheduled R-ONE refresh runs monthly on the 22nd at 06:30 KST through the existing production-secret RONE_API_KEY, and persists data_sources/reb_long_cycle.json **only when underlying price/trade observations changed**. The workflow confirms full source status and non-regression of month coverage. When collection is delayed or fails, it does not write fabricated data or advance the journal. Existing-source push events also run the shadow evaluation independently, with no collector in the push case. A Git blob SHA fingerprints source contents in each newly captured snapshot. This is monthly collection only and does not execute heavy dashboard refreshes.
