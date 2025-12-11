# app/core/config.py
"""
Application configuration - single source of truth for all settings.
"""
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class LLMSettings:
    """LLM provider configuration."""
    default_provider: str = field(default_factory=lambda: os.getenv("DEFAULT_LLM_PROVIDER", "gemini"))
    default_model: str = field(default_factory=lambda: os.getenv("DEFAULT_LLM_MODEL", "gemini-2.0-flash-exp"))
    gemini_api_key: Optional[str] = field(default_factory=lambda: os.getenv("GEMINI_API_KEY"))
    openai_api_key: Optional[str] = field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    anthropic_api_key: Optional[str] = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY"))
    ollama_base_url: str = field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    temperature: float = 0.7
    max_retries: int = 3


@dataclass
class WorkflowSettings:
    """Workflow execution configuration."""
    max_turns: int = 30
    max_files_per_step: int = 5
    max_file_lines: int = 400
    supervision_retries: int = 3
    quality_gate_threshold: int = 5
    default_max_tokens: int = 8000
    # FIX #15: Centralize magic number from engine.py
    max_chat_history: int = 10


@dataclass
class SandboxSettings:
    """Docker sandbox configuration."""
    health_check_timeout: int = 60
    command_timeout: int = 300
    test_timeout: int = 600


@dataclass 
class PathSettings:
    """Path configuration."""
    base_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent.parent)
    # FIX ENV-001: Accept both WORKSPACES_DIR (preferred) and WORKSPACES_PATH (legacy from .env.example)
    workspaces_dir: Path = field(default_factory=lambda: Path(
        os.getenv("WORKSPACES_DIR") or 
        os.getenv("WORKSPACES_PATH") or
        str(Path(__file__).parent.parent.parent.parent / "workspaces")
    ))
    # NOTE: Using 'Frontend' (capitalized) for cross-platform compatibility
    # Windows is case-insensitive, but Linux/Mac are case-sensitive
    frontend_dist: Path = field(default_factory=lambda: Path(os.getenv(
        "FRONTEND_DIST_PATH",
        str(Path(__file__).parent.parent.parent.parent.parent / "Frontend" / "dist")
    )))


@dataclass
class UoTSettings:
    """
    Universe of Thought (UoT) configuration.
    
    Controls the creative reasoning operators:
    - C-UoT: Combinational (blend multiple archetypes)
    - E-UoT: Exploratory (inject foreign patterns)
    - T-UoT: Transformational (mutate constraints)
    """
    # Feature Flags (Safety Layer)
    enable_cuot: bool = field(default_factory=lambda: os.getenv("ENABLE_CUOT", "true").lower() == "true")
    enable_euot: bool = field(default_factory=lambda: os.getenv("ENABLE_EUOT", "true").lower() == "true")
    enable_tuot: bool = field(default_factory=lambda: os.getenv("ENABLE_TUOT", "false").lower() == "true")  # Sandbox only by default
    
    # Rollout Percentages (0-100)
    cuot_rollout_pct: int = field(default_factory=lambda: int(os.getenv("CUOT_ROLLOUT_PCT", "100")))
    euot_rollout_pct: int = field(default_factory=lambda: int(os.getenv("EUOT_ROLLOUT_PCT", "100")))
    tuot_rollout_pct: int = field(default_factory=lambda: int(os.getenv("TUOT_ROLLOUT_PCT", "0")))
    
    # Retry Thresholds for Escalation
    euot_retry_threshold: int = 2   # Activate E-UoT after this many retries
    tuot_retry_threshold: int = 3   # Activate T-UoT after this many retries
    
    # T-UoT Safety
    tuot_require_sandbox: bool = True  # Always run T-UoT mutations in sandbox first
    tuot_require_approval: bool = True  # Require human approval for T-UoT writes
    
    # Entropy Thresholds
    entropy_high: float = 1.5   # Above this = multi-domain query
    entropy_low: float = 0.5    # Below this = confident single option


@dataclass
class Settings:
    """Main application settings."""
    llm: LLMSettings = field(default_factory=LLMSettings)
    workflow: WorkflowSettings = field(default_factory=WorkflowSettings)
    sandbox: SandboxSettings = field(default_factory=SandboxSettings)
    paths: PathSettings = field(default_factory=PathSettings)
    uot: UoTSettings = field(default_factory=UoTSettings)
    port: int = field(default_factory=lambda: int(os.getenv("PORT", 8000)))
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")
    
    def ensure_directories(self):
        """Ensure required directories exist."""
        self.paths.workspaces_dir.mkdir(parents=True, exist_ok=True)


# Singleton instance
settings = Settings()
