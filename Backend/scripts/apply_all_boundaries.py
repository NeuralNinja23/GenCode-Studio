#!/usr/bin/env python3
"""
Quick script to apply @FailureBoundary.enforce to all remaining handlers.
Run this from Backend directory.
"""
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).parent.parent / 'app' / 'handlers'

# All handlers that need the decorator (file, function_name, line_approx)
HANDLERS = [
    ('architecture.py', 'step_architecture'),
    ('backend.py', 'step_backend_implementation'),
    ('backend.py', 'step_system_integration'),
    ('backend_models.py', 'step_backend_models'),
    ('contracts.py', 'step_contracts'),
    ('frontend_integration.py', 'step_frontend_integration'),
    ('frontend_mock.py', 'step_frontend_mock'),
    ('preview.py', 'step_preview_final'),
    ('refine.py', 'step_refine'),
    ('screenshot_verify.py', 'step_screenshot_verify'),
    ('testing_frontend.py', 'step_testing_frontend'),
]

def apply_to_file(filepath: Path, function_names: list[str]):
    """Apply import and decorator to a file."""
    content = filepath.read_text(encoding='utf-8')
    
    # Check if import already exists
    has_import = 'from app.core.failure_boundary import FailureBoundary' in content
    
    # Add import if needed
    if not has_import:
        lines = content.split('\n')
        # Find last import line
        last_import = 0
        for i, line in enumerate(lines):
            if line.startswith(('import ', 'from ')):
                last_import = i
        
        # Insert after last import
        lines.insert(last_import + 1, '')
        lines.insert(last_import + 2, '# Phase 0: Failure Boundary Enforcement')
        lines.insert(last_import + 3, 'from app.core.failure_boundary import FailureBoundary')
        content = '\n'.join(lines)
        print(f"  ✓ Added import to {filepath.name}")
    
    # Add decorators
    for func_name in function_names:
        pattern = rf'(async def {func_name}\()'
        if re.search(pattern, content):
            # Check if already has decorator
            decorator_pattern = rf'@FailureBoundary\.enforce\s+async def {func_name}'
            if not re.search(decorator_pattern, content):
                content = re.sub(pattern, rf'@FailureBoundary.enforce\nasync def {func_name}(', content)
                print(f"  ✓ Added decorator to {func_name}")
    
    filepath.write_text(content, encoding='utf-8')

def main():
    print("🔧 Applying @FailureBoundary.enforce to all handlers...\n")
    
    # Group by file
    file_funcs = {}
    for filename, funcname in HANDLERS:
        if filename not in file_funcs:
            file_funcs[filename] = []
        file_funcs[filename].append(funcname)
    
    for filename, funcnames in file_funcs.items():
        filepath = BACKEND_PATH / filename
        if filepath.exists():
            print(f"📄 {filename}")
            apply_to_file(filepath, funcnames)
        else:
            print(f"  ⚠ Not found: {filename}")
    
    print(f"\n✅ Complete! Applied to {len(file_funcs)} files")

if __name__ == '__main__':
    main()
