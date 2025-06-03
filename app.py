import streamlit as st
import os
import re
import pandas as pd
from io import StringIO
from docx import Document
import fitz  # PyMuPDF
from pptx import Presentation
import spacy
import openai

# --- Load spaCy model and ensure it's available in Streamlit Cloud ---
os.system("python -m spacy download en_core_web_sm")
nlp = spacy.load("en_core_web_sm")

# --- Set your OpenAI API key securely ---
openai.api_key = os.getenv("OPENAI_API_KEY")  # Set this in Streamlit Cloud settings or locally

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
}

# --- Context-Aware Exception Lists ---
ALLOWED_CONTEXTS_NATIONAL = [
    "national university", "national institute", "national agency", "national bureau",
    "national laboratory", "national center", "national academy", "national school",
    "national authority", "national service", "national college", "national research",
    "national science", "national statistics"
]

ALLOWED_CONTEXTS_TAIWAN = [
    "national taiwan university", "taiwan tech", "taiwan normal university",
    "taiwan external trade", "taiwan semiconductor", "taiwan trade center",
    "taiwanese american foundation", "taiwanese chamber", "taiwan forestry",
    "taiwan sugar", "taiwan cement", "taiwan cooperative", "taiwan tourism",
    "taiwan international ports", "taiwan railways", "taiwan high speed rail"
]

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

