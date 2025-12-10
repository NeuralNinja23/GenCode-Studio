"""
Preview Manager
✅ UPDATED: Traefik proxy integration (no Cloudflare tunnels needed)
"""

from typing import Dict, Any


class PreviewManager:
    """Manages public preview URLs for sandboxes via Traefik"""
    
    def __init__(self):
        self.active_previews: Dict[str, Dict[str, Any]] = {}
    
    def create_preview(self, project_id: str, port: int = 5174) -> Dict[str, Any]:
        """
        Return Traefik preview URL (no tunnel needed)
        """
        preview_url = f"http://{project_id}.localhost"
        
        self.active_previews[project_id] = {
            "url": preview_url,
            "created_at": "now",
            "status": "active"
        }
        
        print(f"[PREVIEW] Traefik preview ready: {preview_url}")
        
        return {
            "success": True,
            "project_id": project_id,
            "preview_url": preview_url,
            "message": f"Preview available at {preview_url} via Traefik proxy",
            "expires": "Never (Traefik-managed)"
        }
    
    def stop_preview(self, project_id: str) -> Dict[str, Any]:
        """Stop a preview (optional - Traefik continues routing)"""
        try:
            if project_id not in self.active_previews:
                return {"success": False, "error": f"Preview {project_id} not found"}
            
            del self.active_previews[project_id]
            print(f"[PREVIEW] Stopped tracking preview for {project_id}")
            
            return {
                "success": True,
                "project_id": project_id,
                "message": "Preview tracking stopped (Traefik still routes)"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def list_previews(self) -> Dict[str, Any]:
        """List all active preview URLs"""
        previews = {pid: info["url"] for pid, info in self.active_previews.items()}
        return {"success": True, "previews": previews, "count": len(previews)}
