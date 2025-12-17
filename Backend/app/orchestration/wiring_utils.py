# app/orchestration/wiring_utils.py
"""
Wiring Utilities - Handles injection of content into main.py.

This is the SINGLE SOURCE OF TRUTH for:
- Registering Routers (imports + include_router)
- Registering Models (imports + document_models)

HARD GUARANTEE:
- NO file is written without passing Unicode normalization + AST validation
- NO direct write bypass exists
"""

from pathlib import Path
import re
import ast
from app.core.logging import log
from app.validation.syntax_validator import validate_syntax


# ─────────────────────────────────────────────────────────────
# INTERNAL SAFE WRITE (INFRASTRUCTURE-GRADE)
# ─────────────────────────────────────────────────────────────

def _safe_write_validated_python(path: Path, content: str) -> None:
    """
    Apply the SAME validation gate as LLM output:
    - Unicode normalization
    - AST validation
    """
    # validate_syntax returns a ValidationResult object
    result = validate_syntax(str(path), content)
    valid = result.valid
    error = result.errors[0] if result.errors else None
    fixed_content = result.fixed_content if result.fixed_content else content

    if not valid:
        raise RuntimeError(
            f"WIRING BLOCKED: Validation failed for {path}\n{error}"
        )

    path.write_text(fixed_content, encoding="utf-8")


# ─────────────────────────────────────────────────────────────
# ROUTER WIRING
# ─────────────────────────────────────────────────────────────

def wire_router(project_path: Path, router_name: str) -> bool:
    """
    Ensure router is wired in main.py (idempotent).
    """
    main_path = project_path / "backend" / "app" / "main.py"
    if not main_path.exists():
        log("WIRING", f"⚠️ main.py not found at {main_path}")
        return False

    content = main_path.read_text(encoding="utf-8")
    original_content = content

    # Detect existing imports
    import_variants = [
        f"from app.routers import {router_name}",
        f"from app.routers.{router_name} import router",
        f"from app.routers.{router_name} import router as {router_name}_router",
    ]
    router_already_imported = any(v in content for v in import_variants)

    # Detect existing registrations
    register_variants = [
        f"include_router({router_name}.router",
        f"include_router({router_name}_router",
    ]
    router_already_registered = any(v in content for v in register_variants)

    # Insert import
    if not router_already_imported:
        import_line = f"from app.routers import {router_name}"
        if "# @ROUTER_IMPORTS" in content:
            content = re.sub(
                r'^(# @ROUTER_IMPORTS[^\n]*)\n',
                f'\\1\n{import_line}\n',
                content,
                count=1,
                flags=re.MULTILINE,
            )
        else:
            content = content.replace(
                "from app.core.config import settings",
                f"from app.core.config import settings\n{import_line}",
            )

    # Insert registration
    if not router_already_registered:
        include_line = (
            f"app.include_router("
            f"{router_name}.router, "
            f"prefix='/api/{router_name}', "
            f"tags=['{router_name}']"
            f")"
        )

        if "# @ROUTER_REGISTER" in content:
            content = re.sub(
                r'^(# @ROUTER_REGISTER[^\n]*)\n',
                f'\\1\n{include_line}\n',
                content,
                count=1,
                flags=re.MULTILINE,
            )
        elif "@app.get" in content:
            content = re.sub(
                r'(@app\.get)',
                f'{include_line}\n\n\\1',
                content,
                count=1,
            )
        else:
            content += f"\n\n{include_line}\n"

    if content != original_content:
        _safe_write_validated_python(main_path, content)
        log("WIRING", f"✅ Wired router: {router_name}")
        return True

    return False


# ─────────────────────────────────────────────────────────────
# MODEL WIRING
# ─────────────────────────────────────────────────────────────

def wire_model(project_path: Path, model_name: str) -> bool:
    """
    Ensure model is imported AND registered in document_models list in main.py.

    CRITICAL FOR BEANIE ODM.
    """
    main_path = project_path / "backend" / "app" / "main.py"
    if not main_path.exists():
        log("WIRING", f"⚠️ main.py not found at {main_path}")
        return False

    content = main_path.read_text(encoding="utf-8")
    original_content = content

    # ── Ensure import ─────────────────────────────────────────
    import_line = f"from app.models import {model_name}"
    if import_line not in content:
        if "# @MODEL_IMPORTS" in content:
            content = re.sub(
                r'^(# @MODEL_IMPORTS[^\n]*)\n',
                f'\\1\n{import_line}\n',
                content,
                count=1,
                flags=re.MULTILINE,
            )
        elif "from app.core.config import settings" in content:
            content = content.replace(
                "from app.core.config import settings",
                f"from app.core.config import settings\n{import_line}",
            )
        else:
            content = import_line + "\n" + content

        log("WIRING", f"✅ Added import: {import_line}")

    # ── Ensure document_models registration ───────────────────
    match = re.search(
        r'^(\s*)document_models\s*=\s*\[(.*?)\]',
        content,
        re.MULTILINE | re.DOTALL,
    )

    if match:
        indent = match.group(1)
        current_list = match.group(2).strip()

        if model_name not in current_list:
            new_list = (
                f"{current_list}, {model_name}" if current_list else model_name
            )
            content = content.replace(
                match.group(0),
                f"{indent}document_models = [{new_list}]",
            )
            log("WIRING", f"✅ Added {model_name} to document_models")
    else:
        raise RuntimeError(
            "WIRING FAILURE: document_models list not found in main.py"
        )

    if content != original_content:
        _safe_write_validated_python(main_path, content)

        # HARD POST-CONDITION
        written = main_path.read_text(encoding="utf-8")
        if re.search(
            r'^\s*document_models\s*=\s*\[\s*\]',
            written,
            re.MULTILINE,
        ):
            raise RuntimeError(
                f"WIRING FAILURE: document_models empty after wiring {model_name}"
            )

        log("WIRING", f"✅ Verified document_models is not empty")
        return True

    return False
