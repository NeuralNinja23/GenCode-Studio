# app/orchestration/checkpoint.py
"""
FAST v2 Checkpoint Manager

Stores SAFE checkpoints of each FAST step.
Persists project state to disk for rollback and debugging.
"""
import os
import json
import shutil
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any


class CheckpointManagerV2:
    """
    Stores SAFE checkpoints of each FAST step.
    Does NOT store broken artifacts.
    """
    
    def __init__(self, base_dir: str = ".fast_checkpoints"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    async def save_project_snapshot(self, project_path: Path, step: str, **metadata) -> str:
        """
        Capture the entire project state from disk.
        Async wrapper for blocking IO.
        """
        return await asyncio.to_thread(self._save_project_snapshot_sync, project_path, step, **metadata)

    def _save_project_snapshot_sync(self, project_path: Path, step: str, **metadata) -> str:
        """Sync implementation of project capture."""
        files = {}
        ignore_dirs = {".git", ".fast_checkpoints", "node_modules", "__pycache__", "venv", ".venv"}
        
        for root, dirs, filenames in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            for filename in filenames:
                if filename.endswith(('.py', '.js', '.jsx', '.ts', '.tsx', '.json', '.md', '.css', '.html', '.env')):
                    filepath = Path(root) / filename
                    try:
                        rel_path = str(filepath.relative_to(project_path))
                        files[rel_path] = filepath.read_text(encoding='utf-8')
                    except Exception:
                        pass
        
        return self.save(step, files, **metadata)

    def save(self, step: str, files: Dict[str, str], **metadata):
        """
        Save a checkpoint for a step using provided file content.
        """
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        directory = os.path.join(self.base_dir, f"{step}_{ts}")
        os.makedirs(directory, exist_ok=True)

        for rel_path, content in files.items():
            safe_rel = rel_path.replace("\\", "/").lstrip("/")
            full_path = os.path.join(directory, safe_rel)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

        # Save metadata
        meta = {
            "step": step,
            "timestamp": ts,
            "files": list(files.keys())
        }
        meta.update(metadata) # Merge extra metadata
        with open(os.path.join(directory, "meta.json"), "w") as f:
            json.dump(meta, f, indent=2)
            
        return directory

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
            # Fallback: traverse dir
            pass
        else:
            with open(meta_path, "r") as f:
                meta = json.load(f)

        # Load files recursively
        files = {}
        for root, _, filenames in os.walk(latest_dir):
            for filename in filenames:
                if filename == "meta.json": continue
                full_path = Path(root) / filename
                rel_path = str(full_path.relative_to(latest_dir))
                files[rel_path] = full_path.read_text(encoding="utf-8")

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
                    try:
                        with open(meta_path, "r") as f:
                            meta = json.load(f)
                        checkpoints.append(meta)
                    except:
                        pass

        return sorted(checkpoints, key=lambda x: x.get("timestamp", ""), reverse=True)
