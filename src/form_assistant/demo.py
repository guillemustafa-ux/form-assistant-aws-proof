"""Offline console demo: ``python -m form_assistant.demo``.

Runs the full dialogue with the deterministic mock provider, then answers
questions until EOF. After each model-backed answer it prints the exact
outbound payload so the masking boundary is visible, not just claimed.
"""

from __future__ import annotations

import json
import sys

from .app import FormAssistant
from .llm import MockProvider


def main() -> int:
    provider = MockProvider()
    assistant = FormAssistant.default(provider=provider)

    print("form-assistant offline demo (mock provider, no API key needed)")
    print("--- form dialogue ---")
    while not assistant.session.is_complete:
        field = assistant.session.current_field()
        print(f"> {field['prompt']}")
        line = sys.stdin.readline()
        if not line:
            print("(EOF) exiting before form completion")
            return 0
        result = assistant.session.submit(line.strip())
        if not result.accepted:
            print(f"  rejected: {result.error}")

    print(f"form complete. masked state: {json.dumps(assistant.session.masked_answers())}")
    print("--- questions (Ctrl-D / EOF to exit) ---")
    for line in sys.stdin:
        question = line.strip()
        if not question:
            continue
        print(f"? {question}")
        result = assistant.ask(question)
        if result["type"] == "answer":
            src = result["source"]
            print(f"  {result['answer']}")
            print(f"  passage: {result['passage']}")
            print(f"  source: {src['doc_id']} / {src['section_id']} ({src['heading']})")
            print(f"  outbound payload (audited, masked): {json.dumps(provider.payloads[-1])}")
        else:
            print(f"  [{result['type']}] {result['message']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
