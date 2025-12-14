from typing import Dict, Callable, Any
from .v_value_schema import VValue

class TAMOperator:
    """T-AM (Transformational Active Memory) Operator."""
    def __init__(self, name: str, func: Callable[[VValue], VValue]):
        self.name = name
        self.func = func
        
    def apply(self, v_value: VValue) -> VValue:
        return self.func(v_value)

def _invert_strict_mode(v: VValue) -> VValue:
    """Strategy: Relax constraints to allow partial success."""
    new_v = VValue.from_dict(v.to_dict())
    
    # Disable strict mode
    new_v.set("strict_mode", False)
    
    # Disable type verification if present
    if new_v.get("verify_types") is not None:
        new_v.set("verify_types", False)
        
    # Increase edit limit
    current_edits = new_v.get("max_edits", 3)
    if isinstance(current_edits, int):
        new_v.set("max_edits", current_edits * 2)
        
    return new_v

def build_default_tam_operators() -> Dict[str, TAMOperator]:
    """Build the default set of T-AM mutation operators."""
    ops = {}
    ops["INVERT_STRICT_MODE"] = TAMOperator("INVERT_STRICT_MODE", _invert_strict_mode)
    return ops
