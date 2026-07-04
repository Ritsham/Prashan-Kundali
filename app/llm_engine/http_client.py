from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


def post_json(url: str, payload: dict, headers: dict) -> dict:
    timeout = float(os.getenv("PRASHNA_LLM_TIMEOUT_SECONDS", "20"))
    request_headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "KundaliStudio/1.0 (+https://localhost)",
        **headers,
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=request_headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        if exc.code == 403 and "error code: 1010" in body.lower():
            raise RuntimeError(
                "HTTP 403 from Groq edge: Cloudflare error 1010 blocked this request before it reached the model. "
                "The key may be valid, but Groq is rejecting this machine/network/request fingerprint."
            ) from exc
        raise RuntimeError(f"HTTP {exc.code}: {body[:500]}") from exc


def call_rotating_chat_completion(
    *,
    provider: str,
    api_keys: list[str],
    model: str,
    url: str,
    payload: dict,
    headers: dict,
) -> dict:
    data = None
    errors = []
    for index, api_key in enumerate(api_keys, start=1):
        try:
            data = post_json(
                url,
                payload,
                {
                    "Authorization": f"Bearer {api_key}",
                    **headers,
                },
            )
            break
        except Exception as exc:
            errors.append(f"key {index}: {exc}")
    if data is None:
        raise RuntimeError("; ".join(errors) or f"{provider} failed for model {model}")
    return data

def post_json_stream(url: str, payload: dict, headers: dict):
    timeout = float(os.getenv("PRASHNA_LLM_TIMEOUT_SECONDS", "30"))
    request_headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "KundaliStudio/1.0 (+https://localhost)",
        **headers,
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=request_headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            for line in response:
                decoded = line.decode("utf-8")
                if decoded.startswith("data: "):
                    yield decoded[6:].strip()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body[:500]}") from exc

def call_rotating_chat_completion_stream(
    *,
    provider: str,
    api_keys: list[str],
    model: str,
    url: str,
    payload: dict,
    headers: dict,
):
    errors = []
    for index, api_key in enumerate(api_keys, start=1):
        try:
            yield from post_json_stream(
                url,
                payload,
                {
                    "Authorization": f"Bearer {api_key}",
                    **headers,
                },
            )
            return
        except Exception as exc:
            errors.append(f"key {index}: {exc}")
    raise RuntimeError("; ".join(errors) or f"{provider} failed for model {model}")
