# app/agents/types.py
from typing import TypedDict, List, Literal, Optional, Dict, Any, Union

# --- From parser.ts ---
class GeneratedFile(TypedDict):
    path: str
    code: str

class ArchitectFile(TypedDict):
    path: str
    description: str
    purpose: Optional[str]

class ArchitectPlan(TypedDict):
    summary: str
    planName: str
    description: Optional[str]
    files: List[ArchitectFile]

class QAIssue(TypedDict):
    file: str
    line: int
    area: str
    description: str
    severity: Literal['critical', 'major', 'minor']
    suggested_fix: str
    codeContext: Optional[str]
    testableImpact: Optional[str]

# --- From workflows.ts ---
class FilePlan(TypedDict):
    path: str
    description: str

class TestReport(TypedDict):
    summary: str
    passed: bool
    issueCount: Optional[int]
    severityBreakdown: Optional[Dict[str, int]]
    issues: List[QAIssue]
    recommendations: Optional[List[str]]

# --- From Marcus's JSON Schema ---
class ToolCall(TypedDict):
    name: str
    args: Dict[str, Any]

class MarcusPlan(TypedDict):
    thought: str
    tool_call: Optional[ToolCall]
    speak_to_user: Optional[str]
    