# app/utils/entity_classification.py
"""
Dynamic Entity Classification System

Determines if entities should be AGGREGATE (Document with collection) 
or EMBEDDED (BaseModel nested in other models).

WORKS WITH ANY PROMPT - No hardcoded entity names!
"""
from pathlib import Path
from typing import Dict, Set
import json
import re
from app.core.logging import log


def classify_entities_from_mock(project_path: Path) -> Dict[str, str]:
    """
    Dynamically classify entities from mock.js structure.
    
    Rules (deterministic, works with ANY entities):
    1. AGGREGATE: Appears as top-level export array
       Example: export const mockTasks = [...]
    
    2. EMBEDDED: Appears only as nested object/array property
       Example: assignee: { name: "..." }
       Example: tags: [{ name: "..." }]
    
    Returns:
        Dict mapping entity name to type: {"Task": "AGGREGATE", "Assignee": "EMBEDDED"}
    """
    mock_path = project_path / "frontend" / "src" / "data" / "mock.js"
    
    if not mock_path.exists():
        log("CLASSIFY", "⚠️ mock.js not found - skipping classification")
        return {}
    
    try:
        content = mock_path.read_text(encoding="utf-8")
    except Exception as e:
        log("CLASSIFY", f"❌ Error reading mock.js: {e}")
        return {}
    
    classifications = {}
    
    # ═══════════════════════════════════════════════════════════
    # RULE 1: Top-level arrays = AGGREGATE
    # ═══════════════════════════════════════════════════════════
    # Matches: export const mockTasks = [
    #          export const mockUsers = [
    #          export let dataProducts = [
    
    top_level_pattern = r'export\s+(?:const|let|var)\s+(?:mock|data)?(\w+)\s*=\s*\['
    
    for match in re.finditer(top_level_pattern, content, re.IGNORECASE):
        entity_name_raw = match.group(1)
        
        # Clean up name: remove common suffixes
        entity_name = re.sub(r'(Data|List|Items|Array)$', '', entity_name_raw, flags=re.IGNORECASE)
        
        if entity_name:
            # Capitalize first letter (Task, User, Product)
            entity_name = entity_name[0].upper() + entity_name[1:]
            classifications[entity_name] = "AGGREGATE"
            log("CLASSIFY", f"   ✅ {entity_name}: AGGREGATE (top-level array)")
    
    # ═══════════════════════════════════════════════════════════
    # RULE 2: Nested objects/arrays = EMBEDDED
    # ═══════════════════════════════════════════════════════════
    # Find property names that are objects or arrays of objects
    # BUT only if they're NOT top-level exports
    
    # Pattern: assignee: { ... }
    nested_object_pattern = r'(\w+):\s*\{[^}]{10,}\}'  # At least 10 chars to avoid empty objects
    nested_objects = set(re.findall(nested_object_pattern, content))
    
    # Pattern: tags: [{ ... }]
    nested_array_pattern = r'(\w+):\s*\[[^\]]*\{[^}]{5,}\}[^\]]*\]'
    nested_arrays = set(re.findall(nested_array_pattern, content))
    
    # Combine all nested references
    all_nested = nested_objects | nested_arrays
    
    for prop_name in all_nested:
        # Skip if it's a common property name (not an entity)
        if prop_name.lower() in ['id', 'data', 'meta', 'info', 'config', 'options', 'params']:
            continue
        
        # Capitalize (Assignee, Tag, Author, Category)
        entity_name = prop_name[0].upper() + prop_name[1:]
        
        # Only mark as EMBEDDED if NOT already marked as AGGREGATE
        if entity_name not in classifications:
            classifications[entity_name] = "EMBEDDED"
            log("CLASSIFY", f"   🔒 {entity_name}: EMBEDDED (nested only, no top-level array)")
    
    return classifications


def classify_entities_from_contracts(contracts_path: Path) -> Dict[str, str]:
    """
    Dynamically classify entities from contracts.md endpoint structure.
    
    Rules (deterministic, works with ANY entities):
    1. AGGREGATE: Has 2+ CRUD endpoints OR has POST endpoint
    2. EMBEDDED: Has only GET endpoint (read-only reference data)
    
    Returns:
        Dict mapping entity name to type
    """
    if not contracts_path.exists():
        log("CLASSIFY", "⚠️ contracts.md not found - skipping classification")
        return {}
    
    try:
        content = contracts_path.read_text(encoding="utf-8")
    except Exception as e:
        log("CLASSIFY", f"❌ Error reading contracts.md: {e}")
        return {}
    
    classifications = {}
    endpoint_counts = {}
    
    # Count CRUD operations per entity
    # Matches: GET /api/tasks, POST /api/users, DELETE /api/products/{id}
    crud_pattern = r'(GET|POST|PUT|DELETE|PATCH)\s+/api/(\w+)'
    
    for match in re.finditer(crud_pattern, content, re.IGNORECASE):
        method = match.group(1).upper()
        entity_plural = match.group(2).lower()
        
        if entity_plural not in endpoint_counts:
            endpoint_counts[entity_plural] = set()
        endpoint_counts[entity_plural].add(method)
    
    # Classify based on endpoint patterns
    for entity_plural, methods in endpoint_counts.items():
        from app.utils.entity_discovery import singularize
        entity_name = singularize(entity_plural)
        entity_name = entity_name[0].upper() + entity_name[1:]  # Capitalize
        
        # RULE: AGGREGATE if has POST (can create) OR has 3+ operations (full CRUD)
        if 'POST' in methods or len(methods) >= 3:
            classifications[entity_name] = "AGGREGATE"
            log("CLASSIFY", f"   ✅ {entity_name}: AGGREGATE ({len(methods)} endpoints: {methods})")
        
        # RULE: EMBEDDED if only GET (read-only reference)
        elif methods == {'GET'}:
            classifications[entity_name] = "EMBEDDED"
            log("CLASSIFY", f"   🔒 {entity_name}: EMBEDDED (read-only, 1 endpoint)")
        
        # Default to AGGREGATE for safety
        else:
            classifications[entity_name] = "AGGREGATE"
            log("CLASSIFY", f"   ⚠️ {entity_name}: AGGREGATE (default, {len(methods)} endpoints)")
    
    return classifications


def merge_classifications(
    mock_classifications: Dict[str, str],
    contract_classifications: Dict[str, str]
) -> Dict[str, str]:
    """
    Merge classifications from multiple sources.
    
    Priority (most reliable to least):
    1. mock.js (shows actual data structure)
    2. contracts.md (shows API design)
    
    If conflict: mock.js wins (more trustworthy)
    Default: AGGREGATE (safer than EMBEDDED)
    
    Returns:
        Final classification dict
    """
    # Start with contracts
    merged = dict(contract_classifications)
    
    # Override with mock.js (higher priority)
    for entity_name, entity_type in mock_classifications.items():
        if entity_name in merged and merged[entity_name] != entity_type:
            log("CLASSIFY", f"   🔄 {entity_name}: {merged[entity_name]} → {entity_type} (mock.js override)")
        merged[entity_name] = entity_type
    
    # Ensure all entities have a classification (default to AGGREGATE)
    all_entities = set(mock_classifications.keys()) | set(contract_classifications.keys())
    for entity_name in all_entities:
        if entity_name not in merged:
            merged[entity_name] = "AGGREGATE"
            log("CLASSIFY", f"   🔧 {entity_name}: AGGREGATE (default)")
    
    return merged


def classify_project_entities(project_path: Path) -> Dict[str, str]:
    """
    Main entry point: Classify all entities in a project.
    
    This works with ANY user prompt - completely dynamic!
    
    Returns:
        Dict mapping entity names to types: {"Task": "AGGREGATE", "Tag": "EMBEDDED"}
    """
    log("CLASSIFY", "🔍 Classifying entities from project artifacts...")
    
    # Classify from both sources
    mock_class = classify_entities_from_mock(project_path)
    contract_class = classify_entities_from_contracts(project_path / "contracts.md")
    
    # Merge with priority
    final = merge_classifications(mock_class, contract_class)
    
    if final:
        aggregates = [k for k, v in final.items() if v == "AGGREGATE"]
        embedded = [k for k, v in final.items() if v == "EMBEDDED"]
        log("CLASSIFY", f"📊 Final classification:")
        log("CLASSIFY", f"   AGGREGATE ({len(aggregates)}): {aggregates}")
        log("CLASSIFY", f"   EMBEDDED ({len(embedded)}): {embedded}")
    else:
        log("CLASSIFY", "⚠️ No entities classified (no mock.js or contracts.md found)")
    
    return final
