# app/arbormind/reconstruction/run_slice_builder.py
"""
ArborMind RunSlice Builder
PHASE 3: State Reconstruction Layer

This module is the ONLY authorized reader of the Execution Ledger.
Its job is to:
1. Read raw events from the ledger
2. Re-assemble them into a coherent State object (RunSlice)
3. Apply Phase 3.5 semantics (Ontology, Authority) onto the raw facts.

INVARIANT: The Ledger knows "Events". The Builder knows "Meaning".
"""

from typing import Dict, Any, List
from dataclasses import dataclass
from app.arbormind.observation.execution_ledger import ExecutionLedger

@dataclass
class RunSlice:
    """
    Reconstructed state of a run at a point in time.
    Immutable representation of 'What Happened'.
    """
    run_id: str
    status: str
    steps: List[Dict[str, Any]]
    failures: List[Dict[str, Any]]
    decisions: List[Dict[str, Any]]
    
class RunSliceBuilder:
    def __init__(self):
        self.ledger = ExecutionLedger.get_instance()
        
    def build_slice(self, run_id: str) -> RunSlice:
        """
        Reconstruct the full run state from raw events.
        """
        # 1. Fetch Raw Events (No logic here, just fetching)
        runs_raw = self.ledger._dump_table("runs", run_id)
        if not runs_raw:
            return None
            
        step_events = self.ledger._dump_table("step_events", run_id)
        fail_events = self.ledger._dump_table("failure_events", run_id)
        dec_events = self.ledger._dump_table("decision_events", run_id)
        
        # 2. Assemble Meaning (The Logic Layer)
        
        # A. Semantic Reconstruction of Steps (Entry + Exit = Duration)
        reconstructed_steps = self._reassemble_steps(step_events)
        
        # B. Semantic Classification of Failures (Apply Ontology if needed)
        classified_failures = fail_events # Pass-through for now, mapped later
        
        return RunSlice(
            run_id=run_id,
            status=runs_raw[0]['status_event'],
            steps=reconstructed_steps,
            failures=classified_failures,
            decisions=dec_events
        )
        
    def _reassemble_steps(self, events: List[Dict]) -> List[Dict]:
        """Convert entry/exit event stream into duration objects."""
        steps = {}
        ordered_steps = []
        
        for e in events:
            name = e['step_name']
            if name not in steps:
                steps[name] = {"name": name, "entry": None, "exit": None}
                ordered_steps.append(steps[name])
            
            if e['event_type'] == "ENTRY":
                steps[name]['entry'] = e['timestamp']
            elif e['event_type'] == "EXIT":
                steps[name]['exit'] = e['timestamp']
                steps[name]['status'] = e.get('payload', '{}') # parse logic here
        
        return ordered_steps

# Convenience facade
def get_run_slice(run_id: str):
    return RunSliceBuilder().build_slice(run_id)
