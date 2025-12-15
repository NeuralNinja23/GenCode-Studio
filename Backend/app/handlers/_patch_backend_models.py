# Patch to add entity type awareness to model generation
from pathlib import Path
import re

file_path = Path(r'C:\Users\JARVIS\Desktop\Project GenCode\GenCode Studio\Backend\app\handlers\backend_models.py')
content = file_path.read_text(encoding='utf-8')

# Find and replace the section
old_section = '''    models_code = []
    
    for model_def in model_spec.get("models", []):
        name = model_def["name"]'''

new_section = '''    models_code = []
    
    # Build entity type lookup map
    entity_type_map = {e.name: e.type for e in entities}
    
    for model_def in model_spec.get("models", []):
        name = model_def["name"]
        
        # FIX #5: Determine if this entity is AGGREGATE or EMBEDDED
        entity_type = entity_type_map.get(name, "AGGREGATE")  # Default to AGGREGATE
        is_aggregate = (entity_type == "AGGREGATE")'''

content = content.replace(old_section, new_section)

# Replace the model generation template
old_template = '''        # Document class (database model)
        model_code = f\'''
class {name}(Document):
    \"\"\"{description}\"\"\"
{doc_fields_str}
    
    class Settings:
        name = "{table_name}"


class {name}Create(BaseModel):'''

new_template = '''        # Generate model code based on entity type
        if is_aggregate:
            # AGGREGATE: Document class (Beanie collection with Settings)
            model_code = f\'''
class {name}(Document):
    \"\"\"{description} (AGGREGATE - Beanie Document)\"\"\"
{doc_fields_str}
    
    class Settings:
        name = "{table_name}"

\'''
        else:
            # EMBEDDED: BaseModel (nested object, no Settings)
            model_code = f\'''
class {name}(BaseModel):
    \"\"\"{description} (EMBEDDED - Pydantic BaseModel)\"\"\"
{doc_fields_str}

\'''
        
        # Always add Create and Response schemas
        model_code += f\'''
class {name}Create(BaseModel):'''

content = content.replace(old_template, new_template)

file_path.write_text(content, encoding='utf-8')
print("✅ Successfully patched backend_models.py!")
print("   - Added entity type lookup")
print("   - AGGREGATE entities inherit from Document")
print("   - EMBEDDED entities inherit from BaseModel")
