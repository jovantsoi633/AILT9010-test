# Midterm completion and submission checklist

**Deadline: 26 October 2026, precise Moodle time pending verification.** Checked items below refer to saved evidence. Live API validation and member details are deferred by the user. The revised submitted proposal takes precedence over the background summary; exclude its final peer-review material.

## Core prototype

- [x] Confirm fixed ©2018 OpenStax source/chapters/license/attribution; see `data/source_manifest.json` and `docs/data_notes.md`.
- [x] Verify 203 original prose excerpts with stable IDs and source metadata; corpus checks pass.
- [x] Run no-key `market equilibrium` search and inspect a real paragraph in the browser; see `evidence/browser_check.json`.
- [ ] Verify no-key search makes zero model requests and works after a model connection failure.
- [ ] Real-key supply/demand and elasticity checks — deferred by user; no live results claimed.
- [x] Synthetic personal-information checks 3/3 blocked with zero calls; see `evidence/development_offline.json`.
- [ ] Confirm fixed refusals for advice, prediction, ghostwriting, and non-economics requests; confirm a normal homework concept explanation is permitted.
- [ ] Check top-three retrieval, calibrated τ, keyword overlap, chapter filtering, and insufficient-evidence behavior.
- [ ] Confirm citations map to excerpts actually sent to the answer model; manually assess correctness, citation support, and evidence-external claims.
- [ ] Distinguish connection/format failures from insufficient textbook evidence.

## Reproduction and evidence

- [x] Save 53/53 AI-assisted automated checks, provisional calibration, and offline evaluation in `evidence/`.
- [ ] Live development evaluation — deferred by user; not inferred from mocks.
- [x] Fresh remote checkout c799b0c: hash/start/search checks pass on the same computer and existing runtime (`evidence/reproduction_check.json`).
- [ ] Have a member who did not write the README follow it on another computer. Complete `first_use_check.md` with actual details.
- [ ] Save the demonstrated code version, dependency versions, development inputs, expected/actual results, references, API call counts, and evidence links.
- [ ] Record observed failures and limits; do not claim the final 21-question evaluation has passed.
- [ ] Push the final code to [jovantsoi633/AILT9010-test](https://github.com/jovantsoi633/AILT9010-test); verify repository privacy and course-team access.

## Submission artifacts

- [x] Inspect supplied `AILT9019_Midterm_Status_Sheet_Template.docx`; preserve all official headings, tables and styles.
- [x] Fill verified evidence into a separate draft DOCX with the official template builder; member/owner placeholders remain.
- [x] Native Word export of the actual filled DOCX is one readable PDF page; recheck after any member/owner edits.
- [ ] Replace all placeholders with verified member names, actual completed work, evidence links, dates, and owners. AI-generated files are not personal student contributions.
- [ ] State actual blockers with owners/next actions, or honestly report none after review.
- [ ] Record three future milestones with dates, named owners, and completion criteria.
- [x] Record genuine 27.2-second MP4 with captions, real input/search/results/expanded source (`evidence/source_search_demo.mp4`).
- [x] Label recording as Source search only; it does not demonstrate live Q&A.
- [ ] Play the complete MP4 and check duration, text legibility, sound/captions, and absence of keys/personal information.
- [ ] Package only `video.mp4`, `repository_link.txt`, and `status_sheet.pdf`; ZIP ≤100,000,000 bytes.
- [ ] Open the ZIP and each extracted file; recheck repository access as the course team would see it.
- [ ] Submit to the correct Moodle group slot before its exact deadline; verify all members can see the receipt.

## Milestones after the midterm

| Date (2026) | Owner to assign | Completion criterion |
|---|---|---|
| 30 October | [PENDING: actual AI/testing member] | Development evaluator saves real outputs and checks retrieval, refusals, and insufficient evidence. |
| 6 November | [PENDING: actual textbook/testing member] | Freeze 21 formal questions, reference evidence, τ, and baseline conditions (Gate 3). |
| 9 November | [PENDING: actual evaluation coordinator] | Start one formal run for system/baseline; preserve outputs and assign two independent reviewers for 9–13 November. |

The supplied repository is currently public (different from the proposal). Course access/visibility review, real member contributions, independent first use, and live API evidence remain pending; member details/live validation were deferred by the user. No final submission ZIP exists while member/owner placeholders remain.
