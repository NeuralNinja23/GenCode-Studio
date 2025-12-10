# app/tools/registry.py
"""
Tool registry - routes tool calls to implementations.
"""
from typing import Any, Dict, List, Optional


async def run_tool(name: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Execute a tool by name.
    
    Available tools:
    - sandboxexec: Run command in Docker sandbox
    - subagentcaller: Call a sub-agent (Derek, Luna, Victoria)
    - filewriterbatch: Write multiple files
    - filereader: Read a file
    - unifiedpatchapplier: Apply unified diff patch
    - jsonpatchapplier: Apply JSON patch
    - deploymentvalidator: Validate deployment health
    """
    from app.tools.implementations import run_tool as impl_run_tool
    return await impl_run_tool(name, args)




def get_available_tools() -> List[str]:
    """Get list of available tool names."""
    return [
        "sandboxexec",
        "subagentcaller", 
        "filewriterbatch",
        "filereader",
        "filelister",
        "codeviewer",
        "unifiedpatchapplier",
        "jsonpatchapplier",
        "pytestrunner",
        "playwrightrunner",
        "deploymentvalidator",
        "healthchecker",
    ]
