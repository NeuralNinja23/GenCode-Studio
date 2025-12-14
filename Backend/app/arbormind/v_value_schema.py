from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

@dataclass
class VValue:
    """
    V-Value (Vector Value) Schema.
    Wraps an arbitrary configuration dictionary for use in T-AM operations.
    """
    data: Dict[str, Any]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VValue':
        return cls(data=data.copy())
        
    def to_dict(self) -> Dict[str, Any]:
        return self.data.copy()
        
    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)
        
    def set(self, key: str, value: Any) -> None:
        self.data[key] = value
