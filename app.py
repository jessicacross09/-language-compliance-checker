import streamlit as st
import os
import re
import pandas as pd
from io import StringIO
from docx import Document
import fitz  # PyMuPDF
from pptx import Presentation
import spacy

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

# --- Streamlit Config ---
st.set_page_config(page_title="APEC-RISE Text Harmonization Tool", layout="wide")
st.markdown("## APEC-RISE Text Harmonization Tool")
st.markdown("""
This tool scans uploaded documents for non-compliant language and provides recommended alternatives aligned with APEC-RISE communication guidance.
""")

# --- Banned Terms Dictionary ---
banned_terms_dict = {
    "accessible": ["reachable; usable; broadly available"],
    "activism": ["Stakeholder engagement; issue-focused participation"],
    "anti-racism": ["addressing discrimination"],
    "bias": ["subjective influence"],
    "clean energy": ["energy diversification; secure energy sourcing"],
    "climate change": ["environmental shifts"],
    "climate crisis": ["environmental conditions; weather-related impacts"],
    "climate science": ["environmental data"],
    "country": ["economy"],
    "DEI": ["broad participation; inclusive stakeholder engagement"],
    "DEIA": ["broad participation; inclusive stakeholder engagement"],
    "disability": ["persons with disabilities"],
    "diverse": ["varied"],
    "diverse backgrounds": ["varied experiences"],
    "diverse communities": ["different population groups"],
    "diverse community": ["broad-based community"],
    "diverse group": ["multifaceted group"],
    "diverse groups": ["multiple stakeholder groups"],
    "diversified": ["varied"],
    "diversify": ["broaden"],
    "diversifying": ["expanding"],
    "diversity": ["variety"],
    "equal opportunity": ["merit-based opportunity; fair process"],
    "equity": ["fair access"],
    "gender": ["demographics"],
    "gender mainstreaming": ["gender considerations"],
    "gender-responsive": ["inclusive of gender perspectives"],
    "Gulf of Mexico": ["Gulf of America"],
    "inclusion": ["broad-based participation"],
    "inclusive": ["participatory"],
    "inclusive leadership": ["broad-based leadership"],
    "inclusiveness": ["broad engagement"],
    "inclusivity": ["collaborative approaches"],
    "inequality": ["gaps in access or opportunity"],
    "national": ["domestic"],
    "non-binary": ["gender-diverse"],
    "nonbinary": ["gender-diverse"],
    "oppression": ["restrictive conditions; limiting environments"],
    "oppressive": ["restrictive; limiting"],
    "social justice": ["fair policy outcomes; community fairness"],
    "socioeconomic": ["economic background; living conditions"],
    "Taiwan": ["Chinese Taipei"],
    "victim": ["impacted individual; affected party"],
    "vulnerable populations": ["underrepresented stakeholders"]
}

# --- Named Entity Exception ---
def is_named_entity(snippet: str, term: str):
    doc = nlp(snippet)
    for ent in doc.ents:
        if term.lower() in ent.text.lower() and ent.label_ == "ORG":
            return True
    return False

# --- File Readers ---
def read_docx(file):
    doc = Document(file)
    return "\n".join([para.text for para in doc.paragraphs])

def read_txt(file):
    return StringIO(file.getvalue().decode("utf-8")).read()

def read_pptx(file):
    prs = Presentation(file)
    text_runs = []
    for slide_num, slide in enumerate(prs.slides, start=1):
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                text_runs.append(f"[Slide {slide_num}] {shape.text}")
    return "\n".join(text_runs)

# --- Scan Functions ---
def scan_text(text, banned_dict, chars_per_page=1800):
    results, skipped = [], []
    for term, suggestions in banned_dict.items():
        pattern = re.compile(rf"\b({re.escape(term)})\b", re.IGNORECASE)
        for match in pattern.finditer(text):
            start = match.start()
            estimated_page = max(1, (start // chars_per_page) + 1)
            snippet = text[max(0, start - 40): min(len(text), start + 60)].replace('\n', ' ')
            if term.lower() in ["national", "taiwan"] and is_named_entity(snippet, term):
                skipped.append({"Skipped Term": match.group(), "Page": estimated_page, "Context": f"...{snippet.strip()}..."})
                continue
            results.append({
                "Banned Term": match.group(),
                "Page": estimated_page,
                "Context": f"...{snippet.strip()}...",
                "Suggested Replacement(s)": ", ".join(suggestions)
            })
    return results, skipped

def scan_pdf(file, banned_dict):
    results, skipped = [], []
    doc = fitz.open(stream=file.read(), filetype="pdf")
    for page_number, page in enumerate(doc, start=1):
        text = page.get_text()
        for term, suggestions in banned_dict.items():
            pattern = re.compile(rf"\b({re.escape(term)})\b", re.IGNORECASE)
            for match in pattern.finditer(text):
                snippet = text[max(0, match.start() - 40): min(len(text), match.end() + 60)].replace('\n', ' ')
                if term.lower() in ["national", "taiwan"] and is_named_entity(snippet, term):
                    skipped.append({"Skipped Term": match.group(), "Page": page_number, "Context": f"...{snippet.strip()}..."})
                    continue
                results.append({
                    "Banned Term": match.group(),
                    "Page": page_number,
                    "Context": f"...{snippet.strip()}...",
                    "Suggested Replacement(s)": ", ".join(suggestions)
                })
    return results, skipped

# --- Tabs ---
tab1, tab2 = st.tabs(["Upload Document", "View Banned Terms"])

with tab1:
    uploaded_file = st.file_uploader("Upload a .pdf, .docx, .txt, or .pptx file", type=["pdf", "docx", "txt", "pptx"])
    if uploaded_file:
        findings, skipped = [], []
        raw_text = ""
        try:
            if uploaded_file.name.endswith(".pdf"):
                findings, skipped = scan_pdf(uploaded_file, banned_terms_dict)
            elif uploaded_file.name.endswith(".docx"):
                raw_text = read_docx(uploaded_file)
                findings, skipped = scan_text(raw_text, banned_terms_dict)
            elif uploaded_file.name.endswith(".txt"):
                raw_text = read_txt(uploaded_file)
                findings, skipped = scan_text(raw_text, banned_terms_dict)
            elif uploaded_file.name.endswith(".pptx"):
                raw_text = read_pptx(uploaded_file)
                findings, skipped = scan_text(raw_text, banned_terms_dict)
        except Exception as e:
            st.error(f"Error reading file: {e}")

        if findings:
            df = pd.DataFrame(findings)
            st.markdown("### Summary Statistics")
            st.metric("Total Banned Terms Flagged", len(df))
            st.metric("Unique Terms Found", df['Banned Term'].nunique())
            st.dataframe(df)

            if raw_text:
                for term in df["Banned Term"].unique():
                    raw_text = re.sub(rf"\b({re.escape(term)})\b", r"**\1**", raw_text, flags=re.IGNORECASE)
                st.markdown("### Highlighted Text Preview")
                st.markdown(f"<div style='white-space: pre-wrap'>{raw_text}</div>", unsafe_allow_html=True)

        if skipped:
            st.markdown("### Skipped Terms (Named Entities in Organization Names)")
            st.dataframe(pd.DataFrame(skipped), use_container_width=True)

with tab2:
    st.markdown("### Banned Terms and Suggested Replacements")
    banned_df = pd.DataFrame([
        {"Banned Term": term, "Suggested Replacement(s)": ", ".join(suggestions)}
        for term, suggestions in banned_terms_dict.items()
    ])
    st.dataframe(banned_df, use_container_width=True)
