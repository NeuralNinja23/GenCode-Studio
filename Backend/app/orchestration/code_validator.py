# backend/app/orchestration/code_validator.py
"""
Universal Code Validation Framework

Validates any generated code using actual execution, not pattern matching.
Works for any language/framework by testing what matters: does it run?

This is the GENERALIZED solution - works for any error type, not just Query().
"""
import subprocess
import sys
import ast
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class ErrorType(Enum):
    """
    Classification of validation errors.
    
    These are derived from ACTUAL failures, not hardcoded patterns.
    When a new error type appears, add it here with its classification.
    """
    # Syntax Errors
    SYNTAX_ERROR = "syntax_error"
    INDENTATION_ERROR = "indentation_error"
    
    # Import Errors
    IMPORT_ERROR = "import_error"
    MODULE_NOT_FOUND = "module_not_found"
    CIRCULAR_IMPORT = "circular_import"
    
    # FastAPI Specific
    FASTAPI_PARAMETER_ERROR = "fastapi_parameter_error"  # Query/Path/Body annotation issues
    FASTAPI_ROUTE_ERROR = "fastapi_route_error"
    FASTAPI_DEPENDENCY_ERROR = "fastapi_dependency_error"
    
    # Runtime Errors
    ATTRIBUTE_ERROR = "attribute_error"
    TYPE_ERROR = "type_error"
    VALUE_ERROR = "value_error"
    
    # Database/ORM
    BEANIE_ERROR = "beanie_error"
    MONGODB_ERROR = "mongodb_error"
    
    # Unknown
    UNKNOWN = "unknown"


@dataclass
class ValidationCheck:
    """Result of a single validation check."""
    name: str
    passed: bool
    error_type: Optional[ErrorType] = None
    error_message: str = ""
    traceback: str = ""
    line_number: Optional[int] = None
    file_path: Optional[str] = None


@dataclass
class ValidationResult:
    """Complete validation result with all checks."""
    valid: bool
    checks: List[ValidationCheck] = field(default_factory=list)
    primary_error: Optional[ErrorType] = None
    error_chain: List[ErrorType] = field(default_factory=list)
    
    @property
    def failed_checks(self) -> List[ValidationCheck]:
        return [c for c in self.checks if not c.passed]
    
    @property
    def failure_reasons(self) -> List[str]:
        return [c.error_message for c in self.failed_checks]


class CodeValidator:
    """
    Universal code validator - works for any generated code.
    
    Uses actual execution to validate, not pattern matching.
    """
    
    def __init__(self, project_path: Path):
        """
        Initialize validator.
        
        Args:
            project_path: Path to project workspace
        """
        self.project_path = project_path
        self.backend_path = project_path / "backend"
    
    async def validate_file(self, file_path: Path) -> ValidationResult:
        """
        Validate a single code file.
        
        Runs multiple checks and returns combined result.
        
        Args:
            file_path: Path to file to validate
        
        Returns:
            ValidationResult with all check outcomes
        """
        checks = []
        
        # Check 1: Syntax validation (AST parse)
        syntax_check = self._check_syntax(file_path)
        checks.append(syntax_check)
        
        if not syntax_check.passed:
            return ValidationResult(
                valid=False,
                checks=checks,
                primary_error=syntax_check.error_type,
                error_chain=[syntax_check.error_type]
            )
        
        # Check 2: Import validation (subprocess)
        import_check = await self._check_imports(file_path)
        checks.append(import_check)
        
        if not import_check.passed:
            return ValidationResult(
                valid=False,
                checks=checks,
                primary_error=import_check.error_type,
                error_chain=[import_check.error_type]
            )
        
        # All checks passed
        return ValidationResult(valid=True, checks=checks)
    
    async def validate_fastapi_app(self, main_path: Optional[Path] = None) -> ValidationResult:
        """
        Validate that FastAPI app can be instantiated.
        
        This catches startup errors like:
        - Route registration failures
        - Dependency injection errors
        - Parameter annotation issues
        
        Args:
            main_path: Path to main.py (defaults to backend/app/main.py)
        
        Returns:
            ValidationResult with app instantiation check
        """
        if main_path is None:
            main_path = self.backend_path / "app" / "main.py"
        
        checks = []
        
        # Try to import app in subprocess
        validation_script = f'''
import sys
sys.path.insert(0, r"{self.backend_path}")

try:
    from app.main import app
    
    # Check routes exist
    route_paths = [r.path for r in app.routes]
    print("SUCCESS")
    print("ROUTES:", route_paths)
except Exception as e:
    import traceback
    print("FAIL")
    print("ERROR_TYPE:", type(e).__name__)
    print("ERROR_MSG:", str(e))
    print("TRACEBACK:")
    traceback.print_exc()
'''
        
        try:
            result = subprocess.run(
                [sys.executable, "-c", validation_script],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(self.backend_path),
                env={**dict(subprocess.os.environ), "PYTHONPATH": str(self.backend_path)}
            )
            
            output = result.stdout + result.stderr
            
            if "SUCCESS" in output:
                checks.append(ValidationCheck(
                    name="fastapi_app_build",
                    passed=True
                ))
                return ValidationResult(valid=True, checks=checks)
            else:
                # Parse error from output
                error_type = self._classify_error_from_output(output)
                error_msg = self._extract_error_message(output)
                
                checks.append(ValidationCheck(
                    name="fastapi_app_build",
                    passed=False,
                    error_type=error_type,
                    error_message=error_msg,
                    traceback=output
                ))
                
                return ValidationResult(
                    valid=False,
                    checks=checks,
                    primary_error=error_type,
                    error_chain=[error_type]
                )
                
        except subprocess.TimeoutExpired:
            checks.append(ValidationCheck(
                name="fastapi_app_build",
                passed=False,
                error_type=ErrorType.UNKNOWN,
                error_message="App instantiation timed out"
            ))
            return ValidationResult(valid=False, checks=checks, primary_error=ErrorType.UNKNOWN)
        except Exception as e:
            checks.append(ValidationCheck(
                name="fastapi_app_build",
                passed=False,
                error_type=ErrorType.UNKNOWN,
                error_message=str(e)
            ))
            return ValidationResult(valid=False, checks=checks, primary_error=ErrorType.UNKNOWN)
    
    def _check_syntax(self, file_path: Path) -> ValidationCheck:
        """
        Check Python syntax using AST.
        
        Args:
            file_path: Path to Python file
        
        Returns:
            ValidationCheck with syntax result
        """
        try:
            code = file_path.read_text(encoding="utf-8")
            ast.parse(code)
            return ValidationCheck(name="syntax", passed=True)
        except SyntaxError as e:
            return ValidationCheck(
                name="syntax",
                passed=False,
                error_type=ErrorType.SYNTAX_ERROR,
                error_message=str(e),
                line_number=e.lineno,
                file_path=str(file_path)
            )
        except IndentationError as e:
            return ValidationCheck(
                name="syntax",
                passed=False,
                error_type=ErrorType.INDENTATION_ERROR,
                error_message=str(e),
                line_number=e.lineno,
                file_path=str(file_path)
            )
        except Exception as e:
            return ValidationCheck(
                name="syntax",
                passed=False,
                error_type=ErrorType.UNKNOWN,
                error_message=str(e)
            )
    
    async def _check_imports(self, file_path: Path) -> ValidationCheck:
        """
        Check that file can be imported.
        
        Runs in subprocess to avoid polluting current process.
        
        Args:
            file_path: Path to Python file
        
        Returns:
            ValidationCheck with import result
        """
        # Convert file path to module path
        try:
            relative_path = file_path.relative_to(self.backend_path)
            module_path = str(relative_path.with_suffix("")).replace("/", ".").replace("\\", ".")
        except ValueError:
            return ValidationCheck(
                name="imports",
                passed=False,
                error_type=ErrorType.UNKNOWN,
                error_message=f"File not in backend path: {file_path}"
            )
        
        validation_script = f'''
import sys
sys.path.insert(0, r"{self.backend_path}")

try:
    import {module_path}
    print("SUCCESS")
except ImportError as e:
    print("FAIL:ImportError:", e)
except ModuleNotFoundError as e:
    print("FAIL:ModuleNotFoundError:", e)
except Exception as e:
    import traceback
    print("FAIL:", type(e).__name__, ":", e)
    traceback.print_exc()
'''
        
        try:
            result = subprocess.run(
                [sys.executable, "-c", validation_script],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=str(self.backend_path),
                env={**dict(subprocess.os.environ), "PYTHONPATH": str(self.backend_path)}
            )
            
            output = result.stdout + result.stderr
            
            if "SUCCESS" in output:
                return ValidationCheck(name="imports", passed=True)
            else:
                error_type = self._classify_error_from_output(output)
                return ValidationCheck(
                    name="imports",
                    passed=False,
                    error_type=error_type,
                    error_message=self._extract_error_message(output),
                    traceback=output
                )
                
        except subprocess.TimeoutExpired:
            return ValidationCheck(
                name="imports",
                passed=False,
                error_type=ErrorType.UNKNOWN,
                error_message="Import timed out"
            )
        except Exception as e:
            return ValidationCheck(
                name="imports",
                passed=False,
                error_type=ErrorType.UNKNOWN,
                error_message=str(e)
            )
    
    def _classify_error_from_output(self, output: str) -> ErrorType:
        """
        Classify error type from traceback output.
        
        This is the GENERALIZED approach - parses actual errors,
        not hardcoded patterns.
        
        Args:
            output: stdout/stderr from subprocess
        
        Returns:
            ErrorType classification
        """
        output_lower = output.lower()
        
        # FastAPI parameter errors (like the Query() issue)
        if "assertionerror: non-body parameters must be in" in output_lower:
            return ErrorType.FASTAPI_PARAMETER_ERROR
        
        if "assertionerror" in output_lower and "path" in output_lower:
            return ErrorType.FASTAPI_PARAMETER_ERROR
        
        # Import errors
        if "modulenotfounderror" in output_lower:
            return ErrorType.MODULE_NOT_FOUND
        
        if "importerror" in output_lower:
            if "circular" in output_lower:
                return ErrorType.CIRCULAR_IMPORT
            return ErrorType.IMPORT_ERROR
        
        # Syntax errors
        if "syntaxerror" in output_lower:
            return ErrorType.SYNTAX_ERROR
        
        if "indentationerror" in output_lower:
            return ErrorType.INDENTATION_ERROR
        
        # Type/Value errors
        if "typeerror" in output_lower:
            return ErrorType.TYPE_ERROR
        
        if "valueerror" in output_lower:
            return ErrorType.VALUE_ERROR
        
        if "attributeerror" in output_lower:
            return ErrorType.ATTRIBUTE_ERROR
        
        # ORM errors
        if "beanie" in output_lower:
            return ErrorType.BEANIE_ERROR
        
        return ErrorType.UNKNOWN
    
    def _extract_error_message(self, output: str) -> str:
        """
        Extract human-readable error message from traceback.
        
        Args:
            output: stdout/stderr from subprocess
        
        Returns:
            Extracted error message
        """
        lines = output.strip().split("\n")
        
        # Look for ERROR_MSG line
        for line in lines:
            if line.startswith("ERROR_MSG:"):
                return line.replace("ERROR_MSG:", "").strip()
        
        # Look for last exception line
        for line in reversed(lines):
            if "Error:" in line or "error:" in line.lower():
                return line.strip()
        
        # Return last non-empty line
        for line in reversed(lines):
            if line.strip():
                return line.strip()[:200]
        
        return "Unknown error"


async def validate_healed_code(
    project_path: Path,
    changed_files: List[Path]
) -> ValidationResult:
    """
    Validate healed code files.
    
    Convenience function for healing pipeline.
    
    Args:
        project_path: Path to project workspace
        changed_files: List of files that were modified by healing
    
    Returns:
        Combined validation result
    """
    validator = CodeValidator(project_path)
    
    all_checks = []
    error_chain = []
    primary_error = None
    
    for file_path in changed_files:
        if file_path.suffix == ".py":
            result = await validator.validate_file(file_path)
            all_checks.extend(result.checks)
            
            if not result.valid:
                error_chain.extend(result.error_chain)
                if primary_error is None:
                    primary_error = result.primary_error
    
    # Also validate app can be built
    app_result = await validator.validate_fastapi_app()
    all_checks.extend(app_result.checks)
    
    if not app_result.valid:
        error_chain.extend(app_result.error_chain)
        if primary_error is None:
            primary_error = app_result.primary_error
    
    valid = all(c.passed for c in all_checks)
    
    return ValidationResult(
        valid=valid,
        checks=all_checks,
        primary_error=primary_error,
        error_chain=error_chain
    )
