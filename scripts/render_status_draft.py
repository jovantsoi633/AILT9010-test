"""Render a one-page working draft. This does not replace the Moodle template."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether

ROOT = Path(__file__).resolve().parents[1]


def main():
    evidence = json.loads((ROOT / "evidence/development_offline.json").read_text(encoding="utf-8"))
    corpus = json.loads((ROOT / "data/source_manifest.json").read_text(encoding="utf-8"))
    date = datetime.fromisoformat(evidence["created_at_utc"]).astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d (Asia/Shanghai)")
    output = ROOT / "output/pdf/midterm_status_draft.pdf"
    output.parent.mkdir(parents=True, exist_ok=True)
    normal = ParagraphStyle("body", fontName="Helvetica", fontSize=9, leading=12, textColor=colors.HexColor("#192D29"), spaceAfter=6)
    head = ParagraphStyle("head", parent=normal, fontName="Helvetica-Bold", fontSize=10, spaceBefore=7, spaceAfter=4)
    title = ParagraphStyle("title", parent=head, fontSize=18, leading=22)
    small = ParagraphStyle("small", parent=normal, fontSize=8, leading=10)
    story = []
    def p(text, style=normal):
        return Paragraph(text, style)
    def section(label, text):
        story.append(KeepTogether([p(label, head), p(text)]))
    story.extend([p("AILT9019 Midterm Status", title),
                  p("WORKING DRAFT - NOT THE OFFICIAL MOODLE TEMPLATE", head),
                  p(f"Evidence date: {date}. Team and member details: PENDING. Deadline: 26 October 2026; verify exact Moodle cutoff.", small),
                  p('Repository: <link href="https://github.com/jovantsoi633/AILT9010-test" color="#177A68">github.com/jovantsoi633/AILT9010-test</link>. Supplied repository is public; course access and demonstrated commit must be checked.', small)])
    section("Working now", f"English local Streamlit application. {corpus['passage_count']} source paragraphs from OpenStax Principles of Economics 2e, copyright 2018, Chapters 3 and 5. Verified no-key chapter-filtered search and source inspection. Implemented guarded two-call AI pipeline and citation validation; real-provider QA remains UNVERIFIED without a key.")
    in_scope = [r for r in evidence["cases"] if r["expected_status"] == "answer"]
    outside = [r for r in evidence["cases"] if r["expected_status"] == "insufficient"]
    hits = sum(r["reference_retrieval_hit"] and r["required_references_retained"] for r in in_scope)
    abstains = sum(r["uncovered_filter_pass"] for r in outside)
    pii = sum(r["pass"] for r in evidence["synthetic_privacy"])
    section("Evidence and limitations", f"Annotated-keyword development checks: required evidence retained in {hits}/{len(in_scope)} in-scope cases; no passages retained in {abstains}/{len(outside)} uncovered cases. Synthetic privacy inputs: {pii}/3 blocked with zero client requests. Evidence: evidence/development_offline.json and evidence/calibration.json. Real browser source-search evidence: evidence/browser_check.json. These are offline checks, not live AI accuracy. Graphs, tables and equation-bearing paragraphs are omitted. Citation labels do not prove factual support. Independent first-use and two-person answer review are PENDING.")
    section("Blockers and next steps", "Real API validation: AI/testing owner PENDING - run the development evaluator with a privately entered key and review actual rewrites and answers. Official companion template: submission owner PENDING - obtain it from Moodle. Named owners, genuine member contributions, and independent first-use: team details deferred by user; record before submission. No final ZIP is ready for Moodle.")
    story.append(p("Next two weeks", head))
    rows = [[p("Due", small), p("Owner", small), p("Completion check", small)],
            [p("30 Oct", small), p("AI/testing member<br/>PENDING", small), p("Evaluator saves real development outputs and checks retrieval, refusals and insufficient evidence.", small)],
            [p("6 Nov", small), p("Textbook/testing member<br/>PENDING", small), p("Freeze 21 formal questions, source evidence, threshold and baseline conditions (Gate 3).", small)],
            [p("9 Nov", small), p("Evaluation coordinator<br/>PENDING", small), p("Start the one-time formal system/baseline evaluation; assign two independent reviewers for 9-13 Nov.", small)]]
    table = Table(rows, colWidths=[18*mm, 39*mm, 116*mm])
    table.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#EDF2EC")),
                               ("GRID", (0,0), (-1,-1), .4, colors.HexColor("#CAD5CF")),
                               ("VALIGN", (0,0), (-1,-1), "TOP"), ("LEFTPADDING", (0,0), (-1,-1), 6),
                               ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5)]))
    story.append(table)
    section("Contribution and scope", "Member contributions: PENDING - each real member must list specific completed work and a verifiable artifact. AI-authored files do not establish student contributions. Keep source search, guarded QA, citations and reproducibility. Defer dedicated comparison UI and exercise recommendations. Do not add semantic retrieval, accounts or public application hosting.")
    story.append(p("Transfer verified content into the official one-page template. The formal 21-question evaluation has not been run.", small))
    doc = SimpleDocTemplate(str(output), pagesize=A4, rightMargin=18*mm, leftMargin=18*mm,
                            topMargin=14*mm, bottomMargin=14*mm,
                            title="AILT9019 Midterm Status - Working Draft", author="", subject="Unverified fields remain pending; not for submission")
    doc.build(story)
    print(output)


if __name__ == "__main__":
    main()
