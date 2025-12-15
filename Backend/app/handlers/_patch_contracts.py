# Patch script to add entity classification to contracts.py
import re
from pathlib import Path

contracts_file = Path(r'C:\Users\JARVIS\Desktop\Project GenCode\GenCode Studio\Backend\app\handlers\contracts.py')

content = contracts_file.read_text(encoding='utf-8')

# Patch 1: Update docstring
content = content.replace(
    '''    """
    Auto-generate entity_plan.json by parsing contracts.md.
    
    DYNAMIC DETECTION:
    - CRUD entities: Have POST/PUT/DELETE + standard paths (/api/expenses)
    - Namespaces: Only GET + nested paths (/api/dashboard/stats)
    
    Only generates entities for true CRUD resources.
    """''',
    '''    """
    Auto-generate entity_plan.json by parsing contracts.md.
    
    DYNAMIC DETECTION:
    - CRUD entities: Have POST/PUT/DELETE + standard paths (/api/expenses)
    - Namespaces: Only GET + nested paths (/api/dashboard/stats)
    
    FIX #2, #3, #4: NOW CLASSIFIES ENTITIES AS AGGREGATE OR EMBEDDED!
    - Uses mock.js structure to identify nested vs top-level entities
    - Uses contracts.md patterns to determine CRUD vs readonly
    - Removes embedded entity sections from contracts.md after classification
    
    Only generates entities for true CRUD resources.
    """'''
)

# Patch 2: Add classification before creating EntitySpec instances
old_entity_creation = '''    # Create EntitySpec for each CRUD entity
    entities = []
    for i, plural in enumerate(sorted(crud_entities)):
        singular = singularize(plural)
        entities.append(EntitySpec(
            name=singular.capitalize(),
            plural=plural,
            description=f"Auto-detected CRUD entity from contracts.md",
            fields=[],  # Fields will be inferred by Derek from contracts.md
            is_primary=(i == 0),  # First entity is primary
            generation_order=i + 1
        ))'''

new_entity_creation = '''    # ═══════════════════════════════════════════════════════════
    # FIX #3: CLASSIFY ENTITIES AS AGGREGATE OR EMBEDDED
    # ═══════════════════════════════════════════════════════════
    log("CONTRACTS", "🔍 Classifying entities (AGGREGATE vs EMBEDDED)...")
    
    from app.utils.entity_classification import classify_project_entities
    entity_types = classify_project_entities(project_path)
    
    # Create EntitySpec for each CRUD entity
    entities = []
    for i, plural in enumerate(sorted(crud_entities)):
        singular = singularize(plural)
        entity_name = singular.capitalize()
        
        # Determine entity type from classification
        entity_type = entity_types.get(entity_name, "AGGREGATE")  # Default to AGGREGATE
        
        entities.append(EntitySpec(
            name=entity_name,
            plural=plural,
            type=entity_type,  # NEW: Add classification!
            description=f"Auto-detected from contracts.md ({entity_type} entity)",
            fields=[],  # Fields will be inferred by Derek from contracts.md
            is_primary=(i == 0),  # First entity is primary
            generation_order=i + 1
        ))'''

content = content.replace(old_entity_creation, new_entity_creation)

# Patch 3: Update logging and add rewrite logic
old_logging = '''    log("CONTRACTS", f"✅ Generated entity_plan.json with {len(entities)} entities: {[e.name for e in entities]}")
    if namespaces:
        log("CONTRACTS", f"   ℹ️ Excluded {len(namespaces)} namespaces: {sorted(namespaces)}")'''

new_logging = '''    aggregates = [e.name for e in entities if e.type == "AGGREGATE"]
    embedded = [e.name for e in entities if e.type == "EMBEDDED"]
    
    log("CONTRACTS", f"✅ Generated entity_plan.json with {len(entities)} entities:")
    if aggregates:
        log("CONTRACTS", f"   📊 AGGREGATE ({len(aggregates)}): {aggregates}")
    if embedded:
        log("CONTRACTS", f"   🔒 EMBEDDED ({len(embedded)}): {embedded}")
    if namespaces:
        log("CONTRACTS", f"   ℹ️ Excluded {len(namespaces)} namespaces: {sorted(namespaces)}")
    
    # ═══════════════════════════════════════════════════════════
    # FIX #4: REWRITE CONTRACTS.MD TO REMOVE EMBEDDED ENTITIES
    # ═══════════════════════════════════════════════════════════
    if embedded:
        log("CONTRACTS", f"🗑️ Removing {len(embedded)} EMBEDDED entity sections from contracts.md...")
        _remove_embedded_from_contracts(contracts_file, embedded, plan)


def _remove_embedded_from_contracts(
    contracts_path: Path,
    embedded_names: List[str],
    entity_plan: "EntityPlan"
) -> None:
    """
    FIX #4: Remove endpoint sections for EMBEDDED entities from contracts.md.
    
    Example: Remove "### Assignee Endpoints" section if Assignee is EMBEDDED.
    This prevents Derek from generating routers for nested models!
    """
    if not contracts_path.exists():
        return
    
    try:
        import re
        content = contracts_path.read_text(encoding="utf-8")
        original_length = len(content)
        
        # Get plural forms for embedded entities
        embedded_plurals = [
            e.plural for e in entity_plan.entities 
            if e.name in embedded_names
        ]
        
        # Remove sections for embedded entities 
        # Pattern: ### ENTITY Endpoints ... (until next ### or end)
        for entity_name in embedded_names + embedded_plurals:
            # Try multiple patterns
            patterns = [
                rf'###\\s+{re.escape(entity_name)}.*?Endpoints.*?(?=###|\\Z)',  # ### Assignee Endpoints
                rf'##\\s+{re.escape(entity_name)}.*?(?=##|\\Z)',  # ## Assignee
                rf'#{1,3}\\s+{re.escape(entity_name.capitalize())}.*?(?=#{1,3}|\\Z)',  # Capitalized variations
            ]
            
            for pattern in patterns:
                before = len(content)
                content = re.sub(pattern, '', content, flags=re.DOTALL | re.IGNORECASE)
                if len(content) < before:
                    removed = before - len(content)
                    log("CONTRACTS", f"   ✂️ Removed {entity_name} section ({removed} chars)")
        
        # Clean up multiple blank lines
        content = re.sub(r'\\n{4,}', '\\n\\n\\n', content)
        
        # Write back if changed
        if len(content) < original_length:
            contracts_path.write_text(content, encoding="utf-8")
            removed_total = original_length - len(content)
            log("CONTRACTS", f"   ✅ Rewrote contracts.md (removed {removed_total} chars from embedded entities)")
        else:
            log("CONTRACTS", f"   ℹ️ No embedded entity sections found to remove")
        
    except Exception as e:
        log("CONTRACTS", f"   ⚠️ Failed to rewrite contracts.md: {e}")'''

content = content.replace(old_logging, new_logging)

# Write patched content
contracts_file.write_text(content, encoding='utf-8')
print("✅ Successfully patched contracts.py with entity classification logic!")
print("   - Updated docstring")
print("   - Added classify_project_entities() call")
print("   - Added _remove_embedded_from_contracts() function")
