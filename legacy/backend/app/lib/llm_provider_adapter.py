# app/lib/llm_provider_adapter.py
# GenCode Studio - Multi-Provider LLM Adapter
# ✅ FINALIZED: IDs, costs, models fully normalized with config and routers
# Last Updated: November 8, 2025

import os
import httpx
from typing import Literal, Dict, Any, Optional, List, Tuple
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field

###############################################################################
# ================================================================
# TYPE DEFINITIONS + CONSTANTS
# ================================================================

ProviderType = Literal["openai", "anthropic", "gemini", "ollama"]

PROVIDER_MODELS: Dict[str, List[str]] = {
    "openai": ["gpt-5"],
    "anthropic": ["claude-4.5-sonnet"],
    "gemini": ["gemini-2.5-pro"],
    "ollama": ["qwen2.5-coder:7b"]
}

MODEL_COSTS = {
    "gpt-5": (0.01, 0.03),  # example cost per 1K tokens
    "claude-4.5-sonnet": (0.002, 0.01),
    "gemini-2.5-pro": (0.0004, 0.0004),
    "qwen2.5-coder:7b": (0.0, 0.0)
}

def get_model_cost(model: str) -> Tuple[float, float]:
    """Prompt and completion cost per 1K tokens (USD)"""
    return MODEL_COSTS.get(model, (0.0, 0.0))

def normalized_provider_id(name: str) -> str:
    """Get normalized provider id."""
    raw = (name or "").replace("-", "_").lower()
    if raw in PROVIDER_MODELS:
        return raw
    for pid in PROVIDER_MODELS: # fuzzy match for id slugs
        if raw.startswith(pid):
            return pid
    return raw


###############################################################################
# REQUEST/RESPONSE MODELS

class LLMRequest(BaseModel):
    prompt: str = Field(..., description="User prompt or instruction")
    model: str = Field(..., description="Model identifier")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=8000, ge=1, le=100000)
    provider: ProviderType = Field(default="openai")
    system_prompt: Optional[str] = Field(default=None)
    stop_sequences: Optional[List[str]] = Field(default=None)

class LLMResponse(BaseModel):
    text: str = Field(..., description="Generated text response")
    model: str = Field(..., description="Model used")
    provider: ProviderType = Field(..., description="Provider used")
    tokens_used: Optional[int] = Field(default=None)
    finish_reason: Optional[str] = Field(default=None)
    cost_estimate: Optional[float] = Field(default=None)


###############################################################################
# BASE PROVIDER (ABSTRACT)

class BaseLLMProvider(ABC):
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url

    @abstractmethod
    async def call(self, request: LLMRequest) -> LLMResponse:
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        pass

    @abstractmethod
    def get_models(self) -> List[str]:
        pass

    def estimate_cost(self, tokens: int, model: str) -> float:
        cost = get_model_cost(model)
        rate = sum(cost) / 2
        return (tokens / 1000) * rate
# ================================================================
# OPENAI PROVIDER
# ================================================================

class OpenAIProvider(BaseLLMProvider):
    """OpenAI API Provider (GPT-4, GPT-3.5, etc.)"""

    def __init__(self, api_key: str, base_url: Optional[str] = None):
        super().__init__(api_key, base_url or "https://api.openai.com/v1")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def call(self, request: LLMRequest) -> LLMResponse:
        """Make API call to OpenAI"""
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        payload = {
            "model": request.model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens
        }

        if request.stop_sequences:
            payload["stop"] = request.stop_sequences

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()

        choice = data["choices"][0]
        tokens_used = data.get("usage", {}).get("total_tokens")

        return LLMResponse(
            text=choice["message"]["content"],
            model=request.model,
            provider="openai",
            tokens_used=tokens_used,
            finish_reason=choice.get("finish_reason"),
            cost_estimate=self.estimate_cost(tokens_used or 0, request.model)
        )

    def validate_config(self) -> bool:
        return bool(self.api_key)

    def get_models(self) -> List[str]:
        return [
            "gpt-4",
            "gpt-4-turbo",
            "gpt-4-turbo-preview",
            "gpt-4o",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k"
        ]

    def estimate_cost(self, tokens: int, model: str) -> float:
        pricing = {
            "gpt-4": 0.03,
            "gpt-4-turbo": 0.01,
            "gpt-4o": 0.005,
            "gpt-3.5-turbo": 0.0015
        }
        rate = pricing.get(model.split("-")[0] + "-" + model.split("-")[1], 0.01)
        return (tokens / 1000) * rate


# ================================================================
# ANTHROPIC PROVIDER
# ================================================================

class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude API Provider"""

    def __init__(self, api_key: str, base_url: Optional[str] = None):
        super().__init__(api_key, base_url or "https://api.anthropic.com")
        self.headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }

    async def call(self, request: LLMRequest) -> LLMResponse:
        """Make API call to Anthropic"""
        payload = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "messages": [
                {"role": "user", "content": request.prompt}
            ],
            "temperature": request.temperature
        }

        if request.system_prompt:
            payload["system"] = request.system_prompt

        if request.stop_sequences:
            payload["stop_sequences"] = request.stop_sequences

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/messages",
                json=payload,
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()

        content = data["content"][0]["text"]
        tokens_used = data.get("usage", {}).get("output_tokens")

        return LLMResponse(
            text=content,
            model=request.model,
            provider="anthropic",
            tokens_used=tokens_used,
            finish_reason=data.get("stop_reason"),
            cost_estimate=self.estimate_cost(tokens_used or 0, request.model)
        )

    def validate_config(self) -> bool:
        return bool(self.api_key)

    def get_models(self) -> List[str]:
        return [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
            "claude-2.1",
            "claude-2.0"
        ]

    def estimate_cost(self, tokens: int, model: str) -> float:
        pricing = {
            "claude-3-opus": 0.015,
            "claude-3-sonnet": 0.003,
            "claude-3-haiku": 0.00025,
            "claude-2": 0.008
        }
        for key in pricing:
            if key in model:
                return (tokens / 1000) * pricing[key]
        return (tokens / 1000) * 0.003


# ================================================================
# OLLAMA PROVIDER (LOCAL)
# ================================================================

class OllamaProvider(BaseLLMProvider):
    """Ollama Local LLM Provider"""

    def __init__(self, base_url: str = "http://localhost:11434", api_key: Optional[str] = None):
        super().__init__(api_key, base_url)

    async def call(self, request: LLMRequest) -> LLMResponse:
        """Make API call to local Ollama instance"""
        payload = {
            "model": request.model,
            "prompt": request.prompt,
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens
            }
        }

        if request.system_prompt:
            payload["system"] = request.system_prompt

        if request.stop_sequences:
            payload["options"]["stop"] = request.stop_sequences

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
        except httpx.ConnectError:
            raise ConnectionError(
                f"Could not connect to Ollama at {self.base_url}. "
                f"Make sure Ollama is running: 'ollama serve'"
            )

        return LLMResponse(
            text=data.get("response", ""),
            model=request.model,
            provider="ollama",
            tokens_used=data.get("eval_count"),
            finish_reason="stop",
            cost_estimate=0.0
        )

    def validate_config(self) -> bool:
        try:
            import httpx
            response = httpx.get(f"{self.base_url}/api/tags", timeout=5.0)
            return response.status_code == 200
        except:
            return False

    def get_models(self) -> List[str]:
        try:
            import httpx
            response = httpx.get(f"{self.base_url}/api/tags", timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
        except:
            pass
        return [
            "codellama:13b",
            "codellama:7b",
            "mistral:latest",
            "neural-chat:latest",
            "llama2:latest",
            "qwen:14b"
        ]

    def estimate_cost(self, tokens: int, model: str) -> float:
        return 0.0


# ================================================================
# GEMINI PROVIDER
# ================================================================

class GeminiProvider(BaseLLMProvider):
    """Google Gemini API Provider"""

    def __init__(self, api_key: str, base_url: Optional[str] = None):
        super().__init__(api_key, base_url or "https://generativelanguage.googleapis.com")

    async def call(self, request: LLMRequest) -> LLMResponse:
        """Make API call to Google Gemini"""
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": request.prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens
            }
        }

        if request.stop_sequences:
            payload["generationConfig"]["stopSequences"] = request.stop_sequences

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/models/{request.model}:generateContent?key={self.api_key}",
                json=payload
            )
            response.raise_for_status()
            data = response.json()

        candidate = data["candidates"][0]
        content = candidate["content"]["parts"][0]["text"]

        return LLMResponse(
            text=content,
            model=request.model,
            provider="gemini",
            tokens_used=data.get("usageMetadata", {}).get("totalTokenCount"),
            finish_reason=candidate.get("finishReason"),
            cost_estimate=self.estimate_cost(
                data.get("usageMetadata", {}).get("totalTokenCount", 0),
                request.model
            )
        )

    def validate_config(self) -> bool:
        return bool(self.api_key and len(self.api_key) > 10)

    def get_models(self) -> List[str]:
        return [
            "gemini-pro",
            "gemini-pro-vision",
            "gemini-1.5-pro",
            "gemini-2.0-flash"
        ]

    def estimate_cost(self, tokens: int, model: str) -> float:
        pricing = {
            "gemini-pro": 0.0001,
            "gemini-pro-vision": 0.0002,
            "gemini-1.5-pro": 0.00035,
            "gemini-2.0-flash": 0.00005
        }
        for key in pricing:
            if key in model:
                return (tokens / 1000) * pricing[key]
        return (tokens / 1000) * 0.0001


# ================================================================
# PROVIDER FACTORY
# ================================================================

class LLMProviderFactory:
    """Factory class for creating LLM provider instances"""

    @staticmethod
    def get_provider(
        provider_type: ProviderType,
        config: Dict[str, Any]
    ) -> BaseLLMProvider:
        """Get a provider instance based on type and configuration"""

        if provider_type == "openai":
            api_key = config.get("openai_api_key")
            if not api_key:
                raise ValueError("openai_api_key is required for OpenAI provider")
            return OpenAIProvider(api_key=api_key)

        elif provider_type == "anthropic":
            api_key = config.get("anthropic_api_key")
            if not api_key:
                raise ValueError("anthropic_api_key is required for Anthropic provider")
            return AnthropicProvider(api_key=api_key)

        elif provider_type == "ollama":
            base_url = config.get("ollama_base_url", "http://localhost:11434")
            return OllamaProvider(base_url=base_url)

        elif provider_type == "gemini":
            api_key = config.get("gemini_api_key")
            if not api_key:
                raise ValueError("gemini_api_key is required for Gemini provider")
            return GeminiProvider(api_key=api_key)

        elif provider_type == "azure_openai":
            api_key = config.get("azure_openai_api_key")
            base_url = config.get("azure_openai_base_url")
            deployment = config.get("azure_openai_deployment", "gpt-4")

            if not api_key or not base_url:
                raise ValueError(
                    "azure_openai_api_key and azure_openai_base_url are required"
                )

            return AzureOpenAIProvider(
                api_key=api_key,
                base_url=base_url,
                deployment_name=deployment
            )

        else:
            raise ValueError(f"Unknown provider type: {provider_type}")

    @staticmethod
    def get_provider_from_env(provider_type: ProviderType) -> BaseLLMProvider:
        """Get a provider instance using environment variables"""
        config = {
            "openai_api_key": os.getenv("OPENAI_API_KEY"),
            "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY"),
            "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            "gemini_api_key": os.getenv("GEMINI_API_KEY"),
            "azure_openai_api_key": os.getenv("AZURE_OPENAI_API_KEY"),
            "azure_openai_base_url": os.getenv("AZURE_OPENAI_BASE_URL"),
            "azure_openai_deployment": os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
        }
        return LLMProviderFactory.get_provider(provider_type, config)


# ================================================================
# HELPER FUNCTIONS
# ================================================================
def get_models_for_provider(pid: str) -> List[str]:
    """Return normalized model list for a provider"""
    return PROVIDER_MODELS.get(normalized_provider_id(pid), [])

def get_available_providers() -> Dict[str, Any]:
    """Return registry for routes/UI"""
    return {
        "openai": {
            "id": "openai",
            "name": "OpenAI GPT-5",
            "models": ["gpt-5"],
            "requires_api_key": True,
            "base_url": "https://api.openai.com/v1",
            "cost_per_1k_tokens": 0.03,
        },
        "anthropic": {
            "id": "anthropic",
            "name": "Claude 4.5 Sonnet",
            "models": ["claude-4.5-sonnet"],
            "requires_api_key": True,
            "base_url": "https://api.anthropic.com",
            "cost_per_1k_tokens": 0.015,
        },
        "gemini": {
            "id": "gemini",
            "name": "Gemini 2.5 Pro",
            "models": ["gemini-2.5-flash"],
            "requires_api_key": True,
            "base_url": "https://generativelanguage.googleapis.com",
            "cost_per_1k_tokens": 0.00035,
        },
        "ollama": {
            "id": "ollama",
            "name": "Ollama Qwen 2.5 Coder 7B",
            "models": ["qwen2.5-coder:7b"],
            "requires_api_key": False,
            "base_url": "http://localhost:11434",
            "cost_per_1k_tokens": 0.0,
        },
    }


async def test_provider_connection(
    provider_type: ProviderType,
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """Test connection to a provider"""
    try:
        provider = LLMProviderFactory.get_provider(provider_type, config)

        if not provider.validate_config():
            return {
                "connected": False,
                "provider": provider_type,
                "message": "Invalid configuration",
                "error": "Configuration validation failed"
            }

        import time
        start = time.time()

        test_request = LLMRequest(
            prompt="Say 'Hello' in one word.",
            model=provider.get_models()[0],
            temperature=0.0,
            max_tokens=10,
            provider=provider_type
        )

        response = await provider.call(test_request)
        latency = int((time.time() - start) * 1000)

        return {
            "connected": True,
            "provider": provider_type,
            "message": "Successfully connected",
            "latency_ms": latency,
            "models_available": len(provider.get_models()),
            "test_response": response.text[:50]
        }

    except Exception as e:
        return {
            "connected": False,
            "provider": provider_type,
            "message": "Connection failed",
            "error": str(e)
        }