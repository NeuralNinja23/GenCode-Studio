# Patch to add Classification Confidence Metric to contracts.py
from pathlib import Path
import re

file_path = Path(r'C:\Users\JARVIS\Desktop\Project GenCode\GenCode Studio\Backend\app\handlers\contracts.py')
content = file_path.read_text(encoding='utf-8')

# Add helper function before _generate_entity_plan_from_contracts
helper_function = '''

def _parse_marcus_classification(contracts_content: str) -> dict:
    """
    Parse Marcus's entity classification section from contracts.md.
    
    Looks for "## Entity Classification" section and extracts Marcus's
    classification decisions.
    
    Returns:
        Dict mapping entity names to Marcus's classifications
        Example: {"Task": "AGGREGATE", "Assignee": "EMBEDDED"}
    """
    marcus_classifications = {}
    
    # Find Entity Classification section
    pattern = r'##\\s+Entity\\s+Classification(.*?)(?=##|\\Z)'
    match = re.search(pattern, contracts_content, re.DOTALL | re.IGNORECASE)
    
    if not match:
        return marcus_classifications
    
    section_content = match.group(1)
    
    # Parse each entity
    # Pattern: - **EntityName** followed by Type: AGGREGATE or EMBEDDED
    entity_pattern = r'-\\s+\\*\\*([\\w]+)\\*\\*[^-]*?Type:\\s+(AGGREGATE|EMBEDDED)'
    
    for entity_match in re.finditer(entity_pattern, section_content, re.IGNORECASE):
        entity_name = entity_match.group(1)
        entity_type = entity_match.group(2).upper()
        marcus_classifications[entity_name] = entity_type
    
    return marcus_classifications


def _calculate_classification_confidence(
    marcus_classifications: dict,
    final_classifications: dict
) -> dict:
    """
    Calculate how accurate Marcus was compared to code-based classification.
    
    Args:
        marcus_classifications: Marcus's entity type decisions
        final_classifications: Code-validated entity types
    
    Returns:
        Metrics dict with accuracy and details
    """
    if not marcus_classifications:
        return {
            "marcus_entities": {},
            "final_entities": final_classifications,
            "corrections": 0,
            "total": len(final_classifications),
            "confidence": 0.0,
            "status": "no_marcus_classification"
        }
    
    # Count corrections needed
    corrections = 0
    marcus_correct = 0
    details = []
    
    all_entities = set(marcus_classifications.keys()) | set(final_classifications.keys())
    
    for entity_name in all_entities:
        marcus_type = marcus_classifications.get(entity_name, "UNKNOWN")
        final_type = final_classifications.get(entity_name, "UNKNOWN")
        
        if marcus_type == final_type:
            marcus_correct += 1
            details.append(f"   ✅ {entity_name}: {final_type} (Marcus correct)")
        else:
            corrections += 1
            details.append(f"   🔧 {entity_name}: Marcus said {marcus_type}, corrected to {final_type}")
    
    total = len(all_entities)
    confidence = (marcus_correct / total) if total > 0 else 0.0
    
    return {
        "marcus_entities": marcus_classifications,
        "final_entities": final_classifications,
        "corrections": corrections,
        "correct": marcus_correct,
        "total": total,
        "confidence": confidence,
        "details": details,
        "status": "measured"
    }


'''

# Insert helper function before _generate_entity_plan_from_contracts
insertion_point = 'def _generate_entity_plan_from_contracts(project_path: Path) -> None:'
content = content.replace(insertion_point, helper_function + insertion_point)

# Now update the classification section to use these helpers
old_classification = '''    # ═══════════════════════════════════════════════════════════
    # FIX #3: CLASSIFY ENTITIES AS AGGREGATE OR EMBEDDED
    # ═══════════════════════════════════════════════════════════
    log("CONTRACTS", "🔍 Classifying entities (AGGREGATE vs EMBEDDED)...")
    
    from app.utils.entity_classification import classify_project_entities
    entity_types = classify_project_entities(project_path)'''

new_classification = '''    # ═══════════════════════════════════════════════════════════
    # FIX #3: CLASSIFY ENTITIES AS AGGREGATE OR EMBEDDED
    # ═══════════════════════════════════════════════════════════
    log("CONTRACTS", "🔍 Classifying entities (AGGREGATE vs EMBEDDED)...")
    
    # Parse Marcus's classification from contracts.md
    marcus_classifications = _parse_marcus_classification(content)
    
    # Get code-based classification (ground truth)
    from app.utils.entity_classification import classify_project_entities
    entity_types = classify_project_entities(project_path)
    
    # Calculate Marcus's accuracy
    confidence_metrics = _calculate_classification_confidence(
        marcus_classifications,
        entity_types
    )
    
    # Log classification confidence
    if confidence_metrics["status"] == "measured":
        correct = confidence_metrics["correct"]
        total = confidence_metrics["total"]
        confidence_pct = confidence_metrics["confidence"] * 100
        
        log("CONTRACTS", f"📊 Marcus Classification Accuracy: {correct}/{total} correct ({confidence_pct:.0f}%)")
        
        # Log details
        for detail in confidence_metrics["details"]:
            log("CONTRACTS", detail)
        
        if confidence_metrics["corrections"] == 0:
            log("CONTRACTS", "   🎯 Perfect! Marcus got all classifications correct!")
        else:
            log("CONTRACTS", f"   🔧 Code corrected {confidence_metrics['corrections']} classification(s)")
    else:
        log("CONTRACTS", "   ℹ️ Marcus did not provide Entity Classification section")
        log("CONTRACTS", "   (This is OK - code classification is authoritative)")'''

content = content.replace(old_classification, new_classification)

file_path.write_text(content, encoding='utf-8')
print("✅ Added Classification Confidence Metric!")
print("   - Parses Marcus's Entity Classification section")
print("   - Compares with code-based ground truth")
print("   - Calculates accuracy percentage")
print("   - Logs detailed feedback")
print("   - Measures Marcus as a subsystem!")
