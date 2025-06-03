import streamlit as st
import os
import re
import pandas as pd
from io import StringIO
from docx import Document
import fitz  # PyMuPDF
from pptx import Presentation
import openai

# --- Ensure spaCy model is loaded in Streamlit Cloud ---
import spacy
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    import spacy
nlp = spacy.load("en_core_web_sm")

# --- Set your OpenAI API key securely ---
openai.api_key = os.getenv("OPENAI_API_KEY")

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
}  # Use your full dictionary here (omitted for brevity)

# --- Context-Aware Exception Lists ---
ALLOWED_CONTEXTS_NATIONAL = [ ... ]
ALLOWED_CONTEXTS_TAIWAN = [ ... ]

def ask_gpt_about_context(snippet, term):
    prompt = (
        f"Is the word '{term}' in this sentence referring to a formal institution "
        f"(e.g., government agency, university) or is it used descriptively?\n\n"
        f"Sentence: {snippet}"
    )
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        answer = response['choices'][0]['message']['content'].strip().lower()
        return "descriptive" in answer
    except Exception:
        return False

def is_exception_context(snippet, term):
    snippet_lower = snippet.lower()
    if term.lower() == "national" and any(ctx in snippet_lower for ctx in ALLOWED_CONTEXTS_NATIONAL):
        return True
    if term.lower() == "taiwan" and any(ctx in snippet_lower for ctx in ALLOWED_CONTEXTS_TAIWAN):
        return True
    doc = nlp(snippet)
    for ent in doc.ents:
        if term.lower() in ent.text.lower() and ent.label_ in ["ORG", "GPE", "FAC"]:
            return True
    if term.lower() in ["national", "taiwan"]:
        return not ask_gpt_about_context(snippet, term)
    return False

def scan_text_with_context(text, banned_dict, chars_per_page=1800):
    results, skipped = [], []
    for term, suggestions in banned_dict.items():
        pattern = re.compile(rf"\b({re.escape(term)})\b", re.IGNORECASE)
        for match in pattern.finditer(text):
            start = match.start()
            estimated_page = max(1, (start // chars_per_page) + 1)
            snippet = text[max(0, start - 40): min(len(text), start + 60)].replace('\n', ' ')
            if is_exception_context(snippet, term):
                skipped.append({"Skipped Term": match.group(), "Page": estimated_page, "Context": f"...{snippet.strip()}..."})
                continue
            results.append({
                "Banned Term": match.group(),
                "Page": estimated_page,
                "Context": f"...{snippet.strip()}...",
                "Suggested Replacement(s)": ", ".join(suggestions)
            })
    return results, skipped

def scan_pdf_with_context(file, banned_dict):
    results, skipped = [], []
    doc = fitz.open(stream=file.read(), filetype="pdf")
    for page_number, page in enumerate(doc, start=1):
        text = page.get_text()
        for term, suggestions in banned_dict.items():
            pattern = re.compile(rf"\b({re.escape(term)})\b", re.IGNORECASE)
            for match in pattern.finditer(text):
                snippet = text[max(0, match.start() - 40): min(len(text), match.end() + 60)].replace('\n', ' ')
                if is_exception_context(snippet, term):
                    skipped.append({"Skipped Term": match.group(), "Page": page_number, "Context": f"...{snippet.strip()}..."})
                    continue
                results.append({
                    "Banned Term": match.group(),
                    "Page": page_number,
                    "Context": f"...{snippet.strip()}...",
                    "Suggested Replacement(s)": ", ".join(suggestions)
                })
    return results, skipped

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

# --- Streamlit Tabs ---
tab1, tab2 = st.tabs(["Upload Document", "View Banned Terms"])

with tab1:
    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded_file = st.file_uploader("Upload a .pdf, .docx, .txt, or .pptx file", type=["pdf", "docx", "txt", "pptx"])
    with col2:
        st.info("Once uploaded, the file will be scanned for banned terms. Flagged terms and recommended alternatives will appear below.")

    if uploaded_file:
        findings, skipped, raw_text = [], [], ""
        try:
            if uploaded_file.name.endswith(".pdf"):
                findings, skipped = scan_pdf_with_context(uploaded_file, banned_terms_dict)
            elif uploaded_file.name.endswith(".docx"):
                raw_text = read_docx(uploaded_file)
                findings, skipped = scan_text_with_context(raw_text, banned_terms_dict)
            elif uploaded_file.name.endswith(".txt"):
                raw_text = read_txt(uploaded_file)
                findings, skipped = scan_text_with_context(raw_text, banned_terms_dict)
            elif uploaded_file.name.endswith(".pptx"):
                raw_text = read_pptx(uploaded_file)
                findings, skipped = scan_text_with_context(raw_text, banned_terms_dict)
            else:
                st.error("Unsupported file type.")
        except Exception as e:
            st.error(f"Error reading file: {e}")

        if findings:
            st.markdown("### Banned Terms and Suggested Replacements")
    banned_df = pd.DataFrame([
        {"Banned Term": term, "Suggested Replacement(s)": ", ".join(suggestions)}
        for term, suggestions in banned_terms_dict.items()
    ])
    st.dataframe(banned_df, use_container_width=True)


