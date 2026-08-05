"""The authoring model, and the cache that keeps a re-run from re-paying for it.

Every authoring stage is one JSON-returning call. They differ only in prompt, so they share
one entry point and one cache.

The cache is keyed by task id, stage, model and a hash of the exact prompt. Task id alone
would be wrong in the direction that matters: editing a stage's prompt and getting the old
answer back is silent, whereas re-paying for a call whose prompt did not change is merely
slow. Every call is written out in full — prompt included — so a run can be audited later
without re-running it.
"""

import hashlib
import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from openai import OpenAI


class AuthoringError(RuntimeError):
    """The authoring model did not produce usable output for a stage."""


@dataclass
class Author:
    """One authoring model, pointed at a cache directory."""

    model: str = "openai/gpt-5-mini"
    cache_dir: Path = Path("tmp/my_env2_cache")
    temperature: float | None = None
    """Left unset by default. The gpt-5 family rejects anything but its own default, and the
    variety this pipeline needs comes from the sequences, not from sampling noise."""
    attempts: int = 2
    """Tries per call, for a transient upstream error or an unparseable reply."""
    corrections: int = 1
    """Extra rounds offered when a reply parses but fails its stage's contract."""
    base_url: str | None = None
    api_key: str | None = None

    def __post_init__(self) -> None:
        self.cache_dir = Path(self.cache_dir)
        self._client: OpenAI | None = None
        self.calls = 0
        self.cache_hits = 0

    def client(self) -> OpenAI:
        if self._client is None:
            base_url = self.base_url or os.environ.get("OPENROUTER_BASE_URL")
            api_key = self.api_key or os.environ.get("OPENROUTER_API_KEY")
            if not base_url or not api_key:
                raise AuthoringError(
                    "set OPENROUTER_BASE_URL and OPENROUTER_API_KEY (or pass base_url/api_key)"
                )
            self._client = OpenAI(base_url=base_url, api_key=api_key)
        return self._client

    def ask(
        self,
        task_id: str,
        stage: str,
        system: str,
        user: str,
        validate: Callable[[dict], None] | None = None,
    ) -> dict:
        """One JSON object from the model, cached and checked.

        `validate` raises with a message when the reply does not satisfy the stage's contract.
        The message is handed back to the model once, and the corrected answer is checked
        again; a second failure drops the task. This is deliberately the whole retry policy:
        the model fixes its own output, and nothing here patches a reply into shape, because a
        patched world is one the prompt no longer describes.
        """
        request = user
        problems = []
        for _ in range(1 + self.corrections):
            reply = self._call(task_id, stage, system, request)
            if validate is None:
                return reply
            try:
                validate(reply)
            except Exception as error:  # noqa: BLE001 - any stage's own rejection reason
                problems.append(str(error))
                request = (
                    f"{user}\n\nYOUR PREVIOUS ANSWER WAS REJECTED: {error}\n"
                    "Return the whole object again, corrected. Change only what the rejection "
                    "names; keep everything else as it was."
                )
                continue
            return reply
        raise AuthoringError(f"{task_id} {stage}: " + " | then ".join(problems))

    def _call(self, task_id: str, stage: str, system: str, user: str) -> dict:
        digest = hashlib.sha256(
            "\x00".join([self.model, system, user]).encode()
        ).hexdigest()[:16]
        path = self.cache_dir / task_id / f"{stage}-{digest}.json"
        if path.exists():
            self.cache_hits += 1
            return json.loads(path.read_text())["response"]

        failures = []
        for attempt in range(self.attempts):
            try:
                request = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "response_format": {"type": "json_object"},
                }
                if self.temperature is not None:
                    request["temperature"] = self.temperature
                self.calls += 1
                completion = self.client().chat.completions.create(**request)
                parsed = _parse(completion.choices[0].message.content or "")
            except Exception as error:  # noqa: BLE001 - one bad call must not lose a batch
                failures.append(f"{type(error).__name__}: {error}")
                time.sleep(1.0 + attempt)
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(
                    {
                        "model": self.model,
                        "stage": stage,
                        "system": system,
                        "user": user,
                        "response": parsed,
                    },
                    indent=1,
                    ensure_ascii=False,
                )
            )
            return parsed
        raise AuthoringError(f"{task_id} {stage}: " + " | ".join(failures))


def _parse(text: str) -> dict:
    """The outermost JSON object in the reply.

    Tolerant on purpose: models wrap JSON in prose or a code fence often enough that
    rejecting the whole response over it is not worth the retry. `strict=False` allows raw
    newlines inside strings, which a long authored prompt reliably contains.
    """
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise AuthoringError(f"no JSON object in reply: {text[:200]!r}")
    parsed = json.loads(text[start : end + 1], strict=False)
    if not isinstance(parsed, dict):
        raise AuthoringError("reply was not a JSON object")
    return parsed
