# app/core/domain_grounding.py
"""
Domain Entity Grounding - Phase-1 Stabilization

Ensure projects have meaningful domain entities beyond just User.

RULES:
1. Infer minimum viable entities from archetype
2. User-only projects are invalid for most archetypes
3. Signal if domain entities are missing (non-fatal)

This prevents:
- Empty/meaningless projects
- User CRUD confusion
- Supervisor rejections for incomplete domain models
"""
from typing import List, Set, Dict, Optional


# ═══════════════════════════════════════════════════════════════════════════
# ARCHETYPE → MINIMUM VIABLE ENTITIES MAP
# ═══════════════════════════════════════════════════════════════════════════

ARCHETYPE_ENTITY_MAP: Dict[str, Set[str]] = {
    # Project Management
    "project_management": {"Task", "Project"},
    "kanban": {"Task", "Column"},
    "task_manager": {"Task"},
    "todo": {"Task"},
    "issue_tracker": {"Issue", "Ticket"},
    "bug_tracking": {"Bug", "Issue"},
    
    # Business / CRM
    "crm": {"Lead", "Contact", "Deal"},
    "sales": {"Lead", "Opportunity"},
    "customer": {"Customer", "Account"},
    
    # E-commerce
    "ecommerce": {"Product", "Order"},
    "shop": {"Product", "Cart"},
    "store": {"Product"},
    "marketplace": {"Product", "Listing"},
    
    # Content
    "blog": {"Post", "Article"},
    "cms": {"Page", "Article"},
    "social": {"Post", "Feed"},
    "forum": {"Thread", "Post"},
    
    # Analytics / Tracking
    "analytics": {"Event", "Metric"},
    "dashboard": {"Metric", "Widget"},
    "monitoring": {"Alert", "Metric"},
    
    # Inventory / Assets
    "inventory": {"Item", "Stock"},
    "warehouse": {"Item", "Location"},
    "asset": {"Asset", "Resource"},
    
    # Booking / Scheduling
    "booking": {"Booking", "Appointment"},
    "calendar": {"Event", "Appointment"},
    "scheduling": {"Schedule", "Slot"},
    
    # Education
    "lms": {"Course", "Lesson"},
    "learning": {"Course", "Module"},
    "education": {"Course", "Student"},
    
    # Finance
    "expense": {"Expense", "Transaction"},
    "budget": {"Budget", "Category"},
    "invoice": {"Invoice", "Payment"},
    
    # Default
    "crud": {"Item"},
    "api": {"Resource"},
    "general": {"Item"},
}


def infer_entities_from_archetype(archetype: str) -> Set[str]:
    """
    Infer minimum viable entities from archetype.
    
    Returns:
        Set of entity names (capitalized)
    """
    normalized = archetype.lower().strip()
    
    # Direct match
    if normalized in ARCHETYPE_ENTITY_MAP:
        return ARCHETYPE_ENTITY_MAP[normalized]
    
    # Partial match
    for key, entities in ARCHETYPE_ENTITY_MAP.items():
        if key in normalized or normalized in key:
            return entities
    
    # Default fallback
    return {"Item"}


def infer_entities_from_user_request(user_request: str) -> Set[str]:
    """
    Extract potential entities from user request using keywords.
    
    This is a simple heuristic, not NLP.
    """
    import re
    
    request_lower = user_request.lower()
    detected_entities = set()
    
    # Common entity keywords
    entity_keywords = {
        "task": "Task",
        "project": "Project",
        "issue": "Issue",
        "bug": "Bug",
        "ticket": "Ticket",
        "lead": "Lead",
        "contact": "Contact",
        "customer": "Customer",
        "product": "Product",
        "order": "Order",
        "item": "Item",
        "post": "Post",
        "article": "Article",
        "event": "Event",
        "booking": "Booking",
        "expense": "Expense",
        "invoice": "Invoice",
        "course": "Course",
    }
    
    for keyword, entity_name in entity_keywords.items():
        if keyword in request_lower:
            detected_entities.add(entity_name)
    
    return detected_entities


def validate_domain_entities(
    detected_entities: List[str],
    archetype: str,
    user_request: str
) -> Dict[str, any]:
    """
    Validate that project has meaningful domain entities.
    
    Returns:
        {
            "valid": bool,
            "issues": List[str],
            "suggested_entities": Set[str],
            "has_only_user": bool
        }
    """
    issues = []
    
    # Normalize detected entities
    entity_names = {e.capitalize() for e in detected_entities if e.lower() != "user"}
    has_only_user = (not entity_names) and any(e.lower() == "user" for e in detected_entities)
    
    # Get expected entities from archetype
    expected_from_archetype = infer_entities_from_archetype(archetype)
    expected_from_request = infer_entities_from_user_request(user_request)
    suggested_entities = expected_from_archetype | expected_from_request
    
    # Check if User is the only entity
    if has_only_user:
        issues.append(
            f"User is a SYSTEM entity, not a domain entity. "
            f"Expected domain entities for '{archetype}': {', '.join(suggested_entities)}"
        )
    
    # Check if domain entities are missing
    if not entity_names and archetype not in ["auth", "authentication"]:
        issues.append(
            f"No domain entities detected. "
            f"Suggested entities for '{archetype}': {', '.join(suggested_entities)}"
        )
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "suggested_entities": suggested_entities,
        "has_only_user": has_only_user,
        "domain_entities": entity_names
    }


def apply_entity_grounding(
    entities: List[str],
    archetype: str,
    user_request: str
) -> List[str]:
    """
    Apply domain entity grounding to ensure meaningful entities.
    
    If User is the only entity, inject archetype-appropriate entities.
    
    Returns:
        List of entities (with grounding applied)
    """
    validation = validate_domain_entities(entities, archetype, user_request)
    
    if validation["has_only_user"] or not validation["domain_entities"]:
        # Inject suggested entities
        suggested = list(validation["suggested_entities"])
        
        # Keep User but add domain entities
        grounded_entities = [e for e in entities if e.lower() == "user"] + suggested
        
        return grounded_entities
    
    # Entities are valid, return as-is
    return entities
