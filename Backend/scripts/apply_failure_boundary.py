# scripts/apply_failure_boundary.py
"""
Script to apply @FailureBoundary.enforce decorator to all handler functions.

This is part of Phase 0.2 - applying the boundary to all handlers.
"""
import re
from pathlib import Path

# Handlers to update (main step handlers)
HANDLERS_TO_UPDATE = [
    ('testing_backend.py', 'step_testing_backend'),
    ('testing_frontend.py', 'step_testing_frontend'),
    ('backend_models.py', 'step_backend_models'),
    ('screenshot_verify.py', 'step_screenshot_verify'),
    ('preview.py', 'step_preview'),
    ('refine.py', 'step_refine'),
    ('backend.py', 'step_backend'),
   ('contracts.py', 'step_contracts'),
    ('architecture.py', 'step_architecture'),
    ('analysis.py', 'step_analysis'),

    ('frontend_mock.py', 'step_frontend_mock'),
]

def add_import_and_decorator(file_path: Path, function_name: str) -> bool:
    """
    Add import and decorator to a handler file.
    
    Returns:
        True if changes were made
    """
    content = file_path.read_text(encoding='utf-8')
    
    # Check if already has the import
    has_import = 'from app.core.failure_boundary import FailureBoundary' in content
    
    # Check if function already has decorator
    decorator_pattern = rf'@FailureBoundary\.enforce\s+async def {function_name}'
    has_decorator = bool(re.search(decorator_pattern, content))
    
    if has_import and has_decorator:
        print(f"✓ {file_path.name} already has boundary")
        return False
    
    # Add import if needed
    if not has_import:
        # Find the last import statement
        lines = content.split('\n')
        last_import_idx = 0
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                last_import_idx = i
        
        # Insert the import after the last import
        lines.insert(last_import_idx + 1, 'from app.core.failure_boundary import FailureBoundary')
        content = '\n'.join(lines)
        print(f"  + Added import to {file_path.name}")
    
    # Add decorator if needed
    if not has_decorator:
        # Find the function definition
        function_pattern = rf'(async def {function_name}\()'
        match = re.search(function_pattern, content)
        
        if match:
            # Insert decorator before function
            pos = match.start()
            content = content[:pos] + f'@FailureBoundary.enforce\n' + content[pos:]
            print(f"  + Added decorator to {function_name} in {file_path.name}")
        else:
            print(f"  ⚠ Could not find function {function_name} in {file_path.name}")
            return False
    
    # Write back
    file_path.write_text(content, encoding='utf-8')
    return True

def main():
    """Apply failure boundary to all handlers."""
    backend_path = Path(__file__).parent.parent / 'Backend' / 'app' / 'handlers'
    
    print("🔧 Applying @FailureBoundary.enforce to all handlers...\n")
    
    updated_count = 0
    for filename, func_name in HANDLERS_TO_UPDATE:
        file_path = backend_path / filename
        if file_path.exists():
            if add_import_and_decorator(file_path, func_name):
                updated_count += 1
        else:
            print(f"  ⚠ File not found: {filename}")
    
    print(f"\n✅ Updated {updated_count} handlers")

if __name__ == '__main__':
    main()
