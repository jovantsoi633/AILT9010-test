# Midterm completion and submission checklist

**Deadline: 26 October 2026, precise Moodle time pending verification.** This checklist records work to verify, not evidence that every item is complete. The revised submitted proposal takes precedence over the earlier background summary; exclude its final peer-review material.

## Core prototype

- [ ] Confirm the fixed ©2018 OpenStax source, chapters 3/5, source hash, license, and attribution against the actual PDF.
- [ ] Confirm paragraph data preserves original wording and identifies chapter, section, PDF page, source, and stable paragraph ID.
- [ ] With no API key, select a chapter, search `market equilibrium`, and expand a real source paragraph.
- [ ] Verify no-key search makes zero model requests and works after a model connection failure.
- [ ] Use a real API key for one supply/demand and one elasticity question; retain actual output and timing evidence.
- [ ] Confirm local dummy personal-information cases make zero API requests.
- [ ] Confirm fixed refusals for advice, prediction, ghostwriting, and non-economics requests; confirm a normal homework concept explanation is permitted.
- [ ] Check top-three retrieval, calibrated τ, keyword overlap, chapter filtering, and insufficient-evidence behavior.
- [ ] Confirm citations map to excerpts actually sent to the answer model; manually assess correctness, citation support, and evidence-external claims.
- [ ] Distinguish connection/format failures from insufficient textbook evidence.

## Reproduction and evidence

- [ ] Run unit tests, calibration, and offline development evaluation; preserve timestamped reports and exact commands.
- [ ] Run live development evaluation with a real key; mark every unrun item pending, never inferred from mocks.
- [ ] Have a member who did not write the README follow it on another computer. Complete `first_use_check.md` with actual details.
- [ ] Save the demonstrated code version, dependency versions, development inputs, expected/actual results, references, API call counts, and evidence links.
- [ ] Record observed failures and limits; do not claim the final 21-question evaluation has passed.
- [ ] Push the final code to [jovantsoi633/AILT9010-test](https://github.com/jovantsoi633/AILT9010-test); verify repository privacy and course-team access.

## Submission artifacts

- [ ] Download the actual Moodle companion template; it is not included in the supplied materials.
- [ ] Transfer the status draft into that template and export one readable PDF page.
- [ ] Replace all placeholders with verified member names, actual completed work, evidence links, dates, and owners. AI-generated files are not personal student contributions.
- [ ] State actual blockers with owners/next actions, or honestly report none after review.
- [ ] Record three future milestones with dates, named owners, and completion criteria.
- [ ] Record a genuine run. MP4 ≤60 seconds; visible English input, processing, output, and expanded source; captions or narration readable. See `recording_script.md`.
- [ ] If only source search is recorded, label it as source-search evidence. It does not demonstrate live AI Q&A.
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

The companion template, private-repository access, real member contributions, independent reproduction, and live API evidence require human/account context. Leave them pending until actually verified.
