import json
from pathlib import Path


class PatchEngine:

    @staticmethod
    def apply_patches(workspace_path: str, patch_json: str):
        """
        Applies LLM patches (JSON-based) across multiple files.
        Returns a list of results per file.
        """
        try:
            data = json.loads(patch_json)

        except Exception as e:
            return [{
                "file": None,
                "success": False,
                "error": f"Invalid JSON patch: {str(e)}"
            }]

        patches = data.get("patches", [])
        results = []

        for patch in patches:
            file_rel = patch.get("file")
            before = patch.get("before")
            after = patch.get("after")

            if not file_rel:
                results.append({
                    "file": None,
                    "success": False,
                    "error": "Missing 'file' field in patch."
                })
                continue

            file_path = Path(workspace_path) / file_rel

            if not file_path.exists():
                results.append({
                    "file": file_rel,
                    "success": False,
                    "error": "File does not exist."
                })
                continue

            try:
                text = file_path.read_text()

                if before not in text:
                    results.append({
                        "file": file_rel,
                        "success": False,
                        "error": "Before-block not found in file (safety check)."
                    })
                    continue

                new_text = text.replace(before, after, 1)
                file_path.write_text(new_text, encoding="utf-8")

                results.append({
                    "file": file_rel,
                    "success": True,
                    "error": None
                })

            except Exception as e:
                results.append({
                    "file": file_rel,
                    "success": False,
                    "error": f"Patch failed: {str(e)}"
                })

        return results
