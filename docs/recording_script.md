# Genuine midterm recording script

Target: a readable **≤60-second MP4** showing the exact repository version to be submitted. The preferred recording demonstrates real AI Q&A; it requires a functioning model connection. A real source-search recording is useful backup evidence but does not establish live Q&A.

**Current evidence:** `evidence/source_search_demo.mp4` is a genuine, captioned **27.2-second Source search** recording. It shows `market equilibrium`, BM25 results and expanded textbook evidence, with zero model requests. See `evidence/browser_check.json`. Live Q&A is deferred by the user; the live script below is for a later validated run.

## Before recording

1. Run the app and validate the chosen question against the actual source. Test latency before recording.
2. Configure the API key before capture; keep it masked and out of developer tools, logs, notifications, and browser history. Use synthetic information only.
3. Select the demand and supply chapter. Set browser zoom for readable text and sources; hide unrelated windows.
4. Record the app version, provider/model, timestamp, actual API-call count, and observed latency in the evidence record. Do not add an answer that was not returned in the recorded run.

## Preferred live Q&A take

| Time | Screen action | Caption or narration |
|---|---|---|
| 0–10 s | Show title and chapter; type the question below and submit. | “English concept question, limited to the selected textbook chapter.” |
| 10–35 s | Show the actual request-check, retrieval, and answer process. | “The question is checked, rewritten for retrieval, and answered from selected textbook excerpts.” |
| 35–50 s | Expand a cited excerpt; show paragraph ID, chapter, section, and PDF page. | “Open the citation to compare the explanation with the original source.” |
| 50–60 s | Keep source and answer visible. | “Current coverage: demand and supply, and elasticity. Answers need source checking.” |

**Question:**

> When a product's own price rises and people buy less, is that a change in demand or quantity demanded?

Use the returned answer verbatim in evidence. Expected concept: an own-price change affects quantity demanded along a demand curve; another determinant can shift demand. Check that the returned text and selected paragraph actually support this distinction.

If the real response is too slow, shorten answer length and retry with a fresh real run. Do not hide a failed request, substitute a prewritten answer, or describe an offline response as live. Report persistent latency or connection failure as a blocker. Use captions if recording has no narration.

## Honest source-search backup

With **Source search** selected and no key, type `market equilibrium`, run the search, and expand a returned paragraph. Show chapter, section, PDF page, and attribution. Caption: “Local source search; zero model requests. Live Q&A validation is pending.” If live validation has since succeeded, use its actual status instead. This backup is evidence of the source-search path, not the full two-call Q&A path.

## Review and export

- Play the entire exported MP4; ensure duration is greater than zero and ≤60 seconds and text is readable.
- Confirm the input, processing, output, and expanded source can be followed; captions must describe the actual run.
- Confirm keys and personal information are absent. Retain the recording's original file and evidence metadata.
- Put the chosen final recording in `submission/video.mp4` only after human review. Run the packaging validator with the completed status PDF and real repository URL.
