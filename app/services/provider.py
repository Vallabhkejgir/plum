from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from app.core.settings import Settings


@dataclass
class ProviderResult:
    content: dict[str, Any]
    raw_text: str | None = None


class TuringGatewayClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def configured(self) -> bool:
        return bool(
            self.settings.turing_api_key
            and self.settings.turing_api_base
            and self.settings.turing_api_gateway_key
            and self.settings.turing_basic_auth
            and self.settings.turing_multimodal_model
            and self.settings.turing_text_model
        )

    @property
    def _api_root(self) -> str:
        base = self.settings.turing_api_base.rstrip("/")
        for suffix in ("/chat/completions", "/v2/chat", "/files/upload", "/v1"):
            if base.endswith(suffix):
                base = base[: -len(suffix)]
        return base

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.settings.turing_api_key,
            "x-api-gw-key": self.settings.turing_api_gateway_key,
            "Authorization": self.settings.turing_basic_auth,
        }

    async def _upload_file(self, client: httpx.AsyncClient, file_path: Path) -> str:
        with file_path.open("rb") as handle:
            files = {
                "file": (file_path.name, handle),
                "module": (None, self.settings.turing_upload_module),
            }
            response = await client.post(
                f"{self._api_root}/files/upload",
                headers=self._headers,
                files=files,
            )
        response.raise_for_status()
        payload = response.json()

        candidates = (
            payload.get("file_id"),
            payload.get("id"),
            payload.get("data", {}).get("file_id") if isinstance(payload.get("data"), dict) else None,
            payload.get("data", {}).get("id") if isinstance(payload.get("data"), dict) else None,
            payload.get("result", {}).get("file_id") if isinstance(payload.get("result"), dict) else None,
            payload.get("result", {}).get("id") if isinstance(payload.get("result"), dict) else None,
        )
        file_id = next((item for item in candidates if isinstance(item, str) and item.strip()), None)
        if not file_id:
            raise RuntimeError(f"Turing upload succeeded but no file id was returned: {payload}")
        return file_id

    def _file_content_part(self, file_path: Path, file_id: str) -> dict[str, str]:
        if file_path.suffix.lower() in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff"}:
            return {
                "type": "image_file_id",
                "image_file_id": file_id,
            }
        return {
            "type": "document_file_id",
            "document_file_id": file_id,
        }

    @staticmethod
    def _extract_message_text(payload: dict[str, Any]) -> str:
        choices = payload.get("choices")
        if isinstance(choices, list) and choices:
            message = choices[0].get("message", {})
            content = message.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                text_parts: list[str] = []
                for item in content:
                    if isinstance(item, dict) and isinstance(item.get("text"), str):
                        text_parts.append(item["text"])
                if text_parts:
                    return "\n".join(text_parts)

        for key in ("message", "content", "response", "text"):
            value = payload.get(key)
            if isinstance(value, str):
                return value

        data = payload.get("data")
        if isinstance(data, dict):
            for key in ("message", "content", "response", "text"):
                value = data.get(key)
                if isinstance(value, str):
                    return value

        raise RuntimeError(f"Unsupported Turing chat response shape: {payload}")

    async def extract_document(
        self,
        file_path: Path,
        prompt: str,
    ) -> ProviderResult:
        if not self.configured:
            raise RuntimeError("Turing gateway is not configured.")

        async with httpx.AsyncClient(timeout=60.0) as client:
            file_id = await self._upload_file(client, file_path)
            body = {
                "model": self.settings.turing_multimodal_model,
                "provider": self.settings.turing_provider,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            self._file_content_part(file_path, file_id),
                        ],
                    }
                ],
            }
            response = await client.post(
                f"{self._api_root}/v2/chat",
                headers={**self._headers, "Content-Type": "application/json"},
                json=body,
            )
            response.raise_for_status()
        payload = response.json()
        message = self._extract_message_text(payload)
        content = json.loads(message)
        return ProviderResult(content=content, raw_text=message)

    async def explain(self, prompt: str) -> str:
        if not self.configured:
            raise RuntimeError("Turing gateway is not configured.")
        body = {
            "model": self.settings.turing_text_model,
            "provider": self.settings.turing_provider,
            "messages": [
                {
                    "role": "system",
                    "content": "You summarize insurance adjudication logic into concise operational explanations.",
                },
                {"role": "user", "content": prompt},
            ],
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self._api_root}/v2/chat",
                headers={**self._headers, "Content-Type": "application/json"},
                json=body,
            )
            response.raise_for_status()
        payload = response.json()
        return self._extract_message_text(payload)
