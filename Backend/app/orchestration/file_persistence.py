# app/orchestration/file_persistence.py
"""
FAST v2 File Persistence

Handles all writes to disk for FAST v2.
Ensures consistency using atomic writes (tmp file + rename).
Prevents partial file writes that could corrupt the project.
"""
import os
from typing import Optional

from app.core.logging import log


class FilePersistence:
    """
    Handles all writes to disk for FAST v2.
    Ensures consistency, avoids partial writes using atomic rename.
    """
    
    def __init__(self, base_path: str = ""):
        self.base_path = base_path

    def write(self, path: str, text: str) -> bool:
        """
        Atomically write text to a file.
        Uses a temporary file and rename to prevent partial writes.
        
        Returns:
            True if successful, False otherwise
        """
        full_path = os.path.join(self.base_path, path) if self.base_path else path
        dir_path = os.path.dirname(full_path)
        
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        
        tmp = full_path + ".tmp"

        try:
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(text)
            
            # Atomic rename
            os.replace(tmp, full_path)
            log("FILE", f"✅ Written: {path} ({len(text)} chars)")
            
            # ═══════════════════════════════════════════════════════════════
            # PHASE 3: Record artifact birth event at materialization boundary
            # ═══════════════════════════════════════════════════════════════
            try:
                from app.arbormind.observation.execution_ledger import (
                    record_artifact_event, 
                    get_current_run_id
                )
                run_id = get_current_run_id()
                if run_id:
                    record_artifact_event(
                        run_id=run_id,
                        step="file_persistence",  # Generic step marker
                        file_path=path,
                        event_type="CREATED",
                        size_bytes=len(text.encode("utf-8")),
                    )
            except Exception:
                pass  # Observation is best-effort
            
            return True
            
        except Exception as e:
            log("FILE", f"❌ Write failed: {path} - {e}")
            # Clean up temp file on error
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass  # Temp file cleanup is best-effort
            return False

    def read(self, path: str) -> Optional[str]:
        """Read a file and return its contents, or None if not found."""
        full_path = os.path.join(self.base_path, path) if self.base_path else path
        
        if not os.path.exists(full_path):
            return None
        
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            log("FILE", f"❌ Read failed: {path} - {e}")
            return None

    def exists(self, path: str) -> bool:
        """Check if a file exists."""
        full_path = os.path.join(self.base_path, path) if self.base_path else path
        return os.path.exists(full_path)

    def delete(self, path: str) -> bool:
        """Delete a file if it exists."""
        full_path = os.path.join(self.base_path, path) if self.base_path else path
        
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
                log("FILE", f"🗑️ Deleted: {path}")
                return True
            except Exception as e:
                log("FILE", f"❌ Delete failed: {path} - {e}")
                return False
        return False

    def set_base_path(self, base_path: str):
        """Set the base path for all operations."""
        self.base_path = base_path

    def ensure_dir(self, path: str) -> bool:
        """Ensure a directory exists."""
        full_path = os.path.join(self.base_path, path) if self.base_path else path
        try:
            os.makedirs(full_path, exist_ok=True)
            return True
        except Exception as e:
            log("FILE", f"❌ mkdir failed: {path} - {e}")
            return False
