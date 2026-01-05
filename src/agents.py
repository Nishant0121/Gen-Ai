import json
import time
from src.state import AgentState
from src.utils import query_hf_model, clean_and_parse_json, save_text_to_pdf

# --- Node 1: Curator Agent ---
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
    Review these problem statements and select the Top 4 most innovative and feasible ones.
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
        sys_prompt = f"You are an expert consultant in {item['category']}. "
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

4. **Conclusion**:
    - Summarize the importance of addressing this challenge.
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
        final_doc += f"**Problem Title:** {r['title']}**\n"
        final_doc += "-" * 40 + "\n"
        final_doc += f"{r['expansion']}\n\n" + "="*40 + "\n\n"

    # We return the text so the UI can decide where to save or download
    return {"final_report_text": final_doc}
