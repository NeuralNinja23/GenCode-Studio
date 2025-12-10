"""
Sandbox Configuration
Manages settings for Docker sandbox environments
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List


@dataclass
class SandboxConfig:
    """Configuration for a Docker sandbox environment"""
    
    # Port mappings
    frontend_port: int = 5174
    backend_port: int = 8001
    
    # Resource limits
    memory_limit: str = "512m"
    cpu_limit: float = 1.0
    
    # Timeout settings (seconds)
    startup_timeout: int = 60
    health_check_timeout: int = 30
    test_timeout: int = 300
    
    # Feature flags
    enable_hot_reload: bool = True
    enable_debug_mode: bool = True
    auto_remove_on_stop: bool = False
    
    # Environment variables
    backend_env: Dict[str, str] = field(default_factory=dict)
    frontend_env: Dict[str, str] = field(default_factory=dict)
    
    # Network settings
    network_driver: str = "bridge"
    dns_servers: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            "frontend_port": self.frontend_port,
            "backend_port": self.backend_port,
            "memory_limit": self.memory_limit,
            "cpu_limit": self.cpu_limit,
            "startup_timeout": self.startup_timeout,
            "health_check_timeout": self.health_check_timeout,
            "test_timeout": self.test_timeout,
            "enable_hot_reload": self.enable_hot_reload,
            "enable_debug_mode": self.enable_debug_mode,
            "auto_remove_on_stop": self.auto_remove_on_stop,
            "backend_env": self.backend_env,
            "frontend_env": self.frontend_env,
            "network_driver": self.network_driver,
            "dns_servers": self.dns_servers
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SandboxConfig":
        """Create config from dictionary"""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})
