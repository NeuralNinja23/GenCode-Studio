# app/workflow/engine_v2/checkpoint.py
"""
FAST v2 Checkpoint Manager

Stores SAFE checkpoints of each FAST step.
Does NOT store broken artifacts.
"""
import os
import json
from datetime import datetime
from typing import Dict, Optional


class CheckpointManagerV2:
    """
    Stores SAFE checkpoints of each FAST step.
    Does NOT store broken artifacts.
    """
    
    def __init__(self, base_dir: str = ".fast_checkpoints"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def save(self, step: str, files: Dict[str, str]):
        """
        Save a checkpoint for a step.
        
        Args:
            step: The step name
            files: Dict of {path: content}
        """
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        directory = os.path.join(self.base_dir, f"{step}_{ts}")
        os.makedirs(directory, exist_ok=True)

        for path, content in files.items():
            # Save with basename to avoid path issues
            filename = os.path.basename(path)
            full_path = os.path.join(directory, filename)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

        # Save metadata
        meta = {
            "step": step,
            "timestamp": ts,
            "files": list(files.keys())
        }
        with open(os.path.join(directory, "meta.json"), "w") as f:
            json.dump(meta, f, indent=2)

    def get_latest(self, step: str) -> Optional[Dict[str, str]]:
        """Get the latest checkpoint for a step."""
        if not os.path.exists(self.base_dir):
            return None

        # Find all checkpoints for this step
        checkpoints = []
        for name in os.listdir(self.base_dir):
            if name.startswith(f"{step}_"):
                checkpoints.append(name)

        if not checkpoints:
            return None

        # Sort by timestamp (newest first)
        checkpoints.sort(reverse=True)
        latest_dir = os.path.join(self.base_dir, checkpoints[0])

        # Load metadata
        meta_path = os.path.join(latest_dir, "meta.json")
        if not os.path.exists(meta_path):
            return None

        with open(meta_path, "r") as f:
            meta = json.load(f)

        # Load files
        files = {}
        for original_path in meta.get("files", []):
            filename = os.path.basename(original_path)
            file_path = os.path.join(latest_dir, filename)
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    files[original_path] = f.read()

        return files

    def list_checkpoints(self, step: str = None) -> list:
        """List all checkpoints, optionally filtered by step."""
        if not os.path.exists(self.base_dir):
            return []

        checkpoints = []
        for name in os.listdir(self.base_dir):
            if step is None or name.startswith(f"{step}_"):
                meta_path = os.path.join(self.base_dir, name, "meta.json")
                if os.path.exists(meta_path):
                    with open(meta_path, "r") as f:
                        meta = json.load(f)
                        checkpoints.append(meta)

        return sorted(checkpoints, key=lambda x: x.get("timestamp", ""), reverse=True)
