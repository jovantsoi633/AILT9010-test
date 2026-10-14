"""Fill verified project facts into the supplied official status-sheet DOCX.

The template remains unchanged. Only declared text slots and creator metadata
change in the copy; all other ZIP parts are byte-for-byte preserved. The output
remains a DRAFT because member details and live validation were deferred.
Render the resulting DOCX and check one-page layout before using it.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import zipfile

from lxml import etree


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_SHA256 = "5f57af798fc8f665127840a64da7c102cd7b085bbf6d406ac56293574b369b3e"
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
CORE_NS = {"dc": "http://purl.org/dc/elements/1.1/", "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"}
EDITABLE_PARTS = {"word/document.xml", "docProps/core.xml"}
EXPECTED_HEADINGS = ["AILT9019 Midterm Status Sheet", "Current progress", "Next two weeks", "Contribution and scope"]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def text(node) -> str:
    return "".join(node.xpath(".//w:t/text()", namespaces=NS))


def read_json(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def load_facts():
    """Derive counts from reports, never from the intended implementation."""
    manifest = read_json("data/source_manifest.json")
    tests = read_json("evidence/test_summary.json")
    offline = read_json("evidence/development_offline.json")
    browser = read_json("evidence/browser_check.json")
    reproduction = read_json("evidence/reproduction_check.json")
    if offline["mode"] != "offline_development" or browser["live_ai_tested"]:
        raise ValueError("This draft text expects explicitly offline/source-search evidence.")
    if tests["live_provider_tested"] or reproduction["independent_human_first_use"]:
        raise ValueError("Evidence changed; review the draft wording before regenerating.")
    in_scope = [c for c in offline["cases"] if c["expected_status"] == "answer" and c["id"].startswith("D")]
    uncovered = [c for c in offline["cases"] if c["expected_status"] == "insufficient"]
    privacy = offline["synthetic_privacy"]
    if not all(c["api_calls"] == 0 for c in privacy):
        raise ValueError("Privacy evidence includes model calls; do not describe it as zero-call.")
    return {
        "passages": manifest["passage_count"], "tests_passed": tests["passed"], "tests_run": tests["tests_run"],
        "in_scope_passed": sum(c["required_references_retained"] for c in in_scope), "in_scope_total": len(in_scope),
        "uncovered_passed": sum(c["uncovered_filter_pass"] for c in uncovered), "uncovered_total": len(uncovered),
        "privacy_passed": sum(c["pass"] for c in privacy), "privacy_total": len(privacy),
        "video_seconds": browser["duration_seconds"], "video": browser["recorded_video"],
        "repository": reproduction["remote"], "demonstrated_commit": reproduction["commit"],
        "same_machine_reproduction_pass": reproduction["ui_start_and_search_pass"] and reproduction["corpus_and_development_hashes_match"],
        "evidence_date": datetime.fromisoformat(offline["created_at_utc"]).astimezone(timezone(timedelta(hours=8))).strftime("%d %b %Y"),
    }


def slot_values(f):
    """Each tuple is (one-based table, row, cell), matching the official form."""
    return {
        (1, 2, 1): "DRAFT: team ID and members pending",
        (1, 2, 2): "Economics with Evidence",
        (1, 2, 3): f"{f['repository']}; {f['video']} ({f['video_seconds']:g} s)",
        (2, 2, 2): (
            "No-key Source search: 'market equilibrium' -> BM25 -> 3 original passages with expandable chapter, section, PDF page and attribution. "
            f"{f['passages']} prose excerpts, Chapters 3/5. Real source-search recording: {f['video_seconds']:g} s. "
            "AI Q&A implemented; real provider validation deferred by user, not demonstrated."
        ),
        (2, 3, 2): (
            f"{f['evidence_date']}: {f['tests_passed']}/{f['tests_run']} AI-assisted automated tests. Annotated retrieval: required references "
            f"{f['in_scope_passed']}/{f['in_scope_total']}; uncovered topics {f['uncovered_passed']}/{f['uncovered_total']}; synthetic privacy "
            f"{f['privacy_passed']}/{f['privacy_total']}, 0 API calls. Logs: evidence/test_summary.json; evidence/development_offline.json. "
            f"Fresh remote checkout {f['demonstrated_commit'][:7]}: same-machine search/hash checks "
            f"{'passed' if f['same_machine_reproduction_pass'] else 'FAILED'}; independent first use pending. "
            "Limits: prose only; graphs/formulas omitted; live answer quality unverified."
        ),
        (2, 4, 2): (
            "Live API validation and member details deferred by user; no key used. "
            "Owner: [PENDING]. Next: verify names, actual contributions, course access and independent first use before 26 Oct. "
            "Final packaging waits for completed member entries and assigned owners."
        ),
        (3, 2, 1): "1. Validate real model rewrites and development answers; save outputs and human source review.",
        (3, 2, 2): "[PENDING name]",
        (3, 2, 3): "30 Oct 2026",
        (3, 3, 1): "2. Freeze 21 formal questions, reference evidence, tau and baseline conditions (Gate 3).",
        (3, 3, 2): "[PENDING name]",
        (3, 3, 3): "6 Nov 2026",
        (3, 4, 1): "3. Start one formal system/baseline run; save outputs; assign two reviewers for 9-13 Nov.",
        (3, 4, 2): "[PENDING name]",
        (3, 4, 3): "9 Nov 2026",
        **{(4, row, 2): "PENDING: user deferred names and verified work. Do not infer student contributions from AI assistance." for row in range(2, 6)},
        (4, 6, 2): "Keep: textbook search, guarded Q&A, citations, reproduction. Cut: comparison page, exercises, hosting. Escalate: [PENDING team review].",
    }


def slot_xpath(index):
    table, row, cell = index
    return f"/w:document/w:body/w:tbl[{table}]/w:tr[{row}]/w:tc[{cell}]"


def inspect_template(template, inventory_path, contract_dir):
    raw = template.read_bytes()
    if digest(raw) != TEMPLATE_SHA256:
        raise ValueError("Template checksum changed; inspect and distill it before authoring.")
    with zipfile.ZipFile(template) as archive:
        parts = {name: archive.read(name) for name in archive.namelist()}
    doc = etree.fromstring(parts["word/document.xml"])
    body = doc.find("w:body", NS)
    headings = [text(p) for p in body.findall("w:p", NS) if p.find("w:pPr/w:pStyle", NS) is not None]
    if headings != EXPECTED_HEADINGS:
        raise ValueError("Official template headings differ from the inspected contract.")
    if [len(t.findall("w:tr", NS)) for t in body.findall("w:tbl", NS)] != [2, 4, 4, 6]:
        raise ValueError("Official template table structure changed.")
    facts = load_facts()
    slots = []
    for index, replacement in slot_values(facts).items():
        xpath = slot_xpath(index)
        matches = doc.xpath(xpath, namespaces=NS)
        if len(matches) != 1 or len(matches[0].xpath(".//w:t", namespaces=NS)) != 1:
            raise ValueError(f"Editable slot is not one plain-text run: {xpath}")
        slots.append({"part": "word/document.xml", "xpath": xpath + "/w:p/w:r/w:t", "original": text(matches[0]), "replacement": replacement})
    sect = doc.xpath("//w:sectPr", namespaces=NS)
    styles = etree.fromstring(parts["word/styles.xml"])
    inventory = {
        "reference_filename": template.name, "reference_sha256": TEMPLATE_SHA256,
        "reference_pages": 1, "reference_page_count_verified_by": "Genuine Microsoft Word PDF export; complete page visually inspected",
        "render_method": "Canonical render_docx.py failed because bundled LibreOffice is absent; isolated native Word export used as actual DOCX rendering fallback, not PDF reconstruction.",
        "canonical_render_diagnostic": "tmp/official_template_renderer_diagnostic.log",
        "reference_render": "tmp/pdfs/official_template_reference.pdf",
        "reference_image": "tmp/pdfs/official_template_reference_1.png",
        "final_render_status": "PENDING native Word export and complete-page visual inspection",
        "section_count": len(sect), "section_xml": [etree.tostring(s, encoding="unicode") for s in sect],
        "headings": headings, "table_rows": [2, 4, 4, 6],
        "style_xml": {name: etree.tostring(styles.xpath(f'//w:style[@w:styleId="{name}"]', namespaces=NS)[0], encoding="unicode") for name in ("Normal", "Title", "Heading1", "TableGrid")},
        "feature_counts": {"content_controls": len(doc.xpath("//w:sdt", namespaces=NS)), "fields": len(doc.xpath("//w:fldSimple|//w:fldChar", namespaces=NS)), "drawings": len(doc.xpath("//w:drawing", namespaces=NS)), "bookmarks": len(doc.xpath("//w:bookmarkStart", namespaces=NS))},
        "parts": [{"path": name, "bytes": len(content), "sha256": digest(content), "policy": "slot_text_only" if name == "word/document.xml" else "clear_creator_and_lastModifiedBy_only" if name == "docProps/core.xml" else "preserve_bytes"} for name, content in parts.items()],
        "slots": slots, "facts": facts,
        "draft_reasons": ["Real member names/contributions and milestone owners deferred by user", "Live API validation deferred by user", "Independent human/computer reproduction pending"],
    }
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    inventory_path.write_text(json.dumps(inventory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    contract_dir.mkdir(parents=True, exist_ok=True)
    contract = f"""# Official status sheet execution contract

Reference: `{template.resolve()}`. SHA-256 `{TEMPLATE_SHA256}`; original is read-only and must remain unchanged. Full inventory: `{inventory_path.resolve()}`.

Reference is one US Letter portrait page, one section, four tables; verified by genuine Word export at `tmp/pdfs/official_template_reference.pdf` and whole-page PNG inspection. Canonical renderer failed with missing soffice; no installed desktop LibreOffice is used. Final native Word export and PNG review are mandatory before delivery.

Page geometry: 12240 x 15840 twips; margins top 1037, right/left 1123, bottom 965; header/footer 720; one column. Preserve complete sectPr.

Typography: source Title (18 pt bold, black), Normal (Aptos 9.5 pt, color19202A, after100 twips, line259 auto), Heading1 (Aptos10.5 pt bold, color173753, before160/after60 twips, keepNext/keepLines). Tables retain source TableGrid, grid widths, vertical centering, header fill EAF0F5, borders, direct run size17 half-points and paragraph spacing20/20. Member right cells use original inherited formatting. No font shrinking or generic design preset.

Ordered content: official title/instructions, metadata table, Current progress table, Next two weeks table, Contribution and scope table. Preserve source headings, instructions, labels, optional fourth-member row, table/paragraph counts, and all chrome.

Slot map: replace exactly the 20 plain-text cells listed under slots in inventory. Shorten text if needed for one page; do not alter table geometry/styles. Team cell visibly marks DRAFT. Member/owner fields stay PENDING rather than invented. No student count is inferred from the retained template's four rows.

Package preservation: only word/document.xml text nodes and creator/lastModifiedBy in docProps/core.xml may change. All other parts, including customXml, relationships, styles, numbering and thumbnail, remain byte-identical. No fields, controls, drawings, bookmarks, headers or footers require updates. Validate source and final XML with all w:t text blanked; the resulting trees must match.

Fidelity gates: same section geometry and headings/table counts; byte-preserved opaque parts; blank output creator/lastModifiedBy; unchanged reference hash; genuine output DOCX render exactly one page; no clipping/overlap/unreadable text in every final PNG. No final ZIP while contributions/owners remain pending.
"""
    (contract_dir / "artifact.md").write_text(contract, encoding="utf-8")
    return parts, doc, inventory


def fill(template, output, inventory_path, contract_dir):
    output = output.resolve()
    parts, doc, inventory = inspect_template(template, inventory_path, contract_dir)
    before = deepcopy(doc)
    for slot in inventory["slots"]:
        node = doc.xpath(slot["xpath"], namespaces=NS)[0]
        node.text = slot["replacement"]
    after_without_text = deepcopy(doc)
    for tree in (before, after_without_text):
        for node in tree.xpath("//w:t", namespaces=NS):
            node.text = ""
    if etree.tostring(before) != etree.tostring(after_without_text):
        raise ValueError("Unexpected template structure change.")
    core = etree.fromstring(parts["docProps/core.xml"])
    for xpath in ("dc:creator", "cp:lastModifiedBy"):
        for node in core.findall(xpath, CORE_NS):
            node.text = ""
    modified = {"word/document.xml": etree.tostring(doc, xml_declaration=True, encoding="UTF-8", standalone=True), "docProps/core.xml": etree.tostring(core, xml_declaration=True, encoding="UTF-8", standalone=True)}
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.resolve() == template.resolve():
        raise ValueError("Output must never replace the retained reference.")
    with zipfile.ZipFile(template) as original, zipfile.ZipFile(output, "w") as target:
        for info in original.infolist():
            target.writestr(info, modified.get(info.filename, parts[info.filename]))
    with zipfile.ZipFile(output) as final:
        if set(final.namelist()) != set(parts):
            raise ValueError("Output package part inventory changed.")
        for name, content in parts.items():
            if name not in EDITABLE_PARTS and final.read(name) != content:
                raise ValueError(f"Preserve-only part changed: {name}")
        inventory["output_sha256"] = digest(output.read_bytes())
        inventory["changed_parts"] = [name for name in parts if final.read(name) != parts[name]]
        inventory["preserve_only_parts_identical"] = True
        inventory["source_still_unchanged"] = digest(template.read_bytes()) == TEMPLATE_SHA256
        inventory["output_creator_metadata_blank"] = all(not (node.text or "").strip() for path in ("dc:creator", "cp:lastModifiedBy") for node in core.findall(path, CORE_NS))
    inventory["output_relative"] = output.relative_to(ROOT).as_posix() if output.is_relative_to(ROOT) else output.name
    inventory_path.write_text(json.dumps(inventory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return inventory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "output/docx/AILT9019_midterm_status_draft.docx")
    parser.add_argument("--inventory", type=Path, default=ROOT / "evidence/official_template_inventory.json")
    parser.add_argument("--contract-dir", type=Path, default=ROOT / "tmp/status_template")
    parser.add_argument("--inspect-only", action="store_true")
    args = parser.parse_args()
    if args.inspect_only:
        _, _, inventory = inspect_template(args.template, args.inventory, args.contract_dir)
    else:
        inventory = fill(args.template, args.output, args.inventory, args.contract_dir)
    print(json.dumps({"draft": True, "slots": len(inventory["slots"]), "output": None if args.inspect_only else str(args.output), "inventory": str(args.inventory), "render_status": inventory["final_render_status"]}, indent=2))


if __name__ == "__main__":
    main()
