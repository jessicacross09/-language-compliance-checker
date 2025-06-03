import streamlit as st
import os
import re
import pandas as pd
from io import StringIO
from docx import Document
import fitz  # PyMuPDF
from pptx import Presentation

# --- Streamlit Config ---
st.set_page_config(page_title="APEC-RISE Text Harmonization Tool", layout="wide")

st.markdown("## 📝 APEC-RISE Text Harmonization Tool")
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
    "equal opportunity": ["nerit-based opportunity; fair process"],
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

def scan_pdf(file, banned_dict):
    results = []
    doc = fitz.open(stream=file.read(), filetype="pdf")
    for page_number, page in enumerate(doc, start=1):
        text = page.get_text()
        for term, suggestions in banned_dict.items():
            pattern = re.compile(rf"\b({re.escape(term)})\b", re.IGNORECASE)
            for match in pattern.finditer(text):
                snippet = text[max(0, match.start() - 40): min(len(text), match.end() + 60)].replace('\n', ' ')
                results.append({
                    "Banned Term": match.group(),
                    "Page": page_number,
                    "Context": f"...{snippet.strip()}...",
                    "Suggested Replacement(s)": ", ".join(suggestions)
                })
    return results

def scan_text(text, banned_dict, chars_per_page=1800):
    results = []
    for term, suggestions in banned_dict.items():
        pattern = re.compile(rf"\b({re.escape(term)})\b", re.IGNORECASE)
        for match in pattern.finditer(text):
            start = match.start()
            estimated_page = max(1, (start // chars_per_page) + 1)
            snippet = text[max(0, start - 40): min(len(text), start + 60)].replace('\n', ' ')
            results.append({
                "Banned Term": match.group(),
                "Page": estimated_page,
                "Context": f"...{snippet.strip()}...",
                "Suggested Replacement(s)": ", ".join(suggestions)
            })
    return results

# --- Tabs for Upload and Dictionary View ---
tab1, tab2 = st.tabs(["📤 Upload Document", "📘 View Banned Terms"])

with tab1:
    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded_file = st.file_uploader("Upload a .pdf, .docx, .txt, or .pptx file", type=["pdf", "docx", "txt", "pptx"])
    with col2:
        st.info("Once uploaded, the file will be scanned for banned terms. Flagged terms and recommended alternatives will appear below.")

    if uploaded_file:
        findings = []
        try:
            if uploaded_file.name.endswith(".pdf"):
                findings = scan_pdf(uploaded_file, banned_terms_dict)
            elif uploaded_file.name.endswith(".docx"):
                text = read_docx(uploaded_file)
                findings = scan_text(text, banned_terms_dict)
            elif uploaded_file.name.endswith(".txt"):
                text = read_txt(uploaded_file)
                findings = scan_text(text, banned_terms_dict)
            elif uploaded_file.name.endswith(".pptx"):
                text = read_pptx(uploaded_file)
                findings = scan_text(text, banned_terms_dict)
            else:
                st.error("Unsupported file type.")
        except Exception as e:
            st.error(f"Error reading file: {e}")

        # --- Display Results ---
        if findings:
            st.markdown("### 📊 Summary Statistics")
            df = pd.DataFrame(findings)
            term_counts = df["Banned Term"].value_counts().reset_index()
            term_counts.columns = ["Term", "Frequency"]

            colA, colB = st.columns(2)
            colA.metric(label="Total Banned Terms Flagged", value=len(df))
            colB.metric(label="Unique Terms Found", value=term_counts.shape[0])

            with st.expander("📋 Term Frequency Table"):
                st.dataframe(term_counts, use_container_width=True)

            st.markdown("### 🔎 Flagged Terms Table")
            st.dataframe(df, use_container_width=True)
            st.success(f"{len(df)} instance(s) of non-compliant language found.")
        else:
            st.success("✅ No banned terms found in the uploaded document.")

with tab2:
    st.markdown("### 🚫 Banned Terms and Suggested Replacements")
    banned_df = pd.DataFrame([
        {"Banned Term": term, "Suggested Replacement(s)": ", ".join(suggestions)}
        for term, suggestions in banned_terms_dict.items()
    ])
    st.dataframe(banned_df, use_container_width=True)
