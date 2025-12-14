"""
Multi-entity specifications and data structures.
Used for multi-entity generation in GenCode Studio.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import json


@dataclass
class Field:
    """Field specification for an entity."""
    name: str
    type: str  # "str", "int", "bool", "datetime", "float", "Optional[str]", etc.
    required: bool = True
    enum_values: List[str] = field(default_factory=list)
    description: str = ""
    default: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "required": self.required,
            "enum_values": self.enum_values,
            "description": self.description,
            "default": self.default
        }


@dataclass
class Relationship:
    """Relationship between entities."""
    from_entity: str
    to_entity: str
    type: str  # "one_to_many", "many_to_many", "one_to_one"
    foreign_key: str = ""
    cascade_delete: bool = False
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_entity": self.from_entity,
            "to_entity": self.to_entity,
            "type": self.type,
            "foreign_key": self.foreign_key,
            "cascade_delete": self.cascade_delete,
            "description": self.description
        }


@dataclass
class EntitySpec:
    """Complete specification for an entity."""
    name: str  # "Task", "User", "Note"
    plural: str  # "tasks", "users", "notes"
    description: str = ""
    fields: List[Field] = field(default_factory=list)
    is_primary: bool = True
    generation_order: int = 999  # Lower = generated first
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "plural": self.plural,
            "description": self.description,
            "fields": [f.to_dict() for f in self.fields],
            "is_primary": self.is_primary,
            "generation_order": self.generation_order
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EntitySpec":
        """Create EntitySpec from dictionary."""
        fields = [Field(**f) if isinstance(f, dict) else f for f in data.get("fields", [])]
        return cls(
            name=data["name"],
            plural=data["plural"],
            description=data.get("description", ""),
            fields=fields,
            is_primary=data.get("is_primary", True),
            generation_order=data.get("generation_order", 999)
        )


@dataclass
class EntityPlan:
    """Complete entity generation plan."""
    entities: List[EntitySpec]
    relationships: List[Relationship]
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities": [e.to_dict() for e in self.entities],
            "relationships": [r.to_dict() for r in self.relationships],
            "warnings": self.warnings
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EntityPlan":
        """Create EntityPlan from dictionary."""
        entities = [EntitySpec.from_dict(e) for e in data.get("entities", [])]
        relationships = [Relationship(**r) if isinstance(r, dict) else r for r in data.get("relationships", [])]
        return cls(
            entities=entities,
            relationships=relationships,
            warnings=data.get("warnings", [])
        )
    
    def save(self, path) -> None:
        """Save entity plan to JSON file."""
        from pathlib import Path
        path = Path(path)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
    
    @classmethod
    def load(cls, path) -> "EntityPlan":
        """Load entity plan from JSON file."""
        from pathlib import Path
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Entity plan not found: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(data)
