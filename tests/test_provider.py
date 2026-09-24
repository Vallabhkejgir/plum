from __future__ import annotations

from pathlib import Path

import pytest

from app.core.settings import Settings
from app.services.provider import TuringGatewayClient


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self._payload


class _FakeAsyncClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def post(self, url, headers=None, files=None, json=None):
        self.calls.append(
            {
                "url": url,
                "headers": headers,
                "files": files,
                "json": json,
            }
        )
        return self._responses.pop(0)


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        root_dir=tmp_path,
        policy_path=tmp_path / "policy_terms.json",
        test_cases_path=tmp_path / "test_cases.json",
        db_path=tmp_path / "claims.db",
        upload_dir=tmp_path / "uploads",
        eval_dir=tmp_path / "evals",
        frontend_dist=tmp_path / "dist",
        turing_api_base="https://kong.turing.com/api",
        turing_api_key="api-key",
        turing_api_gateway_key="gw-key",
        turing_basic_auth="Basic test",
        turing_provider="openai",
        turing_upload_module="PLAYGROUND",
        turing_multimodal_model="gemini-flash-latest",
        turing_text_model="gemini-flash-latest",
        app_env="test",
    )


@pytest.mark.asyncio
async def test_extract_document_uses_upload_then_chat_for_images(tmp_path, monkeypatch):
    image_path = tmp_path / "sample.jpg"
    image_path.write_bytes(b"fake-image")

    fake_client = _FakeAsyncClient(
        [
            _FakeResponse({"file_id": "PLAYGROUND_image.jpg"}),
            _FakeResponse(
                {
                    "choices": [
                        {
                            "message": {
                                "content": '{"patient_name":"Rajesh Kumar","diagnosis":"Viral Fever"}'
                            }
                        }
                    ]
                }
            ),
        ]
    )

    import app.services.provider as provider_module

    monkeypatch.setattr(provider_module.httpx, "AsyncClient", lambda timeout: fake_client)

    client = TuringGatewayClient(_settings(tmp_path))
    result = await client.extract_document(image_path, "What is in this image?")

    assert result.content["patient_name"] == "Rajesh Kumar"
    assert fake_client.calls[0]["url"] == "https://kong.turing.com/api/files/upload"
    assert fake_client.calls[1]["url"] == "https://kong.turing.com/api/v2/chat"
    assert fake_client.calls[1]["json"]["messages"][0]["content"][1] == {
        "type": "image_file_id",
        "image_file_id": "PLAYGROUND_image.jpg",
    }


@pytest.mark.asyncio
async def test_extract_document_uses_document_file_id_for_pdfs(tmp_path, monkeypatch):
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    fake_client = _FakeAsyncClient(
        [
            _FakeResponse({"data": {"file_id": "PLAYGROUND_document.pdf"}}),
            _FakeResponse(
                {
                    "choices": [
                        {
                            "message": {
                                "content": '{"summary":"Document summary"}'
                            }
                        }
                    ]
                }
            ),
        ]
    )

    import app.services.provider as provider_module

    monkeypatch.setattr(provider_module.httpx, "AsyncClient", lambda timeout: fake_client)

    client = TuringGatewayClient(_settings(tmp_path))
    await client.extract_document(pdf_path, "Summarize this document")

    assert fake_client.calls[1]["json"]["messages"][0]["content"][1] == {
        "type": "document_file_id",
        "document_file_id": "PLAYGROUND_document.pdf",
    }

