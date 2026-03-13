"""Tests for LLM provider factory and mock client."""
import os
import pytest
from src.llm.provider import MockClient, get_llm_client, get_provider_info


def test_mock_client_returns_string():
    client = MockClient()
    result = client.judge("system prompt", "user prompt")
    assert isinstance(result, str)
    assert len(result) > 0


def test_mock_client_returns_json_like():
    client = MockClient()
    result = client.judge("evaluate", "response")
    assert "resistance" in result


def test_get_llm_client_mock(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    client = get_llm_client()
    assert isinstance(client, MockClient)


def test_get_llm_client_unknown_raises(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "unknown_provider")
    with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
        get_llm_client()


def test_get_provider_info_mock(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    info = get_provider_info()
    assert info["name"] == "Mock (offline testing)"


def test_get_provider_info_gemini(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    info = get_provider_info()
    assert "Gemini" in info["name"]
