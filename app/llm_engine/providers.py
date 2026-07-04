from __future__ import annotations

import os
import textwrap

from app.llm_engine.config import (
    DEFAULT_OPENAI_MODEL,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_GROQ_MODEL,
    DEFAULT_OPENROUTER_MODEL,
    DEFAULT_CEREBRAS_MODEL,
    api_keys_for,
    selected_provider_label,
)
from app.llm_engine.http_client import post_json, call_rotating_chat_completion


def call_openai(sys_prompt: str, usr_prompt: str, model: str = None) -> dict:
    api_keys = api_keys_for("OPENAI")
    if not api_keys:
        raise RuntimeError("OPENAI_API_KEY or OPENAI_API_KEYS is not set")
    model = model or os.getenv("OPENAI_INTERPRETATION_MODEL", DEFAULT_OPENAI_MODEL)
    payload = {
        "model": model,
        "input": [
            {"role": "system", "content": [{"type": "input_text", "text": sys_prompt}]},
            {"role": "user", "content": [{"type": "input_text", "text": usr_prompt}]},
        ],
    }
    data = None
    errors = []
    for index, api_key in enumerate(api_keys, start=1):
        try:
            data = post_json(
                "https://api.openai.com/v1/responses",
                payload,
                {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
            break
        except Exception as exc:
            errors.append(f"key {index}: {exc}")
    if data is None:
        raise RuntimeError("; ".join(errors))
    text = extract_openai_text(data)
    if not text:
        raise RuntimeError("OpenAI response did not contain output text")
    return answer_payload(text, "llm", "openai", model, "")


def call_gemini(sys_prompt: str, usr_prompt: str, model: str = None) -> dict:
    api_keys = api_keys_for("GEMINI") or api_keys_for("GOOGLE")
    if not api_keys:
        raise RuntimeError("GEMINI_API_KEY, GEMINI_API_KEYS, GOOGLE_API_KEY, or GOOGLE_API_KEYS is not set")
    model = model or os.getenv("GEMINI_INTERPRETATION_MODEL", DEFAULT_GEMINI_MODEL)
    payload = {
        "systemInstruction": {"parts": [{"text": sys_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": usr_prompt}]}],
    }
    data = None
    errors = []
    for index, api_key in enumerate(api_keys, start=1):
        try:
            data = post_json(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
                payload,
                {"Content-Type": "application/json"},
            )
            break
        except Exception as exc:
            errors.append(f"key {index}: {exc}")
    if data is None:
        raise RuntimeError("; ".join(errors))
    text = extract_gemini_text(data)
    if not text:
        raise RuntimeError("Gemini response did not contain output text")
    return answer_payload(text, "llm", "gemini", model, "")


def call_groq(sys_prompt: str, usr_prompt: str, model: str = None) -> dict:
    api_keys = api_keys_for("GROQ")
    if not api_keys:
        raise RuntimeError("GROQ_API_KEY or GROQ_API_KEYS is not set")
    model = model or os.getenv("GROQ_INTERPRETATION_MODEL", DEFAULT_GROQ_MODEL)
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": usr_prompt},
        ],
        "temperature": 0.7,
        "stream": stream,
    }
    data = None
    errors = []
    for index, api_key in enumerate(api_keys, start=1):
        try:
            data = post_json(
                "https://api.groq.com/openai/v1/chat/completions",
                payload,
                {"Content-Type": "application/json"},
            )
            break
        except Exception as exc:
            errors.append(f"key {index}: {exc}")
    if data is None:
        raise RuntimeError("; ".join(errors))
    text = extract_chat_completion_text(data)
    if not text:
        raise RuntimeError("Groq response did not contain output text")
    return answer_payload(text, "llm", "groq", model, "")


def call_openrouter(sys_prompt: str, usr_prompt: str, model: str = None, stream: bool = False):
    api_keys = api_keys_for("OPENROUTER")
    if not api_keys:
        raise RuntimeError("OPENROUTER_API_KEY or OPENROUTER_API_KEYS is not set")
    model = model or os.getenv("OPENROUTER_INTERPRETATION_MODEL", DEFAULT_OPENROUTER_MODEL)
    payload = chat_completion_payload(model, sys_prompt, usr_prompt, stream=stream)
    
    if stream:
        from app.llm_engine.http_client import call_rotating_chat_completion_stream
        import json
        
        def stream_generator():
            for chunk_str in call_rotating_chat_completion_stream(
                provider="openrouter",
                api_keys=api_keys,
                model=model,
                url="https://openrouter.ai/api/v1/chat/completions",
                payload=payload,
                headers={
                    "HTTP-Referer": "https://localhost",
                    "X-Title": "KundaliStudio",
                    "Content-Type": "application/json",
                },
            ):
                if chunk_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(chunk_str)
                    delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if delta:
                        yield delta
                except Exception:
                    continue
        return stream_generator()
        
    data = call_rotating_chat_completion(
        provider="openrouter",
        api_keys=api_keys,
        model=model,
        url="https://openrouter.ai/api/v1/chat/completions",
        payload=payload,
        headers={
            "HTTP-Referer": "https://localhost",
            "X-Title": "KundaliStudio",
            "Content-Type": "application/json",
        },
    )
    text = extract_chat_completion_text(data)
    if not text:
        raise RuntimeError("OpenRouter response did not contain output text")
    return answer_payload(text, "llm", "openrouter", model, "")


def call_cerebras(sys_prompt: str, usr_prompt: str, model: str = None) -> dict:
    api_keys = api_keys_for("CEREBRAS")
    if not api_keys:
        raise RuntimeError("CEREBRAS_API_KEY or CEREBRAS_API_KEYS is not set")
    model = model or os.getenv("CEREBRAS_INTERPRETATION_MODEL", DEFAULT_CEREBRAS_MODEL)
    payload = chat_completion_payload(model, sys_prompt, usr_prompt)
    data = call_rotating_chat_completion(
        provider="cerebras",
        api_keys=api_keys,
        model=model,
        url="https://api.cerebras.ai/v1/chat/completions",
        payload=payload,
        headers={"Content-Type": "application/json"},
    )
    text = extract_chat_completion_text(data)
    if not text:
        raise RuntimeError("Cerebras response did not contain output text")
    return answer_payload(text, "llm", "cerebras", model, "")


def chat_completion_payload(model: str, sys_prompt: str, usr_prompt: str, stream: bool = False) -> dict:
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": usr_prompt},
        ],
        "temperature": 0.7,
        "stream": stream,
    }


def extract_openai_text(data: dict) -> str:
    if data.get("output_text"):
        return data["output_text"].strip()
    parts = []
    for item in data.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if text:
                parts.append(text)
    return "\n".join(parts).strip()


def extract_gemini_text(data: dict) -> str:
    parts = []
    for candidate in data.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            text = part.get("text")
            if text:
                parts.append(text)
    return "\n".join(parts).strip()


def extract_chat_completion_text(data: dict) -> str:
    parts = []
    for choice in data.get("choices", []):
        text = choice.get("message", {}).get("content")
        if text:
            parts.append(text)
    return "\n".join(parts).strip()


def answer_payload(text: str, mode: str, provider: str, model: str, note: str) -> dict:
    return {
        "text": clean_text(text),
        "mode": mode,
        "provider": provider,
        "model": model,
        "note": note,
    }


def llm_unavailable_payload(message: str) -> dict:
    return {
        "text": "",
        "mode": "llm_required",
        "provider": selected_provider_label(),
        "model": "",
        "note": message,
        "error": message,
    }


def llm_answer(sys_prompt: str, usr_prompt: str, provider: str, caller, stream: bool = False):
    if 'stream' in caller.__code__.co_varnames:
        return caller(sys_prompt, usr_prompt, stream=stream)
    return caller(sys_prompt, usr_prompt)


def clean_text(text: str) -> str:
    return textwrap.dedent(text).strip()
