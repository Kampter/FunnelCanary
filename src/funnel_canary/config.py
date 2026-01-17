"""Configuration module for FunnelCanary."""

import os
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class Config:
    """Configuration for the FunnelCanary agent."""

    api_key: str
    base_url: str
    model_name: str

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        load_dotenv()

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model_name = os.getenv("MODEL_NAME", "gpt-4")

        return cls(
            api_key=api_key,
            base_url=base_url,
            model_name=model_name,
        )
