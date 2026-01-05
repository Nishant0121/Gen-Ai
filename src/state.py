from typing import List, TypedDict

class AgentState(TypedDict):
    inventory: List[dict]
    shortlist: List[dict]
    expanded_reports: List[dict]
    final_report_text: str
