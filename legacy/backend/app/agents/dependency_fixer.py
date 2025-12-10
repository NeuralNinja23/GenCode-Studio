"""
Dependency Auto-Fixer for Backend Testing
Detects and fixes missing Python dependencies before running tests
"""
import re
from pathlib import Path
from typing import List, Set, Tuple


def detect_missing_dependencies(error_output: str) -> Set[str]:
    """
    Parse pytest/pip error output to detect missing dependencies.
    
    Returns a set of package names that need to be installed.
    """
    missing_deps: Set[str] = set()
    
    # Pattern 1: ModuleNotFoundError: No module named 'xxx'
    module_not_found = re.findall(r"ModuleNotFoundError: No module named ['\"]([^'\"]+)['\"]", error_output)
    for module in module_not_found:
        # Convert module name to package name
        package = _module_to_package(module)
        if package:
            missing_deps.add(package)
    
    # Pattern 2: ImportError: cannot import name 'xxx' from 'yyy'
    import_errors = re.findall(r"ImportError: cannot import name ['\"]([^'\"]+)['\"] from ['\"]([^'\"]+)['\"]", error_output)
    for _, module in import_errors:
        package = _module_to_package(module)
        if package:
            missing_deps.add(package)
    
    # Pattern 3: pytest plugin errors (e.g., "async def functions are not natively supported")
    if "async def functions are not natively supported" in error_output:
        missing_deps.add("pytest-asyncio")
    
    if "Unknown pytest.mark.asyncio" in error_output:
        missing_deps.add("pytest-asyncio")
    
    # Pattern 4: Specific pytest plugin messages
    plugin_patterns = {
        "pytest-asyncio": ["anyio", "pytest-asyncio", "pytest-tornasync", "pytest-trio", "pytest-twisted"],
        "pytest-cov": ["pytest-cov"],
        "pytest-mock": ["pytest-mock"],
    }
    
    for package, keywords in plugin_patterns.items():
        if any(keyword in error_output for keyword in keywords):
            if "pytest-asyncio" in keywords and "async def functions" in error_output:
                missing_deps.add("pytest-asyncio")
    
    return missing_deps


def _module_to_package(module_name: str) -> str:
    """
    Convert Python module name to pip package name.
    
    Common mappings for packages where module != package name.
    """
    # Remove any submodule paths (e.g., 'fastapi.routing' -> 'fastapi')
    base_module = module_name.split('.')[0]
    
    # Known module -> package mappings
    mappings = {
        "cv2": "opencv-python",
        "PIL": "Pillow",
        "sklearn": "scikit-learn",
        "yaml": "PyYAML",
        "dotenv": "python-dotenv",
        "jose": "python-jose",
        "passlib": "passlib",
        "pydantic_settings": "pydantic-settings",
        "motor": "motor",
        "beanie": "beanie",
        "httpx": "httpx",
        "pytest": "pytest",
        "asyncio": "",  # Built-in, no package needed
        "typing": "",  # Built-in
        "pathlib": "",  # Built-in
        "json": "",  # Built-in
        "os": "",  # Built-in
        "sys": "",  # Built-in
        "re": "",  # Built-in
    }
    
    return mappings.get(base_module, base_module)


def add_dependencies_to_requirements(
    requirements_path: Path,
    new_deps: Set[str],
    version_hints: dict = None
) -> Tuple[bool, List[str]]:
    """
    Add missing dependencies to requirements.txt.
    
    Args:
        requirements_path: Path to requirements.txt
        new_deps: Set of package names to add
        version_hints: Optional dict of package -> version string
    
    Returns:
        (modified: bool, added_packages: List[str])
    """
    if not new_deps:
        return False, []
    
    # Default version hints for common packages
    default_versions = {
        "pytest": ">=9.0.0",
        "pytest-asyncio": ">=0.24.0",
        "httpx": ">=0.27.0",
        "pytest-cov": ">=4.1.0",
        "pytest-mock": ">=3.12.0",
        "motor": ">=3.6.0",
        "beanie": ">=1.26.0",
        "pydantic-settings": ">=2.2.0",
        "python-jose": ">=3.3.0",
        "passlib": ">=1.7.4",
    }
    
    version_hints = version_hints or {}
    all_versions = {**default_versions, **version_hints}
    
    # Read existing requirements
    if requirements_path.exists():
        existing_content = requirements_path.read_text(encoding="utf-8")
        existing_lines = existing_content.strip().split("\n")
    else:
        existing_lines = []
    
    # Parse existing packages (handle comments and version specifiers)
    existing_packages = set()
    for line in existing_lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Extract package name (before any version specifier)
        pkg_name = re.split(r'[=<>!]', line)[0].strip()
        existing_packages.add(pkg_name.lower())
    
    # Add new dependencies that don't exist
    added = []
    new_lines = []
    
    for dep in sorted(new_deps):
        if not dep:  # Skip empty strings (built-in modules)
            continue
        
        if dep.lower() not in existing_packages:
            version = all_versions.get(dep, "")
            if version:
                new_lines.append(f"{dep}{version}")
            else:
                new_lines.append(dep)
            added.append(dep)
    
    if not added:
        return False, []
    
    # Write updated requirements.txt
    updated_content = "\n".join(existing_lines + new_lines) + "\n"
    requirements_path.write_text(updated_content, encoding="utf-8")
    
    return True, added


def auto_fix_backend_dependencies(
    project_path: Path,
    error_output: str
) -> Tuple[bool, List[str]]:
    """
    Automatically detect and fix missing backend dependencies.
    
    Args:
        project_path: Path to project workspace
        error_output: Combined stdout/stderr from pytest or pip
    
    Returns:
        (fixed: bool, added_packages: List[str])
    """
    requirements_path = project_path / "backend" / "requirements.txt"
    
    # Detect missing dependencies from error output
    missing_deps = detect_missing_dependencies(error_output)
    
    if not missing_deps:
        return False, []
    
    # Add them to requirements.txt
    modified, added = add_dependencies_to_requirements(requirements_path, missing_deps)
    
    return modified, added
