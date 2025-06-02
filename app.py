import streamlit as st
import os
import re
import pandas as pd
from io import StringIO
from docx import Document
import fitz  # PyMuPDF for PDF support

# --- Streamlit Page Config ---
st.set_page_config(page_title="APEC-RISE Text Harmonization Tool", layout="wide")
st.title("🕵️ APEC-RISE Text Harmonization Tool")
st.markdown("Upload a document to identify non-compliant language and receive suggested alternatives.")

# --- Banned Terms with Replacements ---
banned_terms_dict = {
    "anti-racism": ["addressing discrimination"],
    "clean energy": ["energy diversification"],
    "climate change": ["environmental shifts"],
    "climate crisis": ["environmental challenges"],
    "climate science": ["environmental data"],
    "country": ["economy"],
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
    "equity": ["fair access"],
    "gender": ["demographics"],
    "gender mainstreaming": ["gender considerations"],
    "gender-responsive": ["inclusive of gender perspectives"],
    "Gulf of Mexico": ["Gulf of America"],
    "Hanoi": ["Ha Noi"],
    "inclusion": ["broad participation"],
    "inclusive": ["participatory"],
    "inclusive leadership": ["broad-based leadership"],
    "inclusiveness": ["broad engagement"],
    "inclusivity": ["collaborative approaches"],
    "nation": ["economy"],
    "national": ["domestic"],
    "non-binary": ["gender-diverse"],
    "nonbinary": ["gender-diverse"],
    "oppression": ["systemic challenges"],
    "oppressive": ["restrictive"],
    "social justice": ["equitable policy outcomes"],
    "Taiwan": ["Chinese Taipei"],
    "Vietnam": ["Viet Nam"],
    "vulnerable populations": ["underrepresented stakeholders"]
}

# --- File Readers ---
def read_docx(file):
    doc = Document(file)
    return "\n".join([para.text for para in doc.paragraphs])

def read_txt(file):
    return StringIO(file.getvalue().decode("utf-8")).read()

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

def scan_text(text, banned_dict):
    results = []
    for term, suggestions in banned_dict.items():
        pattern = re.compile(rf"\b({re.escape(term)})\b", re.IGNORECASE)
        for match in pattern.finditer(text):
            snippet = text[max(0, match.start() - 40): min(len(text), match.end() + 60)].replace('\n', ' ')
            results.append({
                "Banned Term": match.group(),
                "Context": f"...{snippet.strip()}...",
                "Suggested Replacement(s)": ", ".join(suggestions)
            })
    return results

# --- Upload and Process ---
uploaded_file = st.file_uploader("📤 Upload a .pdf, .docx, or .txt file", type=["pdf", "docx", "txt"])

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
        else:
            st.error("Unsupported file type.")
    except Exception as e:
        st.error(f"Error reading file: {e}")

    # --- Display Results ---
    if findings:
        st.markdown("### 📋 Flagged Terms Table")
        df = pd.DataFrame(findings)
        st.dataframe(df, use_container_width=True)
        st.success(f"{len(df)} instance(s) of non-compliant language found.")
    else:
        st.success("✅ No banned terms found in the uploaded document.")
