import streamlit as st
import openai
import os
import re
import pandas as pd
from io import StringIO
from docx import Document

# Set up OpenAI key from environment or Streamlit secrets
openai.api_key = os.getenv("OPENAI_API_KEY")

# Banned terms and suggested replacements
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

# Check text for banned terms and extract context
def check_for_banned_terms(text, banned_terms_dict):
    findings = []
    for term, suggestions in banned_terms_dict.items():
        for match in re.finditer(fr"(?i)\b({re.escape(term)})\b", text):
            start = match.start()
            end = match.end()
            snippet = text[max(0, start - 30): min(len(text), end + 30)].replace('\n', ' ')
            findings.append({
                "Term": match.group(),
                "Start Index": start,
                "End Index": end,
                "Context": f"...{snippet.strip()}...",
                "Suggested Replacement": ", ".join(suggestions)
            })
    return findings

# GPT-4 review
def analyze_with_gpt(text, banned_terms_dict):
    banned_list = ", ".join(banned_terms_dict.keys())
    prompt = f"""
You are a compliance checker. Review the following text and flag any language that directly or indirectly relates to these restricted themes: {banned_list}.

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

# Streamlit UI
st.set_page_config(page_title="APEC-RISE Text Harmonization Tool")
st.title("🕵️ APEC-RISE Text Harmonization Tool")
st.markdown("Check uploaded text for non-compliant language and suggest alternative phrasing.")

uploaded_file = st.file_uploader("📤 Upload a .docx or .txt file", type=["docx", "txt"])

if uploaded_file:
    if uploaded_file.name.endswith(".docx"):
        sample_text = read_docx(uploaded_file)
    elif uploaded_file.name.endswith(".txt"):
        sample_text = read_txt(uploaded_file)
    else:
        st.error("Unsupported file type.")
        sample_text = ""

    if sample_text.strip():
        findings = check_for_banned_terms(sample_text, banned_terms_dict)

        if findings:
            st.error("🚫 Banned terms found in document.")
            st.markdown("### 📋 Flagged Terms Table")

            df = pd.DataFrame(findings)
            st.dataframe(df, use_container_width=True)
        else:
            st.success("✅ No banned terms found.")
            st.markdown("### ✏️ Original Text")
            st.text(sample_text)

        st.subheader("🧠 GPT-4 Contextual Review")
        with st.spinner("Running GPT-4 review..."):
            gpt_output = analyze_with_gpt(sample_text, banned_terms_dict)
            st.write(gpt_output)
    else:
        st.warning("The uploaded file is empty.")
