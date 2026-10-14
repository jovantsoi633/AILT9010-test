# AILT9019 Midterm Status — DRAFT, NOT FOR SUBMISSION

**Team:** [PENDING: official group and members] · **Repository:** https://github.com/jovantsoi633/AILT9010-test (course access pending)
**Code version/date:** [PENDING: demonstrated commit and date] · **Deadline:** 26 October 2026, Moodle time to verify

Transfer this content into the **actual Moodle companion template**, then export exactly one page. The official template has not been supplied. Replace every pending field with verified information; do not submit this draft.

**Working now.** Local English Streamlit prototype with 203 original paragraphs from OpenStax _Principles of Economics 2e_ (©2018), chapters 3 and 5. Real-browser no-key search and source inspection verified. Implemented session-only masked key, request check/query rewrite, top-three relevance filtering, grounded QA and source citations. Live API operation is deferred pending a real-key run; mocked tests do not establish live behavior.

**Evidence and testing.** 53/53 automated tests passed (evidence/test_summary.json). Annotated-keyword retrieval: 4/4 required references retained; 3/3 uncovered cases filtered. Synthetic PII: 3/3 blocked, zero client calls (evidence/development_offline.json). Captioned Source search recording and browser_check.json verify `market equilibrium` → PDF61/printed51. These are tuned offline development results, not live QA accuracy. **Independent first use:** [PENDING: non-README-author, computer, date, outcome]. The formal 21-question set has not been evaluated.

**Limits and blockers.** Only demand/supply and elasticity; text excerpts do not reconstruct graphs or tables. Personal-information patterns and citation labels cannot guarantee privacy detection or factual support. **Observed failures:** [PENDING: actual failures and impact]. **Handoffs:** real API validation — [owner/name + next action]; course-team repository access — [owner/name + next action]; official template and first-use record — [owner/name + next action]. Replace this list with current blockers after review.

**Next two weeks.**

| Due (2026) | Named owner | Completion criterion |
|---|---|---|
| 30 Oct | [PENDING: AI/testing member] | Evaluator saves real development outputs and checks retrieval, refusal, and insufficient evidence. |
| 6 Nov | [PENDING: textbook/testing member] | Freeze 21 formal questions, evidence, τ, and baseline conditions (Gate 3). |
| 9 Nov | [PENDING: evaluation coordinator] | Start one formal system/baseline run; save outputs; assign two reviewers for 9–13 Nov. |

**Contributions and scope.** [PENDING: each real member's specific completed work, linked artifact/commit, verification date; add rows in the official template]. AI-authored implementation and documents are recorded separately and cannot stand in for a student's contribution. Retain textbook search, guarded Q&A, provenance, and reproducibility. Defer dedicated concept-comparison UI, exercise recommendations, semantic retrieval, accounts, public hosting, and final website/report work.
