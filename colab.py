import os
import json
import time
import re
import requests
import pandas as pd
from typing import List, TypedDict
from langgraph.graph import StateGraph, END
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT

# ==========================================
# 1. SETUP & UTILS
# ==========================================

HF_TOKEN = "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"
API_URL = "https://router.huggingface.co/v1/chat/completions"
HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"}

def query_hf_model(system_prompt, user_prompt):
    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "model": "deepseek-ai/DeepSeek-V3.2",
        "temperature": 0.1,
        "max_tokens": 1000
    }
    try:
        response = requests.post(API_URL, headers=HEADERS, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"❌ API Error: {e}")
        return ""

def clean_and_parse_json(text):
    try:
        return json.loads(text)
    except:
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            try: return json.loads(match.group())
            except: pass
    return []

# ==========================================
# 2. STATE DEFINITION
# ==========================================

class AgentState(TypedDict):
    inventory: List[dict]
    shortlist: List[dict]
    expanded_reports: List[dict]
    final_report_text: str

# ==========================================
# 3. AGENT NODES
# ==========================================

# --- Node 1: Curator Agent (Updated to handle Excel data) ---
def curator_agent(state: AgentState):
    print("--- 1. Curator Agent: Shortlisting from Excel Data ---")
    inventory = state.get("inventory", [])

    # We send the titles and themes to the LLM to choose the best ones
    # Limiting to top 20 for the prompt to avoid token overflow
    simplified_list = [
        {"id": i, "title": item['title'], "theme": item['category']}
        for i, item in enumerate(inventory[:20])
    ]

    inv_str = json.dumps(simplified_list, indent=2)

    sys_prompt = "You are a hackathon judge. Output strictly valid JSON."
    user_prompt = f"""
    Review these problem statements and select the Top 1 most innovative and feasible ones.
    Return ONLY a JSON list of the selected IDs.

    DATA:
    {inv_str}
    """

    response = query_hf_model(sys_prompt, user_prompt)
    selected_ids = clean_and_parse_json(response)

    if isinstance(selected_ids, list):
        # Map the selected indices back to the original inventory objects
        shortlist = [inventory[idx] for idx in selected_ids if idx < len(inventory)]
    else:
        shortlist = inventory[:4] # Fallback

    print(f"✅ Selected {len(shortlist)} items for technical expansion.")
    return {"shortlist": shortlist}

# --- Node 2: SME Agent ---
def sme_agent(state: AgentState):
    print("--- 2. SME Agent: Expanding Problems ---")
    shortlist = state.get("shortlist", [])
    expanded = []

    for item in shortlist:
        print(f"   > Expanding: {item['title']}...")
        sys_prompt = f"You are an expert consultant in {item['category']}."
        user_prompt = f"""
Expand on the following hackathon problem: "{item['title']}"
Original Description: {item['description']}

Please provide a professional and comprehensive breakdown using the following structure:

1. **The Hook (Title & Summary)**:
   - Create a catchy, descriptive title.
   - Provide a brief "TL;DR" (Too Long; Didn't Read) summary that conveys the "vibe" and essence of the challenge instantly.

2. **Context & Background (The "Why")**:
   - Explain the current state of the industry or specific area.
   - **The Problem**: Detail what is broken, inefficient, or missing.
   - **The Impact**: Explain who is affected and why it matters.
   - **Real-world Example**: Describe a scenario where this problem occurs.

3. **The Core Challenge (The "What")**:
   - **Actionable Goal**: State a clear, specific objective for the project.
   - **Scope**: Define the boundaries (e.g., mobile app, web platform, IoT prototype).
   - **Mandatory Features**: List the main features/functionalities the solution MUST include to be considered successful.

4. **Target Personas**:
   - Define the end-user for whom the teams are building. 
   - Describe their specific needs, pain points, or limitations.
"""

        expansion_text = query_hf_model(sys_prompt, user_prompt)
        expanded.append({
            "category": item['category'],
            "title": item['title'],
            "expansion": expansion_text
        })
        time.sleep(1.0) # Rate limit protection

    return {"expanded_reports": expanded}

# --- Node 3: Architect Agent ---
def architect_agent(state: AgentState):
    print("--- 3. Architect: Generating Formatted PDF ---")
    reports = state.get("expanded_reports", [])

    final_doc = "ANALYZED PROBLEM STATEMENTS REPORT\n\n"
    for r in reports:
        final_doc += f"**Category: {r['category']}**\n"
        final_doc += f"**Problem Title:** {r['title']}**\n" # Original had ** here by mistake, removing.
        final_doc += "-" * 40 + "\n"
        final_doc += f"{r['expansion']}\n\n" + "="*40 + "\n\n"

    save_text_to_pdf(final_doc, "Final_Excel_Report.pdf")
    return {"final_report_text": final_doc}

# --- PDF Helper ---
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

# ==========================================
# 4. EXECUTION
# ==========================================

def load_data_from_csv(file_path):
    # Changed from pd.read_csv to pd.read_excel
    df = pd.read_excel(file_path)
    # Mapping CSV columns to a standard dictionary format
    inventory = []
    for _, row in df.iterrows():
        inventory.append({
            "title": row['Title of the Problem'],
            "category": row['Theme'],
            "description": row['Problem Description']
        })
    return inventory

# Setup Graph
workflow = StateGraph(AgentState)
workflow.add_node("curator", curator_agent)
workflow.add_node("sme", sme_agent)
workflow.add_node("architect", architect_agent)

workflow.set_entry_point("curator")
workflow.add_edge("curator", "sme")
workflow.add_edge("sme", "architect")
workflow.add_edge("architect", END)

app = workflow.compile()

if __name__ == "__main__":
    csv_file = "problem_statements.xlsx"

    if os.path.exists(csv_file):
        print(f"📂 Loading data from {csv_file}...")
        initial_inventory = load_data_from_csv(csv_file)

        print("🚀 Starting Multi-Agent Analysis...\n")
        app.invoke({"inventory": initial_inventory})
    else:
        print("❌ CSV File not found.")

