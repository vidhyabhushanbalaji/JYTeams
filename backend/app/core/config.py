"""Application settings loaded from environment variables and ``backend/.env``."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# backend/app/core/config.py -> parents[2] == backend/
BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIR / ".env"

DEFAULT_DEV_USER_ID = "00000000-0000-0000-0000-000000000001"


class Settings(BaseSettings):
    """Runtime configuration.

    Every value has a safe default, so the API boots without a ``.env`` file. Endpoints
    that need a service answer 503 until that service is configured.
    """

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = "dev"
    log_level: str = "INFO"
    api_prefix: str = "/api"
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://localhost:3000"]
    )

    # Supabase: auth, relational data (Postgres) and file storage.
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    storage_bucket: str = "project-files"

    # Auth. "dev" trusts the X-Dev-User-Id header (local work without a Supabase
    # project); "supabase" verifies the bearer token against Supabase Auth.
    auth_mode: Literal["dev", "supabase"] = "dev"
    dev_user_id: str = DEFAULT_DEV_USER_ID

    # Gemini. Reserved for the Graph AI Search section; used here only by the
    # "gemini" summariser.
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"
    # Positive values cap thinking (faster, cheaper summaries). 0, blank or negative omits
    # the thinking config entirely - which the *-flash-lite models require, because they
    # reject a budget of 0 with 400 INVALID_ARGUMENT.
    gemini_thinking_budget: int | None = 0

    # Summarisation. "auto" uses Gemini when a key is present, otherwise a local mock.
    summarizer: Literal["auto", "gemini", "mock"] = "auto"
    summary_max_input_chars: int = 12_000

    # Directory descriptions (Graph Creation, and the refresh after a placement). A folder's
    # prompt is built from the text of the files directly inside it, so two caps keep one large
    # folder from producing an enormous request.
    description_file_head_chars: int = 1_500
    description_max_input_chars: int = 24_000

    # Local (model-free) matching, shared by Graph AI Search and Graph Add suggestions. The
    # folder threshold is the share of the query a folder description must cover before the
    # walk opens that branch.
    scoring_folder_threshold: float = 0.25
    search_max_files_read: int = 200
    search_max_document_chars: int = 200_000
    blob_cache_entries: int = 256

    # Upload limits.
    max_upload_files: int = 2_000
    max_file_bytes: int = 20 * 1024 * 1024
    max_upload_bytes: int = 200 * 1024 * 1024
    max_directory_depth: int = 32

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: object) -> object:
        """Accept ``a,b`` (env-file friendly) as well as ``["a", "b"]``."""
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return []
            if raw.startswith("["):
                return json.loads(raw)
            return [origin.strip() for origin in raw.split(",") if origin.strip()]
        return value

    @property
    def supabase_configured(self) -> bool:
        """True when the service-role Supabase client can be created."""
        return bool(self.supabase_url and self.supabase_service_role_key)

    @property
    def resolved_summarizer(self) -> Literal["gemini", "mock"]:
        """Which summariser to use, resolving ``auto`` against the Gemini key."""
        if self.summarizer == "auto":
            return "gemini" if self.gemini_api_key else "mock"
        return self.summarizer


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings object (cached; safe to call per request)."""
    return Settings()
