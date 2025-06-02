import streamlit as st
import os
import re
import pandas as pd
from io import StringIO
from docx import Document
import fitz  # PyMuPDF for PDFs

# --- Streamlit UI Configuration ---
st.set_page_config(page_title="APEC-RISE Text Harmonization Tool", layout="wide")
st.title("🕵️ APEC-RISE Text Harmonization Tool")
st.markdown("Upload a document to identify non-compliant language and get suggested alternatives.")

# --- Define banned terms and their suggested replacements ---
banned_terms_dict = {
    "anti-racism": ["addressing discrimination"],
    "clean energy": ["energy diversification"],
    "climate change": ["environmental shifts"],
    "climate crisis": ["environmental challenges"],
    "climate science": ["environmental data"],
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
    "Gulf of Mexico": ["regionally specific area"],
    "inclusion": ["broad participation"],
    "inclusive": ["participatory"],
    "inclusive leadership": ["broad-based leadership"],
    "inclusiveness": ["broad engagement"],
    "inclusivity": ["collaborative approaches"],
    "non-binary": ["gender-diverse"],
    "nonbinary": ["gender-diverse"],
    "oppression": ["systemic challenges"],
    "oppressive": ["restrictive"],
    "social justice": ["equitable policy outcomes"],
    "vulnerable populations": ["underrepresented stakeholders"]
}

# --- Helpers to read files ---
def read_docx(file):
    doc = Document(file)
    return "\n".join([para.text for para in doc.paragraphs])

def read_txt(file):
    return StringIO(file.getvalue().decode("utf-8")).read()

def read_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

# --- Text scan function ---
def scan_text_for_banned_terms(text, banned_dict):
    results = []
    for term, suggestions in banned_dict.items():
        pattern = re.compile(rf"\b({re.escape(term)})\b", re.IGNORECASE)
        for match in pattern.finditer(text):
            start = match.start()
            snippet = text[max(0, start - 40): min(len(text), start + 60)].replace('\n', ' ')
            results.append({
                "Banned Term": match.group(),
                "Location (Character Index)": start,
                "Context": f"...{snippet.strip()}...",
                "Suggested Replacement(s)": ", ".join(suggestions)
            })
    return results

# --- File upload ---
uploaded_file = st.file_uploader("📤 Upload a .docx, .txt, or .pdf file", type=["docx", "txt", "pdf"])

if uploaded_file:
    # Read the uploaded file
    file_text = ""
    try:
        if uploaded_file.name.endswith(".docx"):
            file_text = read_docx(uploaded_file)
        elif uploaded_file.name.endswith(".txt"):
            file_text = read_txt(uploaded_file)
        elif uploaded_file.name.endswith(".pdf"):
            file_text = read_pdf(uploaded_file)
        else:
            st.error("Unsupported file type.")
    except Exception as e:
        st.error(f"Error reading file: {e}")
        file_text = ""

    if file_text.strip():
        # Scan and display results
        st.markdown("### 📋 Flagged Terms Table")
        findings = scan_text_for_banned_terms(file_text, banned_terms_dict)

        if findings:
            df = pd.DataFrame(findings)
            st.dataframe(df, use_container_width=True)
            st.success(f"{len(df)} instance(s) of non-compliant language found.")
        else:
            st.success("✅ No banned terms found in the document.")
    else:
        st.warning("The uploaded file appears to be empty or unreadable.")
