from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def _env(name: str, *fallbacks: str, default: str = "") -> str:
    for key in (name, *fallbacks):
        value = os.getenv(key)
        if value:
            return value
    return default


def _basic_auth_value() -> str:
    value = _env("TURING_BASIC_AUTH", "TURING_AUTHORIZATION")
    if not value:
        return "Basic YWRtaW46VHVyaW5nQDEyMw=="
    if value.startswith("Basic "):
        return value
    return f"Basic {value}"


@dataclass(frozen=True)
class Settings:
    root_dir: Path
    policy_path: Path
    test_cases_path: Path
    db_path: Path
    upload_dir: Path
    eval_dir: Path
    frontend_dist: Path
    turing_api_base: str
    turing_api_key: str
    turing_api_gateway_key: str
    turing_basic_auth: str
    turing_provider: str
    turing_upload_module: str
    turing_multimodal_model: str
    turing_text_model: str
    app_env: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    root_dir = Path(__file__).resolve().parents[2]
    generated_dir = root_dir / "app" / "generated"
    upload_dir = generated_dir / "uploads"
    eval_dir = generated_dir / "evals"

    return Settings(
        root_dir=root_dir,
        policy_path=root_dir / "policy_terms.json",
        test_cases_path=root_dir / "test_cases.json",
        db_path=root_dir / "claims.db",
        upload_dir=upload_dir,
        eval_dir=eval_dir,
        frontend_dist=root_dir / "frontend" / "dist",
        turing_api_base=_env("TURING_API_BASE", default="https://kong.turing.com/api"),
        turing_api_key=_env("TURING_API_KEY"),
        turing_api_gateway_key=_env(
            "TURING_API_GATEWAY_KEY",
            "TURING_API_GW_KEY",
            default="0c015800-dcba-448d-94bb-d01a56b0d22c",
        ),
        turing_basic_auth=_basic_auth_value(),
        turing_provider=_env("TURING_PROVIDER", default="google"),
        turing_upload_module=_env("TURING_UPLOAD_MODULE", default="PLAYGROUND"),
        turing_multimodal_model=_env("TURING_MULTIMODAL_MODEL"),
        turing_text_model=_env("TURING_TEXT_MODEL"),
        app_env=os.getenv("APP_ENV", "development"),
    )
