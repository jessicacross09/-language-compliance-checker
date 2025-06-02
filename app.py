import streamlit as st
import openai
import os
import re
from io import StringIO
from docx import Document
import base64

# Set API key from environment or Streamlit Cloud secret
openai.api_key = os.getenv("OPENAI_API_KEY")

# Customize banned terms here
banned_terms = [
    "diversity",
    "equity",
    "inclusion",
    "climate change",
    "gender mainstreaming",
    "social justice"
]

# Highlight flagged terms
def check_for_banned_terms(text, banned_terms):
    flagged = []
    highlighted_text = text

    for term in banned_terms:
        if term.lower() in text.lower():
            flagged.append(term)
            highlighted_text = re.sub(
                fr"(?i)\b({re.escape(term)})\b",
                r"<span style='background-color: yellow;'>\1</span>",
                highlighted_text
            )

    return flagged, highlighted_text

# GPT-4 contextual review
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

# Download HTML helper
def create_download_link(html_content, filename="reviewed_output.html"):
    b64 = base64.b64encode(html_content.encode()).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="{filename}">📥 Download Reviewed Version</a>'
    return href

# App layout
st.set_page_config(page_title="Language Compliance Checker")
st.title("🕵️ Language Compliance Checker")
st.markdown("Upload a `.docx` or `.txt` file to scan for banned terms and receive a GPT-4 review.")

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
        flagged_terms, highlighted = check_for_banned_terms(sample_text, banned_terms)

        if flagged_terms:
            st.error(f"🚫 Flagged terms: {', '.join(flagged_terms)}")
            st.markdown("### ✏️ Text with Highlighted Issues:")
            st.markdown(highlighted, unsafe_allow_html=True)

            # Add download button
            download_link = create_download_link(f"<html><body>{highlighted}</body></html>")
            st.markdown(download_link, unsafe_allow_html=True)
        else:
            st.success("✅ No direct banned terms found.")
            st.markdown("### ✏️ Your Original Text:")
            st.markdown(sample_text)

        st.subheader("🧠 GPT-4 Contextual Review")
        with st.spinner("Analyzing with GPT-4..."):
            gpt_analysis = analyze_with_gpt(sample_text, banned_terms)
            st.write(gpt_analysis)
    else:
        st.warning("The uploaded file is empty.")
