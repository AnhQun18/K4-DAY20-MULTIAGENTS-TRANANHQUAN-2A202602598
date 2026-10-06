"""Process-wide request pacing and bounded retries, without changing provided model.py."""
import asyncio
import logging
import math
import os
import threading
import time

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import RunnableBinding
from pydantic import ConfigDict

logger = logging.getLogger(__name__)


class RequestGate:
    def __init__(self, rpm):
        self.interval = 60 / rpm if rpm else 0
        self.next_call = 0.0
        self.lock = threading.Lock()

    def delay(self):
        with self.lock:
            now = time.monotonic()
            slot = max(now, self.next_call)
            self.next_call = slot + self.interval
            return slot - now


_gates = {}
_gates_lock = threading.Lock()


def retry_status(error):
    """Recognize provider status codes; never retry unrelated exceptions."""
    for obj in (error, getattr(error, "response", None)):
        for attr in ("status_code", "code"):
            value = getattr(obj, attr, None)
            if callable(value):
                value = value()
            for code, name in ((429, "RESOURCE_EXHAUSTED"), (503, "UNAVAILABLE")):
                if str(getattr(value, "value", value)) == str(code) or getattr(value, "name", None) == name:
                    return code
    return None


class ControlledModel(BaseChatModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    inner: BaseChatModel
    gate: RequestGate
    retry_seconds: float
    retries: int
    unavailable_seconds: float = 30
    unavailable_retries: int = 3

    def _retry_delay(self, error, counts):
        status = retry_status(error)
        if status is None:
            return None
        wait, limit = ((self.retry_seconds, self.retries) if status == 429 else
                       (self.unavailable_seconds, self.unavailable_retries))
        if counts[status] >= limit:
            return None
        counts[status] += 1
        logger.warning("Model returned %d; waiting %.1fs before retry %d/%d",
                       status, wait, counts[status], limit)
        return wait

    @property
    def _llm_type(self):
        return self.inner._llm_type

    @property
    def _identifying_params(self):
        return self.inner._identifying_params

    def bind_tools(self, tools, **kwargs):
        bound = self.inner.bind_tools(tools, **kwargs)
        if bound is self.inner:
            return self
        if not isinstance(bound, RunnableBinding):
            raise TypeError("Rate control requires bind_tools to return a RunnableBinding")
        return self.bind(**bound.kwargs)

    def get_num_tokens_from_messages(self, messages, tools=None):
        return self.inner.get_num_tokens_from_messages(messages, tools=tools)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        counts = {429: 0, 503: 0}
        while True:
            time.sleep(self.gate.delay())
            try:
                return self.inner._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
            except Exception as error:
                wait = self._retry_delay(error, counts)
                if wait is None:
                    raise
                time.sleep(wait)

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        counts = {429: 0, 503: 0}
        while True:
            await asyncio.sleep(self.gate.delay())
            try:
                return await self.inner._agenerate(messages, stop=stop, run_manager=run_manager, **kwargs)
            except Exception as error:
                wait = self._retry_delay(error, counts)
                if wait is None:
                    raise
                await asyncio.sleep(wait)


def control_model(model):
    if isinstance(model, ControlledModel):
        return model
    rpm = float(os.getenv("LAB_REQUESTS_PER_MINUTE", "0"))
    wait = float(os.getenv("LAB_429_WAIT_SECONDS", "30"))
    retries = int(os.getenv("LAB_429_MAX_RETRIES", "3"))
    unavailable_wait = float(os.getenv("LAB_503_WAIT_SECONDS", "30"))
    unavailable_retries = int(os.getenv("LAB_503_MAX_RETRIES", "3"))
    if not math.isfinite(rpm) or rpm < 0 or not math.isfinite(wait) or wait <= 0 or retries < 0:
        raise ValueError("RPM must be finite and >= 0, 429 wait > 0, retries >= 0")
    if not math.isfinite(unavailable_wait) or unavailable_wait <= 0 or unavailable_retries < 0:
        raise ValueError("503 wait must be finite and > 0, retries >= 0")
    # model_copy does not reconstruct SDK clients created at model initialization.
    # Copy OpenAI-compatible clients as well, otherwise their hidden retries
    # multiply this wrapper's budget (including DeepSeek and Azure transports).
    if "max_retries" in type(model).model_fields:
        from openai import AsyncOpenAI, OpenAI

        updates = {"max_retries": 0}
        for root_name, resource_name, client_type in (
            ("root_client", "client", OpenAI),
            ("root_async_client", "async_client", AsyncOpenAI),
        ):
            resource = getattr(model, resource_name, None)
            root = getattr(model, root_name, None) or getattr(resource, "_client", None)
            if isinstance(root, client_type):
                copied = root.with_options(max_retries=0)
                updates[root_name] = copied
                updates[resource_name] = copied.chat.completions
        model = model.model_copy(update=updates)
    with _gates_lock:
        gate = _gates.setdefault(rpm, RequestGate(rpm))
    return ControlledModel(inner=model, gate=gate, retry_seconds=wait, retries=retries,
                           unavailable_seconds=unavailable_wait, unavailable_retries=unavailable_retries,
                           profile=model.profile)
