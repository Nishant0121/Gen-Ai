import json
import re
import requests
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from src.config import API_URL, HEADERS

def query_hf_model(system_prompt, user_prompt):
    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "model": "deepseek-ai/DeepSeek-V3.2",
        "temperature": 0.1,
        "max_tokens": 1500
    }
    try:
        response = requests.post(API_URL, headers=HEADERS, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"❌ API Error: {e}")
        return ""

def clean_and_parse_json(text):
    print(f"LLM Response: {text}")
    try:
        res = json.loads(text)
        print(f"Selected IDs: {res}")
        return res
    except:
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            try:
                res = json.loads(match.group())
                print(f"Selected IDs: {res}")
                return res
            except: pass
    print(f"Selected IDs: []")
    return []

def save_text_to_pdf(text, filename):
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=10, leading=12, spaceAfter=10)

    story = []
    for p_text_raw in text.split('\n'): # Iterate through raw text lines
        if not p_text_raw.strip():
            story.append(Spacer(1, 12))
            continue

        # Apply the markdown-to-HTML conversion to each line individually
        p_text_formatted = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', p_text_raw, flags=re.DOTALL)

        # Create Paragraph.
        p = Paragraph(p_text_formatted, styles['Heading2'] if "Category:" in p_text_formatted else body_style)
        story.append(p)
    doc.build(story)

def load_data_from_df(df):
    inventory = []
    for _, row in df.iterrows():
        # Handle cases where column names might be slightly different or missing
        title = row.get('Title of the Problem', row.get('title', 'Unknown Title'))
        category = row.get('Theme', row.get('category', 'General'))
        description = row.get('Problem Description', row.get('description', 'No description provided.'))
        
        inventory.append({
            "title": title,
            "category": category,
            "description": description
        })
    return inventory
