"""Runtime configuration validation for external dependencies."""

from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigError(RuntimeError):
    """Raised when required runtime configuration is invalid or missing."""


def get_admin_api_key() -> str | None:
    """Return the admin API key used to protect indexing endpoints."""
    value = os.getenv("ADMIN_API_KEY")
    return value.strip() if value and value.strip() else None


@dataclass(frozen=True)
class PineconeSettings:
    """Validated Pinecone configuration loaded from environment variables."""

    api_key: str
    index_name: str
    namespace: str
    cloud: str
    region: str
    top_k_default: int

    @classmethod
    def from_env(cls) -> "PineconeSettings":
        required = {
            "PINECONE_API_KEY": os.getenv("PINECONE_API_KEY"),
            "PINECONE_INDEX_NAME": os.getenv("PINECONE_INDEX_NAME"),
            "PINECONE_NAMESPACE": os.getenv("PINECONE_NAMESPACE"),
            "PINECONE_CLOUD": os.getenv("PINECONE_CLOUD"),
            "PINECONE_REGION": os.getenv("PINECONE_REGION"),
            "PINECONE_TOP_K_DEFAULT": os.getenv("PINECONE_TOP_K_DEFAULT"),
        }
        missing = [name for name, value in required.items() if not value or not value.strip()]
        if missing:
            raise ConfigError("Missing required Pinecone env vars: " + ", ".join(missing))

        try:
            top_k_default = int(required["PINECONE_TOP_K_DEFAULT"] or "")
        except ValueError as exc:
            raise ConfigError("PINECONE_TOP_K_DEFAULT must be an integer.") from exc

        if top_k_default <= 0:
            raise ConfigError("PINECONE_TOP_K_DEFAULT must be greater than zero.")

        return cls(
            api_key=str(required["PINECONE_API_KEY"]).strip(),
            index_name=str(required["PINECONE_INDEX_NAME"]).strip(),
            namespace=str(required["PINECONE_NAMESPACE"]).strip(),
            cloud=str(required["PINECONE_CLOUD"]).strip(),
            region=str(required["PINECONE_REGION"]).strip(),
            top_k_default=top_k_default,
        )
