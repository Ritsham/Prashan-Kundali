"""LLM Engine — Main generator entry point.

Pipeline:
    chart (dict)
        └─► insight_engine.build_interpretation()  →  interpretation (dict)
                └─► llm_engine.generate_interpretation_answer()  →  answer (dict)
                        ├─► prompts (Map-Reduce)
                        └─► providers.*               calls the configured LLM

Public API:
    generate_interpretation_answer(chart, interpretation) -> dict
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.llm_engine.config import (
    caller_for_provider,
    load_local_env,
    provider_order,
)
from app.llm_engine.providers import llm_answer, llm_unavailable_payload
from app.llm_engine.prompts import (
    foundation_prompt,
    domain_prompt,
    timing_prompt,
    synthesizer_prompt
)
from app.config import get_settings

logger = logging.getLogger(__name__)


import redis
import json

def generate_interpretation_answer(chart: dict, interpretation: dict, chart_id: str = None) -> dict:
    load_local_env()

    chart_type = chart.get("meta", {}).get("chart_type", "unknown")
    domain = interpretation.get("domain", "general")
    logger.info("[llm_engine] Generating narrative (Map-Reduce) | chart_type=%s domain=%s", chart_type, domain)

    errors = []
    for provider in provider_order():
        try:
            logger.info("[llm_engine] Trying provider: %s", provider)
            caller = caller_for_provider(provider)
            
            # Step 1: Map (Run 3 parallel tasks)
            f_sys, f_usr = foundation_prompt(chart, interpretation)
            d_sys, d_usr = domain_prompt(chart, interpretation)
            t_sys, t_usr = timing_prompt(chart, interpretation)

            with ThreadPoolExecutor(max_workers=3) as executor:
                future_f = executor.submit(llm_answer, f_sys, f_usr, provider, caller)
                future_d = executor.submit(llm_answer, d_sys, d_usr, provider, caller)
                future_t = executor.submit(llm_answer, t_sys, t_usr, provider, caller)

                f_result = future_f.result()
                d_result = future_d.result()
                t_result = future_t.result()

            # Step 2: Reduce (Synthesize)
            s_sys, s_usr = synthesizer_prompt(chart, interpretation, f_result["text"], d_result["text"], t_result["text"])
            
            # Request streaming only if provider supports it and chart_id is provided
            supports_stream = provider in ["openrouter", "groq"]
            if chart_id and supports_stream:
                stream_gen = llm_answer(s_sys, s_usr, provider, caller, stream=True)
                
                redis_client = redis.Redis.from_url(get_settings().redis_url)
                full_text = ""
                for chunk in stream_gen:
                    full_text += chunk
                    redis_client.publish(f"stream:{chart_id}", json.dumps({"text": chunk}))
                redis_client.publish(f"stream:{chart_id}", json.dumps({"done": True}))
                
                from app.llm_engine.providers import answer_payload
                final_result = answer_payload(full_text, "llm", provider, "", "")
            else:
                final_result = llm_answer(s_sys, s_usr, provider, caller)
                if chart_id:
                    redis_client = redis.Redis.from_url(get_settings().redis_url)
                    redis_client.publish(f"stream:{chart_id}", json.dumps({"text": final_result["text"]}))
                    redis_client.publish(f"stream:{chart_id}", json.dumps({"done": True}))

            logger.info("[llm_engine] Success | provider=%s", provider)
            return final_result
            
        except Exception as exc:
            logger.warning("[llm_engine] Provider %s failed: %s", provider, exc)
            errors.append(f"{provider}: {exc}")

    return llm_unavailable_payload("; ".join(errors) or "All LLM providers failed")
