from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class LLMVerdict:
    verdict: str
    score: float
    reasons: List[str]
    suggestions: List[str]
    missing_sections: List[str]

    def passed(self, threshold: float = 0.75) -> bool:
        return self.verdict.lower() == "pass" and self.score >= threshold


def _format_prompt(url: str, title: Optional[str], html_excerpt: str, markdown: str) -> str:
    return (
        "You are a meticulous documentation QA assistant. Given an HTML excerpt and a Markdown conversion, "
        "judge whether the Markdown accurately and cleanly represents the original content.\n"
        f"URL: {url}\nTitle: {title or ''}\n\n"
        "HTML excerpt (first ~3000 chars):\n" + html_excerpt[:3000] + "\n\n"
        "Markdown candidate:\n" + markdown[:6000] + "\n\n"
        "Return strict JSON with keys: verdict ('pass'|'fail'), score (0..1), reasons (string[]), suggestions (string[]), missing_sections (string[])."
    )


def evaluate_with_openai(url: str, title: Optional[str], html_text: str, markdown: str, model: Optional[str] = None) -> Optional[LLMVerdict]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI  # type: ignore
    except Exception:
        return None

    client = OpenAI(api_key=api_key)
    model = model or os.getenv("WEBTOMD_LLM_MODEL", "gpt-4o-mini")
    prompt = _format_prompt(url, title, html_text, markdown)
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        content = resp.choices[0].message.content or "{}"
        data = json.loads(content)
        return LLMVerdict(
            verdict=str(data.get("verdict", "fail")),
            score=float(data.get("score", 0.0)),
            reasons=list(data.get("reasons", [])),
            suggestions=list(data.get("suggestions", [])),
            missing_sections=list(data.get("missing_sections", [])),
        )
    except Exception:
        return None

