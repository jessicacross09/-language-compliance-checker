import streamlit as st
import openai
import os
import re

# Get your API key from environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")

# List of banned terms you can customize
banned_terms = [
    "diversity",
    "equity",
    "inclusion",
    "climate change",
    "gender mainstreaming",
    "social justice"
]

# Function to flag and highlight banned terms
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

Flag explicit terms as well as paraphrased or implied references (e.g., "inclusive policies" instead of "inclusion"). Provide a short reason for each issue.

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

# Set up the app interface
st.set_page_config(page_title="Language Compliance Checker")
st.title("🕵️ Language Compliance Checker")
st.markdown("This tool flags banned language and highlights terms in your writing.")

sample_text = st.text_area("✏️ Paste your writing sample below:", height=300)

if st.button("🔍 Check Writing"):
    if not sample_text.strip():
        st.warning("Please enter some text.")
    else:
        # Rule-based check and highlighting
        flagged_terms, highlighted = check_for_banned_terms(sample_text, banned_terms)

        if flagged_terms:
            st.error(f"🚫 Flagged terms: {', '.join(flagged_terms)}")
            st.markdown("### ✏️ Text with Highlighted Issues:")
            st.markdown(highlighted, unsafe_allow_html=True)
        else:
            st.success("✅ No direct banned terms found.")
            st.markdown("### ✏️ Your Original Text:")
            st.markdown(sample_text)

        # GPT-4 contextual review
        st.subheader("🧠 GPT-4 Contextual Review")
        with st.spinner("Analyzing with GPT-4..."):
            gpt_analysis = analyze_with_gpt(sample_text, banned_terms)
            st.write(gpt_analysis)
