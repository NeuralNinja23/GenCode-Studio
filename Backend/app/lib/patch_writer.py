# app/agents/patch_writer.py
# Fully improved version with REAL unified diff support.
# Supports multi-hunk patches, file adds, deletes, and modifications.

from pathlib import Path
from typing import Tuple, Dict, Any


def apply_patch(root: Path, patch: str) -> Dict[str, Any]:
    """
    Apply a unified diff patch to the workspace.
    Accepts real git-style unified diffs.
    Example:
        --- a/api.py
        +++ b/api.py
        @@ -1,4 +1,4 @@
    """

    changes = []
    failures = []

    # Split patch into file-level segments
    file_patches = _split_into_file_patches(patch)

    for fp in file_patches:
        try:
            status, path = _apply_single_file_patch(root, fp)
            changes.append({"status": status, "file": path})
        except Exception as e:
            failures.append({"file_patch": fp[:80], "error": str(e)})

    return {"changes": changes, "failures": failures}


def _split_into_file_patches(patch: str) -> list:
    """Split a full multi-file unified diff into file-level diffs."""
    lines = patch.splitlines()
    patches = []
    current = []

    for line in lines:
        if line.startswith("--- "):
            if current:
                patches.append("\n".join(current))
                current = []
        current.append(line)

    if current:
        patches.append("\n".join(current))

    return patches


def _apply_single_file_patch(root: Path, patch_text: str) -> Tuple[str, str]:
    """Apply unified diff to a single file (one file at a time)."""

    lines = patch_text.splitlines()
    old_path = None
    new_path = None
    body: list[str] = []  # <-- FIX: predefine body so it's never unbound

    # Parse header
    for i, line in enumerate(lines):
        if line.startswith("--- "):
            old_path = line[4:].strip().split("\t")[0]

        if line.startswith("+++ "):
            new_path = line[4:].strip().split("\t")[0]
            body = lines[i + 1 :]  # safe because body is pre-defined
            break

    # Validate header structure
    if old_path is None or new_path is None:
        raise ValueError(
            "Invalid unified diff: missing ---/+++ headers.\n"
            f"Patch snippet:\n{patch_text[:200]}"
        )

    # Normalize paths
    new_clean = new_path.replace("a/", "").replace("b/", "")
    target_file = root / new_clean

    # Handle deleted file
    if old_path != "/dev/null" and target_file.exists():
        original = target_file.read_text(encoding="utf-8").splitlines()
    else:
        original = []

    result = _apply_hunks(original, body)

    # /dev/null → deletion
    if new_path == "/dev/null":
        if target_file.exists():
            target_file.unlink()
        return ("deleted", str(target_file))

    # Write updated or new file
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text("\n".join(result) + "\n", encoding="utf-8")

    if not original:
        return ("created", str(target_file))

    return ("modified", str(target_file))



def _apply_hunks(original: list, hunk_lines: list) -> list:
    """Apply each @@ hunk to file content."""
    result = original[:]
    index = 0

    while index < len(hunk_lines):
        line = hunk_lines[index]

        if not line.startswith("@@"):
            index += 1
            continue

        # Parse hunk header
        header = line
        _, old_info, new_info, _ = header.split(" ")

        old_start = int(old_info.split(",")[0][1:])

        index += 1
        new_block = []
        original_pos = old_start - 1

        while index < len(hunk_lines) and not hunk_lines[index].startswith("@@"):
            hl = hunk_lines[index]

            if hl.startswith("+"):
                new_block.append(hl[1:])
            elif hl.startswith("-"):
                # Skip line in original
                original_pos += 1
            else:
                new_block.append(hl[1:] if hl.startswith(" ") else hl)
                original_pos += 1

            index += 1

        # Apply this hunk
        start = old_start - 1
        end = start + (original_pos - (old_start - 1))
        result[start:end] = new_block

    return result
