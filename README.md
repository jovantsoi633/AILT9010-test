# AILT9019: Textbook Learning Assistant

A local English-language study prototype for **demand and supply** and **elasticity**. Search the textbook without an API key, or connect your own DeepSeek API account to ask concept questions with inspectable textbook citations.

This is coursework in development. Offline checks and live model checks are distinct: a passing mocked test does not establish live answer quality. Live validation, independent first-use reproduction, course-team repository access, and the official Moodle status sheet must be verified before the midterm submission. Project repository: [jovantsoi633/AILT9010-test](https://github.com/jovantsoi633/AILT9010-test).

## Verified implementation snapshot

The 15 October 2026 build includes 203 original textbook paragraphs and passed **53 automated checks**. Real-browser Source search was exercised with both chapters; [the captioned MP4](evidence/source_search_demo.mp4) demonstrates the demand/supply path without an API key. See [test results](evidence/test_summary.json), [offline development evidence](evidence/development_offline.json), and [browser evidence](evidence/browser_check.json). Annotated keyword retrieval retained the required reference in 4/4 development cases and filtered all passages in 3/3 uncovered cases. These small, tuned development results are **not live AI or final-set accuracy**. Live validation is deferred at the user's request; member details will be supplied later.

The user-supplied repository is currently **public**, which differs from the proposal's private-distribution plan. Review repository visibility and course access before the submission. Only the licensed prose corpus is included; the full PDF and local environment are not required to run the app.

## Run locally

Use Python **3.11 or newer**. Python 3.12 is the development environment. Clone the repository or extract its source archive into a local directory, then open a terminal there.

**Windows PowerShell**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Using the environment's Python directly avoids changing PowerShell execution policy. If Python 3.12 is unavailable, use an installed Python version of at least 3.11.

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open the local URL printed by Streamlit, usually `http://localhost:8501`. Keep the terminal running. Press Ctrl+C to stop the application. The processed textbook data is included; downloading or processing the full PDF is unnecessary for ordinary use.

## Use the two modes

**Source search** requires no key. Under **Search within**, select a chapter or **All included chapters**, enter an English term such as `market equilibrium`, and click **Find passages**. Expand a result to see the original paragraph, chapter, section, PDF page, and attribution. Source search uses local BM25 retrieval and makes no model request.

**AI Q&A** requires an API key with access to the configured model. Create or manage a key in the [DeepSeek platform](https://platform.deepseek.com/), choose AI Q&A, and enter the key in **AI connection → API key** (masked). Set **Base URL** and **Model** if needed, then enter the question and click **Explain with evidence**. The default connection uses `https://api.deepseek.com` and model `deepseek-flash`. See the provider's [API quick start](https://api-docs.deepseek.com/) and [JSON output requirements](https://api-docs.deepseek.com/guides/json_mode/) if configuring another supported model. Provider model names and availability can change; consult the [current model information](https://api-docs.deepseek.com/quick_start/pricing/).

Try this English question with the demand and supply chapter selected:

> When a product's own price rises and people buy less, is that a change in demand or quantity demanded?

The key is held in the current Streamlit session and is not deliberately written to project files or included in evidence. A permitted question can make two paid model requests: one for request checking and query rewriting, and one for the grounded answer. The provider receives the question and instructions; the answer request also includes the retrieved textbook excerpts. Source search remains available if the model connection fails. Do not enter real personal information.

## How the question flow works

1. Local patterns block obvious email addresses, telephone numbers, and labelled student IDs before any API request. Pattern checks are limited and cannot recognize every form of personal information.
2. The first model call classifies the request and rewrites an allowed economics concept question into English search terms. Code returns a fixed refusal for investment advice, market predictions, assessed-work writing or grading, and non-economics requests. Requests to explain a concept remain allowed, including when the learner mentions homework.
3. BM25 retrieves at most three paragraphs within the chapter selection. A paragraph must meet threshold τ and share at least one non-stopword query term. The included calibration uses annotated development keywords and remains **provisional** until actual model rewrites are checked.
4. If no paragraph qualifies, the application returns insufficient evidence without an answer-model call. Otherwise, the second model call explains the concept using the supplied excerpts, or reports insufficient evidence.
5. `[P1]`–`[P3]` labels refer to the actual excerpts sent for that answer. Expand sources to check them. Citation validation can reject malformed labels; it does not prove that a sentence is supported, so answer quality also needs human review.

Connection or response-format failures appear separately from insufficient textbook evidence. No precomputed answer is presented as a live result.

## Textbook provenance and scope

The source is **OpenStax, _Principles of Economics 2e_, ©2018**, chapter **3 sections 3.1–3.5 (Demand and Supply)** and chapter **5 sections 5.1–5.4 (Elasticity)**. Paragraphs preserve the source wording with line wrapping/whitespace normalization. This is a prose excerpt corpus: figures, tables, equations, and equation-bearing paragraphs are omitted. Questions requiring their visual or numerical information may not be answerable. See the precise exclusions and provenance in [data notes](docs/data_notes.md).

- [Source PDF](https://d3bxy9euw4e147.cloudfront.net/oscms-prodcms/media/documents/Economics2e-LR.pdf)
- PDF SHA-256: `4294836051532268aa0ffd3f2926db9b1b9e620fad415f73d3941265d063feca`
- License: [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/), with source attribution retained in the dataset and displayed results. Any exceptions or third-party credits in the source retain their original terms.
- Every stored excerpt has a stable ID and source metadata. **PDF page numbers are one-based file pages**, which can differ from printed textbook page numbers. Use the displayed page type when checking a citation.

Keep the source metadata and licensing notices with any redistributed excerpt data. The app code's license, if any, does not replace the textbook's license.

To optionally rebuild or audit the corpus, download the pinned PDF to `data/source/Economics2e-LR.pdf` and use the installed extraction dependency from `requirements.txt`:

```bash
python scripts/build_corpus.py --check
python scripts/build_corpus.py
```

`--check` verifies the stored corpus without rewriting it; the second command regenerates it. Both refuse a PDF with another checksum. Recalibrate after any corpus change. The original full PDF is gitignored and not required when running the app or the ordinary checks.

## Development checks and evidence

Run these commands with the virtual environment's Python. In PowerShell, substitute `.\.venv\Scripts\python.exe` for `python` when the environment is not activated.

```bash
python -m unittest discover -s tests -v
python scripts/calibrate.py
python scripts/evaluate.py --offline
python scripts/evaluate.py --live
```

The live evaluator requests the API key using a hidden prompt; do not pass it as a command argument or commit it. Live requests incur provider charges. Calibration writes `evidence/calibration.json` and `data/retrieval_config.json`; evaluators write `evidence/development_offline.json` or `evidence/development_live.json`. Review the generated report's mode and timestamp before citing results. An offline report exercises local retrieval or controlled test responses and is not a real API evaluation.

After a real live development run, preserve a dated copy of its report and calibrate using its actual search rewrites:

```bash
python scripts/calibrate.py --live-results evidence/development_live.json
```

Stop and restart Streamlit after regenerating corpus or calibration files because the app caches its local index/settings. Re-run live development checks against the new threshold before reporting outcomes, preserving the previous report rather than silently replacing evidence.

The development set contains ten questions: four in-scope concepts, three economics topics outside the included chapters, and three requests that should be refused. Additional checks cover synthetic personal information, a non-economics request, a normal homework explanation request, assessed-work grading, chapter restrictions, and connection failure. Expected reference paragraphs are checked against the actual textbook. Keep the final 21-question evaluation set separate; it is not run as part of midterm development.

Read [first-use checks](docs/first_use_check.md) for an independent reproduction record and [the submission checklist](docs/midterm_checklist.md) for remaining handoffs. No independent participant or contribution should be inferred from AI-authored files.

To render the separate one-page **working draft** locally, install `requirements-dev.txt` and run `python scripts/render_status_draft.py`. It writes `output/pdf/midterm_status_draft.pdf` and explicitly retains unverified fields. It is not the official Moodle companion template.

## Prepare the midterm handoff

The deadline is **26 October 2026**, at the precise time shown in Moodle. The submission is a ZIP of at most **100 MB** containing a real screen recording of no more than **60 seconds**, `repository_link.txt`, and a one-page status sheet using the Moodle companion template.

Preparation documents:

- [One-page status-sheet draft](docs/status_sheet_draft.md): working copy with explicit pending fields; transfer it to the actual companion template.
- [Recording script](docs/recording_script.md): real input → processing → output → expanded source; no simulated live answers.
- [Contribution record](docs/team_contributions.md): each member records and verifies their own completed work.

Once a real recording, accessible GitHub repository, and completed official-template PDF exist, package them:

```bash
python scripts/package_midterm.py --video submission/video.mp4 --repository-url https://github.com/jovantsoi633/AILT9010-test --status-sheet submission/status_sheet.pdf --output submission/AILT9019_midterm.zip --confirm-official-template --confirm-contributions
```

The confirmation flags attest that the sheet uses the official template and that names, contributions, results, and evidence are verified with no placeholders. The tool validates the MP4 container and duration, a single-page PDF, three exact ZIP entries, and a conservative **100,000,000-byte** size limit. If installed, `ffprobe` additionally validates the recording. The fallback reads the MP4 header; it cannot establish video readability or that the recording depicts a genuine run. The tool cannot verify private repository access, official-template content, student authorship, or Moodle submission. Check those manually, play the complete recording, and retain the submission receipt.

Dedicated concept-comparison pages, exercise recommendations, semantic search, accounts, public hosting, and the final website/report are outside the midterm implementation.
