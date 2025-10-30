import json
import os
import logging
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class AIConfig:
    """Manager for AI provider configuration"""

    SUPPORTED_PROVIDERS = {
        "gemini": {
            "name": "Google Gemini",
            "models": ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
            "requires_api_key": True
        },
        "openai": {
            "name": "OpenAI GPT",
            "models": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
            "requires_api_key": True
        },
        "claude": {
            "name": "Anthropic Claude",
            "models": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"],
            "requires_api_key": True
        },
        "custom": {
            "name": "Custom API",
            "models": ["custom-model"],
            "requires_api_key": True
        }
    }

    def __init__(self, config_file="ai_config.json"):
        self.config_file = Path(config_file)
        self.config = {}
        self.load_config()

    def load_config(self):
        """Load AI configuration from JSON file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                logger.info(f"Loaded AI config from {self.config_file}")
            except Exception as e:
                logger.error(f"Error loading AI config: {str(e)}")
                self.config = {}
                self._create_default_config()
        else:
            self._create_default_config()

    def save_config(self):
        """Save AI configuration to JSON file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved AI config to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving AI config: {str(e)}")
            return False

    def _create_default_config(self):
        """Create default AI configuration"""
        from config import GEMINI_API_KEY

        self.config = {
            "active_provider": "gemini",
            "providers": {
                "gemini": {
                    "api_key": GEMINI_API_KEY or "",
                    "model": "gemini-2.0-flash",
                    "temperature": 0.7,
                    "max_tokens": 1000,
                    "enabled": True
                },
                "openai": {
                    "api_key": "",
                    "model": "gpt-3.5-turbo",
                    "temperature": 0.7,
                    "max_tokens": 1000,
                    "enabled": False
                },
                "claude": {
                    "api_key": "",
                    "model": "claude-3-haiku",
                    "temperature": 0.7,
                    "max_tokens": 1000,
                    "enabled": False
                },
                "custom": {
                    "api_key": "",
                    "api_url": "",
                    "model": "custom-model",
                    "temperature": 0.7,
                    "max_tokens": 1000,
                    "enabled": False
                }
            },
            "prompts": {
                "blog_post": "default_blog",
                "tiktok_caption": "default_tiktok"
            },
            "updated_at": datetime.now().isoformat()
        }
        self.save_config()

    def get_active_provider(self) -> str:
        """Get the currently active AI provider"""
        return self.config.get("active_provider", "gemini")

    def set_active_provider(self, provider: str) -> bool:
        """Set the active AI provider"""
        if provider not in self.SUPPORTED_PROVIDERS:
            logger.error(f"Unsupported provider: {provider}")
            return False

        self.config["active_provider"] = provider
        self.config["updated_at"] = datetime.now().isoformat()
        return self.save_config()

    def get_provider_config(self, provider: Optional[str] = None) -> Dict:
        """Get configuration for a specific provider or active provider"""
        if provider is None:
            provider = self.get_active_provider()

        return self.config.get("providers", {}).get(provider, {})

    def update_provider_config(self, provider: str, **kwargs) -> bool:
        """Update configuration for a specific provider"""
        if provider not in self.SUPPORTED_PROVIDERS:
            logger.error(f"Unsupported provider: {provider}")
            return False

        if "providers" not in self.config:
            self.config["providers"] = {}

        if provider not in self.config["providers"]:
            self.config["providers"][provider] = {}

        # Update provided fields
        for key, value in kwargs.items():
            self.config["providers"][provider][key] = value

        self.config["updated_at"] = datetime.now().isoformat()
        return self.save_config()

    def get_selected_prompt(self, prompt_type: str) -> str:
        """Get the selected prompt ID for a given type"""
        return self.config.get("prompts", {}).get(prompt_type, f"default_{prompt_type}")

    def set_selected_prompt(self, prompt_type: str, prompt_id: str) -> bool:
        """Set the selected prompt for a given type"""
        if "prompts" not in self.config:
            self.config["prompts"] = {}

        self.config["prompts"][prompt_type] = prompt_id
        self.config["updated_at"] = datetime.now().isoformat()
        return self.save_config()

    def get_all_providers(self) -> Dict:
        """Get information about all supported providers"""
        return self.SUPPORTED_PROVIDERS

    def is_provider_enabled(self, provider: str) -> bool:
        """Check if a provider is enabled"""
        provider_config = self.get_provider_config(provider)
        return provider_config.get("enabled", False)

    def enable_provider(self, provider: str, enabled: bool = True) -> bool:
        """Enable or disable a provider"""
        return self.update_provider_config(provider, enabled=enabled)

    def validate_provider_config(self, provider: Optional[str] = None) -> tuple:
        """
        Validate provider configuration
        Returns: (is_valid, error_message)
        """
        if provider is None:
            provider = self.get_active_provider()

        provider_config = self.get_provider_config(provider)

        if not provider_config:
            return False, f"No configuration found for provider '{provider}'"

        if not provider_config.get("enabled", False):
            return False, f"Provider '{provider}' is not enabled"

        provider_info = self.SUPPORTED_PROVIDERS.get(provider, {})
        if provider_info.get("requires_api_key"):
            api_key = provider_config.get("api_key", "")
            if not api_key or api_key.strip() == "":
                return False, f"API key not configured for provider '{provider}'"

        if provider == "custom":
            api_url = provider_config.get("api_url", "")
            if not api_url or api_url.strip() == "":
                return False, "API URL not configured for custom provider"

        return True, "Configuration is valid"
