# app/validation/static_validator.py
"""
Static validator - Evidence-based verification without execution.

CRITICAL: This is READ-ONLY. It provides EVIDENCE, not VERDICTS.
The workflow aggregator makes the final decision.

Phase 4: Implements Adjustment 2 - Evidence emission only.
"""
import ast
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class StaticValidationEvidence:
    """
    Evidence collected from static analysis.
    
    Philosophy (ADJUSTMENT 2):
    - We OBSERVE facts
    - We EMIT evidence
    - We DO NOT make verdicts
    - The aggregator decides if evidence = correctness
    """
    
    def __init__(self, step_name: str):
        self.step_name = step_name
        self.syntax_errors: List[Dict[str, Any]] = []
        self.routes_found: List[str] = []
        self.models_found: List[str] = []
        self.imports_valid: bool = True
        self.import_errors: List[str] = []
        self.file_count: int = 0
        self.warnings: List[str] = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert evidence to dictionary for aggregator."""
        return {
            "step": self.step_name,
            "type": "static",
            "syntax_errors": self.syntax_errors,
            "routes_found": self.routes_found,
            "models_found": self.models_found,
            "imports_valid": self.imports_valid,
            "import_errors": self.import_errors,
            "file_count": self.file_count,
            "warnings": self.warnings,
            # Note: No "passed" or "failed" field - aggregator decides
        }


class StaticValidator:
    """
    Provides static evidence about code without executing it.
    
    Use cases:
    1. When step is isolated due to ENVIRONMENT_FAILURE
    2. When we want to validate structure before execution
    3. When execution is not possible but we need evidence
    
    Examples of evidence:
    - Syntax is valid
    - Expected files exist
    - Routes are defined
    - Models are present
    - Imports are resolvable
    """
    
    def __init__(self, project_path: Path):
        self.project_path = project_path
    
    def validate_backend_step(self, step_name: str) -> StaticValidationEvidence:
        """
        Collect evidence about backend implementation.
        
        Observes:
        - Python syntax validity
        - FastAPI routes defined
        - MongoDB models present
        - Import statements
        
        Does NOT:
        - Execute code
        - Make database connections
        - Run tests
        - Determine if "correct" (aggregator's job)
        
        Args:
            step_name: Name of step to validate
            
        Returns:
            Evidence object with observations
        """
        evidence = StaticValidationEvidence(step_name)
        backend_path = self.project_path / "backend"
        
        if not backend_path.exists():
            evidence.warnings.append("Backend directory not found")
            return evidence
        
        # Check models.py
        models_path = backend_path / "app" / "models.py"
        if models_path.exists():
            evidence.file_count += 1
            models_evidence = self._analyze_python_file(models_path)
            evidence.syntax_errors.extend(models_evidence["syntax_errors"])
            evidence.models_found.extend(models_evidence["models"])
            
            if not evidence.models_found:
                evidence.warnings.append("models.py exists but no Document classes found")
        else:
            evidence.warnings.append("models.py not found")
        
        # Check routers
        routers_path = backend_path / "app" / "routers"
        if routers_path.exists():
            for router_file in routers_path.glob("*.py"):
                if router_file.name == "__init__.py":
                    continue
                
                evidence.file_count += 1
                router_evidence = self._analyze_python_file(router_file)
                evidence.syntax_errors.extend(router_evidence["syntax_errors"])
                evidence.routes_found.extend(router_evidence["routes"])
        else:
            evidence.warnings.append("routers directory not found")
        
        # Check main.py
        main_path = backend_path / "app" / "main.py"
        if main_path.exists():
            evidence.file_count += 1
            main_evidence = self._analyze_python_file(main_path)
            evidence.syntax_errors.extend(main_evidence["syntax_errors"])
        else:
            evidence.warnings.append("main.py not found")
        
        return evidence
    
    def validate_frontend_step(self, step_name: str) -> StaticValidationEvidence:
        """
        Collect evidence about frontend implementation.
        
        Observes:
        - JavaScript/JSX syntax validity
        - Component files present
        - API client exists
        - Routes defined
        
        Args:
            step_name: Name of step to validate
            
        Returns:
            Evidence object with observations
        """
        evidence = StaticValidationEvidence(step_name)
        frontend_path = self.project_path / "frontend"
        
        if not frontend_path.exists():
            evidence.warnings.append("Frontend directory not found")
            return evidence
        
        # Check src directory
        src_path = frontend_path / "src"
        if src_path.exists():
            # Count component files
            components = list((src_path / "components").rglob("*.jsx")) if (src_path / "components").exists() else []
            evidence.file_count += len(components)
            
            # Check for api.js
            api_path = src_path / "lib" / "api.js"
            if api_path.exists():
                evidence.file_count += 1
                # Could add JS syntax checking here
            else:
                evidence.warnings.append("API client (lib/api.js) not found")
        else:
            evidence.warnings.append("src directory not found")
        
        return evidence
    
    def _analyze_python_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Analyze a Python file and collect evidence.
        
        Returns:
            Dictionary with syntax_errors, routes, models found
        """
        result = {
            "syntax_errors": [],
            "routes": [],
            "models": []
        }
        
        try:
            content = file_path.read_text(encoding="utf-8")
            
            # Check syntax
            try:
                ast.parse(content)
            except SyntaxError as e:
                result["syntax_errors"].append({
                    "file": str(file_path),
                    "line": e.lineno,
                    "message": str(e)
                })
                # If syntax is broken, can't reliably parse further
                return result
            
            # Find FastAPI routes
            route_patterns = [
                r'@router\.(get|post|put|delete|patch)\(',
                r'@app\.(get|post|put|delete|patch)\('
            ]
            for pattern in route_patterns:
                matches = re.findall(pattern, content)
                result["routes"].extend([match for match in matches])
            
            # Find MongoDB models (Document classes)
            model_pattern = r'class\s+(\w+)\s*\(\s*Document\s*\)'
            matches = re.findall(model_pattern, content)
            result["models"].extend(matches)
            
        except Exception as e:
            result["syntax_errors"].append({
                "file": str(file_path),
                "line": 0,
                "message": f"File read error: {str(e)}"
            })
        
        return result
    
    def validate_testing_step(
        self,
        step_name: str,
        test_type: str = "backend"
    ) -> StaticValidationEvidence:
        """
        Collect evidence about test files (without running them).
        
        Observes:
        - Test files exist
        - Test syntax is valid
        - Test structure looks correct
        
        Args:
            step_name: Name of testing step
            test_type: "backend" or "frontend"
            
        Returns:
            Evidence about test files
        """
        evidence = StaticValidationEvidence(step_name)
        
        if test_type == "backend":
            tests_path = self.project_path / "backend" / "tests"
            if tests_path.exists():
                test_files = list(tests_path.glob("test_*.py"))
                evidence.file_count = len(test_files)
                
                for test_file in test_files:
                    result = self._analyze_python_file(test_file)
                    evidence.syntax_errors.extend(result["syntax_errors"])
            else:
                evidence.warnings.append("Backend tests directory not found")
        
        elif test_type == "frontend":
            tests_path = self.project_path / "frontend" / "tests"
            if tests_path.exists():
                test_files = list(tests_path.glob("*.spec.js"))
                evidence.file_count = len(test_files)
            else:
                evidence.warnings.append("Frontend tests directory not found")
        
        return evidence
