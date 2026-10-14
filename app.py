"""Local English textbook learning assistant. Never cache API clients or keys."""
from __future__ import annotations

import json
import re
import hashlib
from pathlib import Path

import streamlit as st

from econ_assistant.api import APIConfig, OpenAICompatibleClient
from econ_assistant.models import load_passages
from econ_assistant.pipeline import Pipeline
from econ_assistant.retrieval import BM25Retriever

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="Economics with Evidence", page_icon="📖", layout="wide")


@st.cache_resource
def resources():
    passages = load_passages(ROOT / "data" / "passages.jsonl")
    settings = json.loads((ROOT / "data" / "retrieval_config.json").read_text(encoding="utf-8"))
    if settings.get("corpus_sha256") != hashlib.sha256((ROOT / "data/passages.jsonl").read_bytes()).hexdigest():
        raise ValueError("Recalibrate the threshold after changing the corpus.")
    return BM25Retriever(passages), settings


def clear_result():
    st.session_state.pop("last_run", None)
    st.session_state.pop("citation_choice", None)


def set_example(text):
    st.session_state["question"] = text
    clear_result()


def clear_key():
    st.session_state["api_key"] = ""
    clear_result()


def source_heading(hit, label):
    p = hit.passage
    return f"{label} · {p.section} {p.section_title} · PDF page {p.pdf_page}"


def render_source(hit, label, expanded=False):
    p = hit.passage
    st.markdown(f'<div id="source-{label.lower()}"></div>', unsafe_allow_html=True)
    with st.expander(source_heading(hit, label), expanded=expanded):
        st.caption(f"Chapter {p.chapter}: {p.chapter_title} · Section {p.section}")
        st.write(p.text)
        pages = str(p.pdf_page)
        end = getattr(p, "pdf_page_end", None)
        if end and end != p.pdf_page:
            pages += f"–{end}"
        st.caption(f"PDF file page: {pages} · Printed textbook page: {p.printed_page} · Passage: {p.id}")
        st.markdown(f"[Open the source PDF at this page]({p.source}#page={p.pdf_page})")
        st.caption(p.attribution)


try:
    retriever, settings = resources()
except (OSError, ValueError, KeyError) as exc:
    st.error("The prepared textbook data is missing or invalid. Follow the data setup steps in the README.")
    st.stop()

with st.sidebar:
    st.markdown("### Your textbook")
    st.caption("OpenStax · Principles of Economics 2e · ©2018 Rice University")
    chapter_option = st.selectbox(
        "Search within",
        ["All included chapters", "3 · Demand and Supply", "5 · Elasticity"],
        key="chapter_choice", on_change=clear_result,
    )
    chapter = None if chapter_option.startswith("All") else chapter_option.split(" · ")[0]
    st.caption("This edition includes the prose of Chapters 3 and 5. Diagrams are not interpreted.")
    with st.expander("AI connection"):
        st.text_input("API key", type="password", key="api_key", help="Kept only in this browser session. Never saved or logged.")
        st.text_input("Base URL", value="https://api.deepseek.com", key="base_url")
        st.text_input("Model", value="deepseek-flash", key="model_name")
        st.button("Clear API key", on_click=clear_key, use_container_width=True)
        st.caption("Use your own key. AI Q&A needs internet access and may incur provider charges.")
        st.markdown("[Get a DeepSeek key](https://platform.deepseek.com/) · [Current model names](https://api-docs.deepseek.com/quick_start/pricing/)")
    st.divider()
    st.caption("For understanding concepts. Financial advice, market predictions, assignment writing and grading are outside this tool's scope.")

st.caption("A TEXTBOOK LEARNING COMPANION")
st.title("Economics, with evidence.")
st.write("Explore supply, demand and elasticity. Read the textbook passages behind each explanation.")
mode = st.radio("Choose a learning mode", ["Source search", "AI Q&A"], horizontal=True,
                key="mode", on_change=clear_result)

if mode == "Source search":
    st.info("Search English terms or short phrases. This mode uses the local textbook and makes no model requests.")
    examples = ["market equilibrium", "quantity demanded", "price elasticity total revenue"]
else:
    st.info("AI Q&A sends your question, then the selected textbook passages, to the configured model provider. Do not enter personal information.")
    examples = ["What is the difference between demand and quantity demanded?",
                "Why does a shortage put upward pressure on price?",
                "How does raising price affect total revenue when demand is elastic?"]

columns = st.columns(3)
for column, example in zip(columns, examples):
    column.button(example, on_click=set_example, args=(example,), use_container_width=True)

with st.form("question_form"):
    st.text_area("English keywords" if mode == "Source search" else "Your question in English",
                 key="question", height=105,
                 placeholder="market equilibrium" if mode == "Source search" else "Ask about a concept in the included chapters…")
    submitted = st.form_submit_button("Find passages" if mode == "Source search" else "Explain with evidence", type="primary")

if submitted:
    clear_result()
    question = st.session_state.get("question", "").strip()
    if not question:
        st.warning("Enter a question or a textbook term first.")
    elif len(question) > 1500:
        st.warning("Keep your question under 1,500 characters.")
    elif re.search(r"[\u3400-\u9fff]", question):
        st.warning("This prototype supports English. Please ask your question in English.")
    elif mode == "Source search":
        with st.spinner("Finding passages in your selected chapters…"):
            hits = retriever.search(question, chapter=chapter, top_k=3)
        st.session_state["last_run"] = {"mode": mode, "hits": hits, "scope": chapter_option}
    elif not st.session_state.get("api_key", "").strip():
        st.warning("Enter an API key under AI connection to use AI Q&A. Source search is available without a key.")
    else:
        try:
            config = APIConfig(api_key=st.session_state["api_key"].strip(),
                               base_url=st.session_state["base_url"].strip(),
                               model=st.session_state["model_name"].strip())
            client = OpenAICompatibleClient(config)
            with st.status("Checking your question and finding textbook evidence…", expanded=True) as progress:
                result = Pipeline(retriever, client, tau=settings["tau"]).run(question, chapter=chapter)
                for stage in result.stages:
                    st.write(stage)
                progress.update(label="Explanation ready" if result.status == "answer" else "Request checked", state="complete")
            st.session_state["last_run"] = {"mode": mode, "result": result, "scope": chapter_option}
        except ValueError:
            st.error("Check your connection settings. Use an HTTPS base URL, a model name and an API key.")

last_run = st.session_state.get("last_run")
if last_run:
    st.divider()
    st.caption(f"Search scope: {last_run['scope']}")
    if last_run["mode"] == "Source search":
        hits = last_run["hits"]
        if not hits or all(h.score <= 0 for h in hits):
            st.warning("No matching textbook terms were found. Try a shorter English phrase or another included chapter.")
        else:
            hits = [h for h in hits if h.score > 0]
            st.subheader("Read the source")
            st.caption(f"{len(hits)} ranked passages · No AI-generated explanation · 0 model requests")
            for i, hit in enumerate(hits, 1):
                render_source(hit, f"P{i}", expanded=i == 1)
    else:
        result = last_run["result"]
        if result.status == "answer":
            st.subheader("Textbook-based explanation")
            st.caption("AI-generated · Verify the explanation against its sources")
            answer = re.sub(r"\[(P[1-3])\]", lambda m: f"[{m.group(1)}](#source-{m.group(1).lower()})", result.answer)
            st.markdown(answer)
            labels = [f"P{i}" for i in range(1, len(result.hits) + 1)]
            selected = st.pills("Open a cited passage", labels, key="citation_choice")
            for label, hit in zip(labels, result.hits):
                render_source(hit, label, expanded=selected == label)
        elif result.status in ("pii", "refused", "insufficient", "input_error"):
            st.warning(result.message)
        else:
            st.error(result.message)
        with st.expander("Run details"):
            st.write(f"Result: {result.status} · Model requests: {result.api_calls}")
            if result.rewritten_query:
                st.write(f"Textbook search terms: {result.rewritten_query}")
            st.caption("The source passages support inspection; citations alone do not guarantee that an answer is correct.")
            if settings.get("calibration_status") == "provisional_annotated":
                st.caption("Prototype: relevance filtering is provisionally calibrated on annotated development keywords. Live rewrite validation is still required.")

st.divider()
st.caption("OpenStax, Principles of Economics 2e, ©2018 Rice University. Textbook excerpts licensed CC BY 4.0. Whitespace normalized; excerpt wording retained.")
st.markdown("Download for free at https://openstax.org/details/books/principles-economics-2e.")
