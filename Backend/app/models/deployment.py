from datetime import datetime, timezone
from typing import Optional, Dict, Literal
from beanie import Document, Indexed
from pydantic import Field

DeploymentStatus = Literal["initialized", "deploying", "success", "failed", "rolling_back", "not_deployed"]

class Deployment(Document):
    """Deployment configuration and status."""
    project_id: Indexed(str, unique=True)
    status: DeploymentStatus = "not_deployed"
    project_name: str
    custom_domain: Optional[str] = None
    environment_vars: Dict[str, str] = Field(default_factory=dict)
    
    # Versioning
    version: str = "1.0.0"
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deployed_at: Optional[datetime] = None
    last_updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Runtime info
    url: Optional[str] = None
    container_health: str = "unknown"
    port: int = 3000

    class Settings:
        name = "deployments"
