# Textbook source, attribution, and rebuild

The application ships **203 original prose excerpts** (17,486 words) from the pinned
OpenStax *Principles of Economics 2e* PDF. An LLM did not write, summarize, translate,
or repair these excerpts. The preprocessed corpus is sufficient to run the app;
downloading the full textbook is only necessary to rebuild or audit it.

## Source identity

- Senior contributing authors: Steven A. Greenlaw and David Shapiro; publisher:
  OpenStax, Rice University. These names are on PDF page 3.
- [Pinned PDF](https://d3bxy9euw4e147.cloudfront.net/oscms-prodcms/media/documents/Economics2e-LR.pdf):
  974 file pages, 18,214,074 bytes, SHA-256
  `4294836051532268aa0ffd3f2926db9b1b9e620fad415f73d3941265d063feca`.
- Copyright page: **PDF page 4**, no printed page number. It states **©2018 Rice
  University**, **CC BY 4.0**, revision **PE2-2017-002-(03/18)-LC**, PDF ISBN
  **978-1-947172-37-1**, and original publication year **2017**. The copyright year,
  revision date and first publication year are different fields.
- The original [2e book details URL](https://openstax.org/details/books/principles-economics-2e)
  redirected to the 3e page when checked on 2026-10-15. The app uses the pinned 2e
  PDF, not the redirected edition or today's website text.
- Verified on 2026-10-15 by inspecting copyright and author pages and the visual
  layout of the key evidence pages. Machine-readable metadata is in
  `data/source_manifest.json`.

## Exact scope and page numbering

| Included original prose | One-based PDF pages | Printed pages |
| --- | --- | --- |
| Chapter 3, sections 3.1–3.5, Demand and Supply | 56–84 | 46–74 |
| Chapter 5, sections 5.1–5.4, Elasticity | 118–136 | 108–126 |

The corpus retains normal body paragraphs and explanatory feature-box prose.
It excludes the chapter introductions before sections 3.1/5.1, learning objectives,
chapter-end key terms, summaries, questions and exercises, external-link panels,
page headers/footers, diagrams, figure captions, tables, displayed equations and
paragraphs containing embedded equation glyphs. Short fragments are omitted.
No cover, logo or trademark image is reproduced.

This is a **prose excerpt corpus**, not a complete digital edition of both chapters.
Some retained paragraphs refer to figures, formulas or tables that are not included.
Questions requiring these materials or numerical calculations can have insufficient
evidence. Historical examples keep the source's 2018 context; they are not claims
about current conditions.

`pdf_page` is always the **one-based page in the actual PDF file**. `printed_page`
is the page number printed in its header. For these sections, printed = PDF − 10.
Paragraphs continuing onto the next PDF page retain the original text as one passage
and have `pdf_page_end` and `printed_page_end`. Citation links must use `pdf_page`,
not the printed page, in the PDF `#page=` fragment.

## Attribution and permitted modifications

The copyright page requires this line in every digital page view containing an
excerpt:

> Download for free at https://openstax.org/details/books/principles-economics-2e.

The application must show the full attribution stored in each passage, including
the authors, copyright, [CC BY 4.0 license](https://creativecommons.org/licenses/by/4.0/),
and required download line. Chapter 3's upstream credit to Steve Greenlaw and
Lumen Learning is retained. The app's code license does not replace this textbook
license, and the OpenStax/Rice trademark images are outside the textbook license.

Modifications are limited to joining visual PDF lines and normalizing whitespace;
printed line-end hyphens are retained and joined directly to the next line.
Subscript/superscript numbers are represented as ordinary text (for example `D0`).
Exclusions and modifications are disclosed in the manifest and passage attribution.
Source typos, dated examples, duplicate wording and grammar are intentionally not
silently corrected.

## Rebuild and audit

Use Python 3.11 or newer with `pdfplumber==0.11.10` (the extraction dependency is
pinned in the project requirements). The build records the installed extractor
version programmatically in the source manifest. Store the downloaded PDF at
`data/source/Economics2e-LR.pdf`. The source PDF is gitignored; it is not necessary
for app installation and is not part of the midterm submission ZIP.

```powershell
python scripts/build_corpus.py
python scripts/build_corpus.py --check
python -m unittest discover -s tests -p test_corpus.py -v
```

The script refuses a missing PDF, a different checksum, or an unexpected copyright
or edition marker before writing the corpus. It does not download files or contact
an API. `--check` recomputes the entire corpus and manifest without writing them.
Its extraction settings are pinned: `x_tolerance=1`, `y_tolerance=5`. The latter is
necessary to keep subscript numbers on the same text line; the library's default
settings damage justified spaces or split mathematical labels into fragments.

Paragraph boundaries come from visual line gaps of at least five points, headings
and layout/font-category changes. Unfinished paragraphs join only across adjacent
pages in the same section and text category. IDs use chapter, section, starting PDF
page and paragraph ordinal; IDs stay stable when rebuilding this source with these
settings. Changing the source or segmentation is a corpus version change and can
require updating evaluation references and recalibrating the relevance threshold.

Each passage stores the original extracted `source_spans` (PDF page, vertical
coordinates and line text), its normalized text and a text SHA-256. Tests compare
every passage to its stored original lines and check a full deterministic rebuild
against the source PDF when it is locally available. Without the optional PDF,
that one audit test is explicitly skipped; the remaining corpus checks still run.

## Development reference passages

| Concept | Passage ID | Chapter / section | PDF / printed page |
| --- | --- | --- | --- |
| Demand versus quantity demanded | `ch3-s3-1-p058-02` | 3 / 3.1 | 58 / 48 |
| Shortage and upward price adjustment | `ch3-s3-1-p061-08` | 3 / 3.1 | 61 / 51 |
| Price elasticity definition | `ch5-s5-1-p118-01` | 5 / 5.1 | 118 / 108 |
| Elasticity and total revenue | `ch5-s5-3-p127-02` | 5 / 5.3 | 127 / 117 |

The development topics unemployment rate, GDP deflator and fractional reserve
banking have no direct definitional evidence in this corpus. An absence-of-phrase
test checks that the source data has not accidentally expanded to those chapters;
it does not prove that every possible model rewrite will retrieve no passage.
