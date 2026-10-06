"""Offline checks for rate control; keeps the supplied tests/ unchanged."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock

import pytest
from langchain_core.callbacks import UsageMetadataCallbackHandler
from langchain_core.messages import AIMessage

from lab import rate_control as rc
from lab.agent import build_agent
from lab.testing import ScriptedChatModel


class QuotaError(Exception):
    status_code = 429


class OverloadError(Exception):
    code = 503


class FlakyModel(ScriptedChatModel):
    failures: int = 1
    attempts: int = 0
    fatal: bool = False
    overloaded: bool = False

    def _generate(self, *args, **kwargs):
        self.attempts += 1
        if self.fatal:
            raise ValueError("invalid request")
        if self.attempts <= self.failures:
            if self.overloaded:
                raise OverloadError("high demand")
            raise QuotaError("quota")
        return super()._generate(*args, **kwargs)

    async def _agenerate(self, *args, **kwargs):
        return self._generate(*args, **kwargs)


@pytest.fixture(autouse=True)
def settings(monkeypatch):
    monkeypatch.setenv("LAB_REQUESTS_PER_MINUTE", "12")
    monkeypatch.setenv("LAB_429_WAIT_SECONDS", "30")
    monkeypatch.setenv("LAB_429_MAX_RETRIES", "3")
    monkeypatch.setenv("LAB_503_WAIT_SECONDS", "30")
    monkeypatch.setenv("LAB_503_MAX_RETRIES", "3")
    monkeypatch.setattr(rc, "_gates", {})


def test_shared_pacing_across_threads(monkeypatch):
    monkeypatch.setattr(rc.time, "monotonic", lambda: 100.0)
    a = rc.control_model(ScriptedChatModel())
    b = rc.control_model(ScriptedChatModel())
    assert a.gate is b.gate
    with ThreadPoolExecutor(max_workers=4) as pool:
        delays = list(pool.map(lambda _: a.gate.delay(), range(4)))
    assert sorted(delays) == [0, 5, 10, 15]


def test_429_wait_and_usage_counted_once(monkeypatch):
    sleeps = []
    monkeypatch.setattr(rc.time, "sleep", sleeps.append)
    monkeypatch.setattr(rc.time, "monotonic", lambda: 100.0)
    inner = FlakyModel(script=[AIMessage(content="OK")])
    usage = UsageMetadataCallbackHandler()
    assert rc.control_model(inner).invoke("hello", config={"callbacks": [usage]}).content == "OK"
    assert inner.attempts == 2
    assert sleeps == [0, 30, 5]
    assert sum(v["total_tokens"] for v in usage.usage_metadata.values()) == 120


def test_retries_are_bounded_and_other_errors_propagate(monkeypatch):
    monkeypatch.setattr(rc.time, "sleep", lambda _: None)
    inner = FlakyModel(failures=20)
    with pytest.raises(QuotaError):
        rc.control_model(inner).invoke("hello")
    assert inner.attempts == 4
    fatal = FlakyModel(fatal=True)
    with pytest.raises(ValueError, match="invalid request"):
        rc.control_model(fatal).invoke("hello")
    assert fatal.attempts == 1


def test_async_retry_uses_async_wait(monkeypatch):
    sleep = AsyncMock()
    monkeypatch.setattr(rc.asyncio, "sleep", sleep)
    inner = FlakyModel(script=[AIMessage(content="OK")])
    assert asyncio.run(rc.control_model(inner).ainvoke("hello")).content == "OK"
    assert inner.attempts == 2
    assert any(call.args == (30,) for call in sleep.await_args_list)


@pytest.mark.parametrize("async_call", [False, True])
def test_503_retries_and_exhaustion(monkeypatch, async_call):
    sleeps = []
    monkeypatch.setattr(rc.time, "sleep", sleeps.append)
    async_sleep = AsyncMock()
    monkeypatch.setattr(rc.asyncio, "sleep", async_sleep)
    def invoke(inner):
        model = rc.control_model(inner)
        return asyncio.run(model.ainvoke("hello")) if async_call else model.invoke("hello")
    inner = FlakyModel(overloaded=True, script=[AIMessage(content="OK")])
    assert invoke(inner).content == "OK"
    assert inner.attempts == 2
    assert (any(c.args == (30,) for c in async_sleep.await_args_list) if async_call else 30 in sleeps)
    exhausted = FlakyModel(overloaded=True, failures=20)
    with pytest.raises(OverloadError):
        invoke(exhausted)
    assert exhausted.attempts == 4


def test_subagent_calls_are_paced_and_counted_once(tmp_path, monkeypatch):
    sleeps = []
    monkeypatch.setattr(rc.time, "sleep", sleeps.append)
    inner = ScriptedChatModel(script=[
        AIMessage(content="", tool_calls=[{"name": "task", "args": {
            "description": "inspect", "subagent_type": "explorer"}, "id": "1"}]),
        AIMessage(content="report"), AIMessage(content="done"),
    ])
    usage = UsageMetadataCallbackHandler()
    build_agent(tmp_path, mode="subagents", model=inner).invoke(
        {"messages": [{"role": "user", "content": "inspect"}]},
        config={"callbacks": [usage]},
    )
    assert inner.calls == len(sleeps) == 3
    assert sum(v["total_tokens"] for v in usage.usage_metadata.values()) == 360


@pytest.mark.parametrize("key,value", [
    ("LAB_REQUESTS_PER_MINUTE", "-1"), ("LAB_REQUESTS_PER_MINUTE", "nan"),
    ("LAB_429_WAIT_SECONDS", "0"), ("LAB_429_MAX_RETRIES", "-1"),
    ("LAB_503_WAIT_SECONDS", "nan"), ("LAB_503_MAX_RETRIES", "-1"),
])
def test_invalid_configuration(key, value, monkeypatch):
    monkeypatch.setenv(key, value)
    with pytest.raises(ValueError):
        rc.control_model(ScriptedChatModel())


@pytest.mark.parametrize("async_call", [False, True])
def test_real_sdk_retries_do_not_multiply_wrapper_budget(monkeypatch, async_call):
    """Exercise the actual DeepSeek/OpenAI transport with no network or API key."""
    import httpx
    from langchain_deepseek import ChatDeepSeek
    from openai import RateLimitError

    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(429, json={"error": {"message": "offline quota", "type": "rate_limit"}})

    sync_client = httpx.Client(transport=httpx.MockTransport(respond))
    async_client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    inner = ChatDeepSeek(model="deepseek-chat", api_key="offline-test-placeholder",
                         http_client=sync_client, http_async_client=async_client)
    monkeypatch.setattr(rc.time, "sleep", lambda _: None)
    monkeypatch.setattr(rc.asyncio, "sleep", AsyncMock())
    controlled = rc.control_model(inner)
    assert inner.client._client.max_retries == 2  # The original model stays intact.
    assert controlled.inner.client._client.max_retries == 0
    assert controlled.inner.async_client._client.max_retries == 0
    try:
        with pytest.raises(RateLimitError):
            if async_call:
                asyncio.run(controlled.ainvoke("hello"))
            else:
                controlled.invoke("hello")
        assert len(requests) == 4  # One initial request plus exactly three retries.
    finally:
        sync_client.close()
        asyncio.run(async_client.aclose())
