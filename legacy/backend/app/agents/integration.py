# app/agents/integration.py
# GenCode Studio - Integration Manager
# ✅ ALL 13 IMPORT ERRORS FIXED!
# Last Updated: November 8, 2025

import os
import json
from typing import Dict, List, Optional, Any, TypedDict, Literal

# ================================================================
# ✅ FIX: Define all missing constants locally (errors #1-13 fixed)
# ================================================================

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

# Temperature setting
DEFAULT_TEMPERATURE = 0.7

# Available models
AVAILABLE_MODELS = {
    "gemini": ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"],
    "openai": ["gpt-5", "gpt-4o-mini"],
    "anthropic": ["claude-3.5-sonnet", "claude-3.5-opus"],
    "ollama": ["qwen2.5-coder:7b", "mistral", "codellama"],
}


# ================================================================
# TYPE DEFINITIONS
# ================================================================

class ChatMessage(TypedDict):
    """Chat message format"""
    role: Literal["system", "user", "assistant"]
    content: str

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

# ---- Compatibility exports for workflows.py ----

def initialize_marcus() -> dict:
    """Return a minimal agent team descriptor used by workflows."""
    return {
        "Marcus": {"role": "Orchestrator", "provider": "gemini", "model": "gemini-2.0-flash"},
        "Derek": {"role": "Backend QA"},
        "Luna": {"role": "Frontend QA"},
        "Victoria": {"role": "Architect"},
    }

AGENT_TEAM = initialize_marcus()

DEVELOPMENT_PHASES = [
    "analysis",
    "frontend_mock",
    "backend",
    "testing_backend",
    "testing_frontend_approval",
    "testing_frontend",
    "deployment",
]

# Tool registry placeholder (wire to your real tools if available)
GENCODE_TOOLS = {
    "unit_tests": "derek_backend_tester",
    "e2e_tests": "luna_frontend_tester",
    "architecture": "victoria_architect",
}

# ================================================================
# INTEGRATION MANAGER
# ================================================================

class IntegrationManager:
    """
    Manages feature flags and configuration for GenCode Studio.

    Controls:
    - Persistent memory (project context storage)
    - Marcus reflex loop (JSON compliance retry)
    - Telemetry tracking (usage analytics)
    - Context compression (large prompt handling)
    - Tool result linking (output references)
    - Deployment validation (pre-deploy checks)
    - Key validation (API key verification)
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
        """
        Check if a specific feature is enabled.

        Args:
            feature: Feature name (e.g., "persistent_memory", "reflex_loop")

        Returns:
            True if feature is enabled, False otherwise
        """
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
        """Get database path for persistent memory"""
        return MEMORY_DB_PATH_TEMPLATE.replace("{project_id}", self.project_id)

    def get_max_workflow_turns(self) -> int:
        """Get maximum workflow turns before forcing completion"""
        return self.config.get("max_workflow_turns", MAX_WORKFLOW_TURNS)

    def get_max_test_retries(self) -> int:
        """Get maximum test retry attempts"""
        return self.config.get("max_test_retries", MAX_TEST_RETRIES)

    def should_compress_context(self, token_count: int) -> bool:
        """
        Determine if context should be compressed.

        Args:
            token_count: Estimated token count of context

        Returns:
            True if compression should be applied
        """
        if not self.is_feature_enabled("context_compression"):
            return False
        return token_count > CONTEXT_COMPRESSION_THRESHOLD

    def validate_api_keys(self) -> Dict[str, bool]:
        """
        Validate that required API keys are configured.

        Returns:
            Dict mapping provider to validation status
        """
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

    def get_available_models(self, provider: Optional[str] = None) -> Dict[str, List[str]] | List[str]:
        """
        Get available models.

        Args:
            provider: Optional provider filter

        Returns:
            Dict of all models or list for specific provider
        """
        if provider:
            return AVAILABLE_MODELS.get(provider, [])
        return AVAILABLE_MODELS

    def get_config_summary(self) -> Dict[str, Any]:
        """
        Get summary of current configuration.

        Returns:
            Dict with configuration details
        """
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
            "available_models": self.get_available_models(),
        }

# ================================================================
# HELPER FUNCTIONS
# ================================================================

def create_integration_manager(project_id: Optional[str] = None) -> IntegrationManager:
    """
    Factory function to create integration manager.

    Args:
        project_id: Optional project identifier

    Returns:
        Configured IntegrationManager instance
    """
    return IntegrationManager(project_id)

def get_feature_flags() -> Dict[str, bool]:
    """
    Get all feature flags as a dictionary.

    Returns:
        Dict mapping feature names to enabled status
    """
    return {
        "persistent_memory": ENABLE_PERSISTENT_MEMORY,
        "marcus_reflex_loop": ENABLE_MARCUS_REFLEX_LOOP,
        "telemetry_tracking": ENABLE_TELEMETRY_TRACKING,
        "context_compression": ENABLE_CONTEXT_COMPRESSION,
        "tool_result_linking": ENABLE_TOOL_RESULT_LINKING,
        "deployment_validation": ENABLE_DEPLOYMENT_VALIDATION,
        "key_validation": ENABLE_KEY_VALIDATION,
    }

def is_feature_enabled(feature: str) -> bool:
    """
    Quick check if a feature is enabled.

    Args:
        feature: Feature name

    Returns:
        True if enabled
    """
    feature_map = {
        "persistent_memory": ENABLE_PERSISTENT_MEMORY,
        "marcus_reflex_loop": ENABLE_MARCUS_REFLEX_LOOP,
        "reflex_loop": ENABLE_MARCUS_REFLEX_LOOP,
        "telemetry": ENABLE_TELEMETRY_TRACKING,
        "context_compression": ENABLE_CONTEXT_COMPRESSION,
        "tool_linking": ENABLE_TOOL_RESULT_LINKING,
        "deployment_validation": ENABLE_DEPLOYMENT_VALIDATION,
        "key_validation": ENABLE_KEY_VALIDATION,
    }
    return feature_map.get(feature, False)

def get_workflow_limits() -> Dict[str, int]:
    """
    Get workflow execution limits.

    Returns:
        Dict with max turns and retries
    """
    return {
        "max_workflow_turns": MAX_WORKFLOW_TURNS,
        "max_test_retries": MAX_TEST_RETRIES,
        "compression_threshold": CONTEXT_COMPRESSION_THRESHOLD,
    }

def validate_environment() -> Dict[str, Any]:
    """
    Validate that the environment is properly configured.

    Returns:
        Dict with validation results
    """
    manager = IntegrationManager()
    config = manager.get_config_summary()

    # Check for critical issues
    issues = []
    warnings = []

    # Validate API keys
    api_validation = config["api_keys"]
    if not any(api_validation.values()):
        issues.append("No API keys configured. At least one LLM provider is required.")

    # Check memory configuration
    if ENABLE_PERSISTENT_MEMORY:
        memory_path = manager.get_memory_db_path()
        memory_dir = os.path.dirname(memory_path)
        if memory_dir and not os.path.exists(memory_dir):
            try:
                os.makedirs(memory_dir, exist_ok=True)
            except Exception as e:
                warnings.append(f"Could not create memory directory: {e}")

    # Check workflow limits
    if MAX_WORKFLOW_TURNS < 10:
        warnings.append(f"MAX_WORKFLOW_TURNS is very low ({MAX_WORKFLOW_TURNS}). Recommend at least 20.")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "config": config,
    }

# ================================================================
# MODULE EXPORTS
# ================================================================

__all__ = [
    "IntegrationManager",
    "create_integration_manager",
    "get_feature_flags",
    "is_feature_enabled",
    "get_workflow_limits",
    "validate_environment",
    # Constants
    "ENABLE_PERSISTENT_MEMORY",
    "ENABLE_MARCUS_REFLEX_LOOP",
    "ENABLE_TELEMETRY_TRACKING",
    "ENABLE_CONTEXT_COMPRESSION",
    "ENABLE_TOOL_RESULT_LINKING",
    "ENABLE_DEPLOYMENT_VALIDATION",
    "ENABLE_KEY_VALIDATION",
    "MAX_WORKFLOW_TURNS",
    "MAX_TEST_RETRIES",
    "CONTEXT_COMPRESSION_THRESHOLD",
    "MEMORY_DB_PATH_TEMPLATE",
    "AVAILABLE_MODELS",
]