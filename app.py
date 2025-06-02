import streamlit as st
import openai
import os
import re
from io import BytesIO, StringIO
from docx import Document
from docx.shared import RGBColor
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# API key from environment or Streamlit Cloud secret
openai.api_key = os.getenv("OPENAI_API_KEY")

# Customize banned terms
banned_terms = [
    "anti-racism",
    "clean energy",
    "climate change",
    "climate crisis",
    "climate science",
    "disability",
    "diverse",
    "diverse backgrounds",
    "diverse communities",
    "diverse community",
    "diverse group",
    "diverse groups",
    "diversified",
    "diversify",
    "diversifying",
    "diversity",
    "equity",
    "gender",
    "gender mainstreaming",
    "gender-responsive",
    "Gulf of Mexico",
    "inclusion",
    "inclusive",
    "inclusive leadership",
    "inclusiveness",
    "inclusivity",
    "non-binary",
    "nonbinary",
    "oppression",
    "oppressive",
    "social justice",
    "vulnerable populations"
]

# Highlight terms and return both HTML + positions
def check_for_banned_terms(text, banned_terms):
    flagged = []
    pattern_map = []

    for term in banned_terms:
        if term.lower() in text.lower():
            flagged.append(term)
            matches = list(re.finditer(fr"(?i)\b({re.escape(term)})\b", text))
            pattern_map.extend(matches)

    return flagged, text, pattern_map

# GPT-4 review
def analyze_with_gpt(text, banned_terms):
    prompt = f"""
You are a compliance checker. Review the following text and flag any language that directly or indirectly relates to these restricted themes: {', '.join(banned_terms)}.

Flag explicit terms as well as paraphrased or implied references. Provide a short reason for each issue.

Text:
{text}

Return a bullet list of all flagged issues.
"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        return f"⚠️ GPT-4 error: {e}"

# Read DOCX
def read_docx(file):
    doc = Document(file)
    return "\n".join([para.text for para in doc.paragraphs])

# Read TXT
def read_txt(file):
    stringio = StringIO(file.getvalue().decode("utf-8"))
    return stringio.read()

# Create a Word file with highlighted banned terms
def create_docx_with_highlights(text, pattern_map):
    doc = Document()
    para = doc.add_paragraph()

    last_index = 0
    for match in sorted(pattern_map, key=lambda m: m.start()):
        start, end = match.start(), match.end()

        if start > last_index:
            para.add_run(text[last_index:start])

        run = para.add_run(text[start:end])
        highlight_run(run)

        last_index = end

    if last_index < len(text):
        para.add_run(text[last_index:])

    # Save to BytesIO
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# Apply yellow highlight to a run
def highlight_run(run):
    highlight = OxmlElement("w:highlight")
    highlight.set(qn("w:val"), "yellow")
    rPr = run._element.get_or_add_rPr()
    rPr.append(highlight)

# Streamlit UI
st.set_page_config(page_title="APEC-RISE Text Harmonization Tool")
st.title("🕵️ APEC-RISE Text Harmonization Tool")
st.markdown("Check text for non-compliant language and suggest improvements.")

uploaded_file = st.file_uploader("📤 Upload a file", type=["docx", "txt"])

if uploaded_file:
    if uploaded_file.name.endswith(".docx"):
        sample_text = read_docx(uploaded_file)
    elif uploaded_file.name.endswith(".txt"):
        sample_text = read_txt(uploaded_file)
    else:
        st.error("Unsupported file type.")
        sample_text = ""

    if sample_text.strip():
        flagged_terms, full_text, pattern_map = check_for_banned_terms(sample_text, banned_terms)

        if flagged_terms:
            st.error(f"🚫 Flagged terms: {', '.join(flagged_terms)}")
            st.markdown("### ✏️ Preview (not highlighted in browser):")
            st.text(full_text[:1000] + ("..." if len(full_text) > 1000 else ""))

            # Word download
            buffer = create_docx_with_highlights(full_text, pattern_map)
            st.download_button(
                label="📥 Download Reviewed Word File",
                data=buffer,
                file_name="reviewed_text.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        else:
            st.success("✅ No direct banned terms found.")
            st.markdown("### ✏️ Your Original Text:")
            st.text(sample_text)

        st.subheader("🧠 GPT-4 Contextual Review")
        with st.spinner("Analyzing with GPT-4..."):
            gpt_analysis = analyze_with_gpt(sample_text, banned_terms)
            st.write(gpt_analysis)
    else:
        st.warning("The uploaded file is empty.")
