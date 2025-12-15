# Patch to add full learning loop to Marcus
from pathlib import Path
import re

file_path = Path(r'C:\Users\JARVIS\Desktop\Project GenCode\GenCode Studio\Backend\app\handlers\contracts.py')
content = file_path.read_text(encoding='utf-8')

# ========================================
# STEP 1: Inject Learned Examples into Marcus's Prompt
# ========================================

# Find where Marcus's prompt starts
old_prompt_start = '''═══════════════════════════════════════════════════════
🎯 ENTITY CLASSIFICATION RULES (CRITICAL!)
═══════════════════════════════════════════════════════

Before creating API endpoints, you MUST classify each entity correctly:'''

new_prompt_start = '''═══════════════════════════════════════════════════════
🧠 LEARNED EXAMPLES (from past successful classifications)
═══════════════════════════════════════════════════════

{learned_examples_section}

═══════════════════════════════════════════════════════
🎯 ENTITY CLASSIFICATION RULES (CRITICAL!)
═══════════════════════════════════════════════════════

Before creating API endpoints, you MUST classify each entity correctly:'''

content = content.replace(old_prompt_start, new_prompt_start)

# ========================================
# STEP 2: Load learned examples before calling LLM
# ========================================

old_llm_call_prep = '''    # Broadcast Marcus started
    await broadcast_agent_log(
        manager,
        project_id,
        "AGENT:Marcus",
        f"Analyzing frontend mock data to define API contracts for {intent.get('domain', 'app')}..."
    )
    
    try:'''

new_llm_call_prep = '''    # ═══════════════════════════════════════════════════════════
    # LEARNING LOOP: Load successful examples from past classifications
    # ═══════════════════════════════════════════════════════════
    learned_examples_section = ""
    try:
        from app.arbormind.metrics_collector import (
            get_successful_classification_examples,
            get_classification_accuracy_stats
        )
        
        examples = get_successful_classification_examples(limit=5)
        stats = get_classification_accuracy_stats()
        
        if examples:
            examples_text = []
            for ex in examples:
                examples_text.append(f"""
- **{ex['entity']}** classified as **{ex['type']}**
  - Evidence: {ex['mock_evidence']}
""")
            
            learned_examples_section = f"""
Marcus, you have classified {stats['total']} entities so far with {stats['accuracy']:.0f}% accuracy.
Here are {len(examples)} recent successful classifications to learn from:

{''.join(examples_text)}

Use these patterns to guide your classification!
"""
            log("CONTRACTS", f"📚 Loaded {len(examples)} learned examples for Marcus (overall accuracy: {stats['accuracy']:.0f}%)")
        else:
            learned_examples_section = "No learned examples yet. This is your first classification!"
            
    except Exception as learn_err:
        log("CONTRACTS", f"⚠️ Could not load learned examples: {learn_err}")
        learned_examples_section = "(Learning system initializing...)"
    
    # Format the prompt with learned examples
    contracts_prompt = contracts_prompt.format(learned_examples_section=learned_examples_section)
    
    # Broadcast Marcus started
    await broadcast_agent_log(
        manager,
        project_id,
        "AGENT:Marcus",
        f"Analyzing frontend mock data to define API contracts for {intent.get('domain', 'app')}..."
    )
    
    try:'''

content = content.replace(old_llm_call_prep, new_llm_call_prep)

# ========================================
# STEP 3: Store classification decisions after generation
# ========================================

old_classification_section = '''    # Log classification confidence
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

new_classification_section = '''    # Log classification confidence
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
        log("CONTRACTS", "   (This is OK - code classification is authoritative)")
    
    # ═══════════════════════════════════════════════════════════
    # LEARNING LOOP: Store classification decisions in database
    # ═══════════════════════════════════════════════════════════
    try:
        from app.arbormind.metrics_collector import store_classification_decision
        
        # Store each classification decision for learning
        all_entities = set(marcus_classifications.keys()) | set(entity_types.keys())
        
        for entity_name in all_entities:
            marcus_type = marcus_classifications.get(entity_name)
            final_type = entity_types.get(entity_name, "UNKNOWN")
            
            # Extract evidence from mock.js and contracts
            mock_evidence = f"(structure analysis needed)"
            contracts_evidence = f"endpoints: {endpoint_groups.get(entity_name.lower() + 's', {}).get('methods', set())}"
            
            store_classification_decision(
                project_id=project_id,
                entity_name=entity_name,
                marcus_classification=marcus_type,
                final_classification=final_type,
                mock_evidence=mock_evidence,
                contracts_evidence=contracts_evidence
            )
        
        log("CONTRACTS", f"💾 Stored {len(all_entities)} classification decisions for learning")
        
    except Exception as store_err:
        log("CONTRACTS", f"⚠️ Failed to store classifications: {store_err}")'''

content = content.replace(old_classification_section, new_classification_section)

file_path.write_text(content, encoding='utf-8')
print("✅ Full Learning Loop Implemented!")
print("   - Marcus receives learned examples in his prompt")
print("   - Classifications are stored in ArborMind database")
print("   - Marcus improves from past successes!")
print("   - Historical accuracy tracking enabled")
