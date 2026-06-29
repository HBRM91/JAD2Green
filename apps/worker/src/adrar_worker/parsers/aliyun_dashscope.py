"""
Aliyun DashScope adapter for PaddleOCR-VL-1.5.

Multilingual OCR (FR/AR/EN) used for messy PDF scans. Returns plain text
extracted from the document; downstream LLM (Qwen3-Plus via OpenRouter)
structures it into activity_facts.

DASHSCOPE_API_KEY env var required. Returns empty string on any failure
(callers log the skip; the user can always re-upload with a clean PDF).
"""

from __future__ import annotations

import os

_OCR_MODEL = "paddleocr-vl"


def ocr_scan(content: bytes) -> str:
    """
    Run PaddleOCR-VL-1.5 over the PDF and return concatenated page text.

    Returns "" if DASHSCOPE_API_KEY is missing or the call fails.
    """
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        return ""

    try:
        import dashscope  # type: ignore
        from dashscope import MultiModalConversation  # type: ignore
    except Exception:
        return ""

    dashscope.api_key = api_key
    import base64
    b64 = base64.standard_b64encode(content).decode()

    messages = [
        {
            "role": "user",
            "content": [
                {"image": f"data:application/pdf;base64,{b64}"},
                {"text": "Extract all text from this document. Return plain text only."},
            ],
        }
    ]
    try:
        resp = MultiModalConversation.call(model=_OCR_MODEL, messages=messages)
        if not resp or not getattr(resp, "output", None):
            return ""
        chunks = resp.output.get("choices", [])
        if not chunks:
            return ""
        content = chunks[0].get("message", {}).get("content", [])
        parts = [c.get("text", "") for c in content if isinstance(c, dict) and c.get("text")]
        return "\n".join(parts).strip()
    except Exception:
        return ""
