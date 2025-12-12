# app/core/integration.py
"""
Integration Manager logic ported from legacy agents/integration.py.
Handles feature flags, configuration, and environment validation.
"""
import os
from typing import Dict, Optional, Any, TypedDict

# Feature flags - Define locally instead of importing
ENABLE_PERSISTENT_MEMORY = os.getenv("ENABLE_PERSISTENT_MEMORY", "false").lower() == "true"
ENABLE_MARCUS_REFLEX_LOOP = os.getenv("ENABLE_MARCUS_REFLEX_LOOP", "true").lower() == "true"
ENABLE_TELEMETRY_TRACKING = os.getenv("ENABLE_TELEMETRY_TRACKING", "false").lower() == "true"
ENABLE_CONTEXT_COMPRESSION = os.getenv("ENABLE_CONTEXT_COMPRESSION", "false").lower() == "true"
ENABLE_TOOL_RESULT_LINKING = os.getenv("ENABLE_TOOL_RESULT_LINKING", "true").lower() == "true"
ENABLE_DEPLOYMENT_VALIDATION = os.getenv("ENABLE_DEPLOYMENT_VALIDATION", "true").lower() == "true"
ENABLE_KEY_VALIDATION = os.getenv("ENABLE_KEY_VALIDATION", "true").lower() == "true"

# Workflow limits
MAX_WORKFLOW_TURNS = int(os.getenv("MAX_WORKFLOW_TURNS", "50"))
MAX_TEST_RETRIES = int(os.getenv("MAX_TEST_RETRIES", "3"))

# Compression settings
CONTEXT_COMPRESSION_THRESHOLD = int(os.getenv("CONTEXT_COMPRESSION_THRESHOLD", "100000"))

# Database path
MEMORY_DB_PATH_TEMPLATE = os.getenv("MEMORY_DB_PATH_TEMPLATE", "data/memory_{project_id}.db")

# Sample Models (Reference) - Updated for 2024-2025
AVAILABLE_MODELS = {
    "gemini": ["gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash"],
    "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
    "anthropic": ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-haiku-20240307"],
    "ollama": ["qwen2.5-coder:7b", "mistral", "codellama", "llama3.1"],
}


class IntegrationConfig(TypedDict, total=False):
    """Configuration for integration features"""
    enable_persistent_memory: bool
    enable_marcus_reflex_loop: bool
    enable_telemetry: bool
    enable_context_compression: bool
    enable_tool_linking: bool
    enable_deployment_validation: bool
    max_workflow_turns: int
    max_test_retries: int


class IntegrationManager:
    """
    Manages feature flags and configuration for GenCode Studio.
    Ported from legacy.
    """

    def __init__(self, project_id: Optional[str] = None):
        """Initialize integration manager for a project"""
        self.project_id = project_id or "default"
        self.config = self._load_config()

    def _load_config(self) -> IntegrationConfig:
        """Load configuration from environment and defaults"""
        return {
            "enable_persistent_memory": ENABLE_PERSISTENT_MEMORY,
            "enable_marcus_reflex_loop": ENABLE_MARCUS_REFLEX_LOOP,
            "enable_telemetry": ENABLE_TELEMETRY_TRACKING,
            "enable_context_compression": ENABLE_CONTEXT_COMPRESSION,
            "enable_tool_linking": ENABLE_TOOL_RESULT_LINKING,
            "enable_deployment_validation": ENABLE_DEPLOYMENT_VALIDATION,
            "max_workflow_turns": MAX_WORKFLOW_TURNS,
            "max_test_retries": MAX_TEST_RETRIES,
        }

    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a specific feature is enabled."""
        feature_map = {
            "persistent_memory": "enable_persistent_memory",
            "reflex_loop": "enable_marcus_reflex_loop",
            "marcus_reflex_loop": "enable_marcus_reflex_loop",
            "telemetry": "enable_telemetry",
            "context_compression": "enable_context_compression",
            "tool_linking": "enable_tool_linking",
            "deployment_validation": "enable_deployment_validation",
        }
        config_key = feature_map.get(feature, f"enable_{feature}")
        return self.config.get(config_key, False)

    def get_memory_db_path(self) -> str:
        return MEMORY_DB_PATH_TEMPLATE.replace("{project_id}", self.project_id)

    def get_max_workflow_turns(self) -> int:
        return self.config.get("max_workflow_turns", MAX_WORKFLOW_TURNS)

    def get_max_test_retries(self) -> int:
        return self.config.get("max_test_retries", MAX_TEST_RETRIES)

    def validate_api_keys(self) -> Dict[str, bool]:
        """Validate that required API keys are configured."""
        if not ENABLE_KEY_VALIDATION:
            return {"validation_disabled": True}

        validation = {}
        # Check Gemini keys
        gemini_keys = [
            os.getenv("GEMINI_API_KEY_PRIMARY"),
            os.getenv("GEMINI_API_KEY"),
        ]
        validation["gemini"] = any(gemini_keys)
        # Check OpenAI
        validation["openai"] = bool(os.getenv("OPENAI_API_KEY"))
        # Check Anthropic
        validation["anthropic"] = bool(os.getenv("ANTHROPIC_API_KEY"))
        # Check Ollama
        validation["ollama"] = bool(os.getenv("OLLAMA_BASE_URL"))

        return validation

    def get_config_summary(self) -> Dict[str, Any]:
        """Get summary of current configuration."""
        return {
            "project_id": self.project_id,
            "features": {
                "persistent_memory": self.is_feature_enabled("persistent_memory"),
                "marcus_reflex_loop": self.is_feature_enabled("reflex_loop"),
                "telemetry": self.is_feature_enabled("telemetry"),
                "context_compression": self.is_feature_enabled("context_compression"),
                "tool_linking": self.is_feature_enabled("tool_linking"),
                "deployment_validation": self.is_feature_enabled("deployment_validation"),
            },
            "limits": {
                "max_workflow_turns": self.get_max_workflow_turns(),
                "max_test_retries": self.get_max_test_retries(),
                "compression_threshold": CONTEXT_COMPRESSION_THRESHOLD,
            },
            "api_keys": self.validate_api_keys(),
            "available_models": AVAILABLE_MODELS,
        }


def create_integration_manager(project_id: Optional[str] = None) -> IntegrationManager:
    return IntegrationManager(project_id)


def validate_environment() -> Dict[str, Any]:
    """Validate that the environment is properly configured."""
    manager = IntegrationManager()
    config = manager.get_config_summary()
    issues = []
    warnings = []

    api_validation = config["api_keys"]
    # If key validation is enabled and failed for all
    if ENABLE_KEY_VALIDATION and not api_validation.get("validation_disabled") and not any(k for k, v in api_validation.items() if v):
       issues.append("No API keys configured. At least one LLM provider is required.")

    if ENABLE_PERSISTENT_MEMORY:
        memory_path = manager.get_memory_db_path()
        memory_dir = os.path.dirname(memory_path)
        if memory_dir and not os.path.exists(memory_dir):
            try:
                os.makedirs(memory_dir, exist_ok=True)
            except Exception as e:
                warnings.append(f"Could not create memory directory: {e}")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "config": config,
    }
