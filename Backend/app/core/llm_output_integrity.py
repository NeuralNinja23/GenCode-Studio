# app/core/llm_output_integrity.py

from typing import Dict, List
import ast
import json
import re


class LLMOutputIntegrityError(Exception):
    pass


def _is_truncated(content: str) -> bool:
    # common truncation signals
    if content.count("{") != content.count("}"):
        return True
    if content.count("[") != content.count("]"):
        return True
    if re.search(r"\.\.\.$", content.strip()):
        return True
    return False


def _validate_python(content: str, path: str):
    try:
        ast.parse(content)
    except SyntaxError as e:
        raise LLMOutputIntegrityError(
            f"Invalid Python syntax in {path}: {e}"
        )


def _validate_js_like(content: str, path: str):
    # very light JS sanity checks (not a parser)
    if content.strip().startswith("{") and content.strip().endswith("}"):
        return
    if content.count("(") != content.count(")"):
        raise LLMOutputIntegrityError(
            f"Unbalanced parentheses in {path}"
        )


def validate_llm_files(
    files: Dict[str, str],
    step: str | None = None,
) -> Dict[str, str]:
    """
    Hygiene-only validation.
    Ensures files are readable, complete, and syntactically sane.

    RETURNS: same files dict if valid
    RAISES: LLMOutputIntegrityError if invalid
    """

    if not files:
        raise LLMOutputIntegrityError(
            f"No files produced by LLM{f' during {step}' if step else ''}"
        )

    for path, content in files.items():
        if not content or not content.strip():
            raise LLMOutputIntegrityError(
                f"Empty file generated: {path}"
            )

        if _is_truncated(content):
            raise LLMOutputIntegrityError(
                f"Truncated or incomplete output detected in {path}"
            )

        if path.endswith(".py"):
            _validate_python(content, path)

        elif path.endswith((".js", ".ts", ".jsx", ".tsx")):
            _validate_js_like(content, path)

        elif path.endswith(".json"):
            try:
                json.loads(content)
            except json.JSONDecodeError as e:
                raise LLMOutputIntegrityError(
                    f"Invalid JSON in {path}: {e}"
                )

    return files
