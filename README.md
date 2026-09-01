# Form Assistant — AWS Proof of Competence

A deliberately small, verifiable slice of a multilingual form assistant:
LLM dialogue orchestration, retrieval with traceable sources, and a PII
masking boundary, deployable to AWS Lambda via SAM.

## What this proves

- **Sensitive values never reach a model call — enforced and tested.**
  Sensitive field values are replaced by typed placeholder tokens (`[NAME_1]`,
  `[ID_1]`, …) before any model-bound payload is built, and every payload
  passes a mandatory audit that raises if a registered value leaks.
  `tests/test_masking.py` captures the real outbound payloads and proves it.
- **Retrieval answers are traceable to a source — or refuse.**
  Every answer cites `doc_id / section_id` from the guidance corpus. A
  question the corpus does not cover returns "no source found" and makes
  **no model call at all** — no hallucinated guidance. Questions matching
  legal-assessment triggers are refused with a fixed safe message.
- **The dialogue runtime executes a moving behavioral spec as data.**
  Field order, validation rules, and conditional follow-ups live in
  `form_spec.json`. The runtime is generic: an externally produced
  behavioral specification can change without touching the code.

## Run the tests offline (no AWS account, no API key)

```bash
pip install -e .[dev]
pytest
```

All tests run against the deterministic `MockProvider`.

## Offline demo

```bash
python -m form_assistant.demo
```

Answer the form prompts, then ask questions (e.g. "When is the registration
deadline?"). Each answer prints its source reference and the exact masked
payload that was sent to the (mock) model. Set `ANTHROPIC_API_KEY` to switch
the provider to Claude (`claude-sonnet-5`); nothing else changes.

## Architecture

```
User ──> API Gateway ──> Lambda (form_assistant.app.lambda_handler)
                            │
         ┌──────────────────┼─────────────────────┐
         │                  │                     │
    Orchestrator        Retrieval            Refusal check
  (spec as JSON data) (corpus + source     (declarative trigger
                        references)              list)
         │                  │
         └───── PII masking boundary ─────> LLM provider
              (tokens in, audit on          (MockProvider offline /
               every outbound payload)       Claude claude-sonnet-5)
```

CloudWatch: log group with 14-day retention plus an alarm on Lambda errors
(`template.yaml`).

## Deploy with SAM

**Live deployment** (eu-central-1, Lambda + API Gateway, deployed with the
commands below):

```
https://gr0hz97g21.execute-api.eu-central-1.amazonaws.com/Prod/assistant
```

```bash
curl -X POST https://gr0hz97g21.execute-api.eu-central-1.amazonaws.com/Prod/assistant \
  -H "Content-Type: application/json" \
  -d '{"question": "What documents do I need for residence registration?"}'
# -> {"type": "answer", ..., "source": {"doc_id": "sample-residence-registration-guide", "section_id": "required-documents"}}
```

To deploy your own copy:

```bash
sam build
sam deploy --guided
```

Then:

```bash
curl -X POST "$API_URL" -H "Content-Type: application/json" \
  -d '{"question": "When is the registration deadline?", "fields": {"full_name": "Alex Sample"}}'
```

### CI deploy gate

`.github/workflows/ci.yml` runs pytest on every push with no secrets. The
deploy job runs only on `main` **and** only when the repository *variable*
`AWS_DEPLOY_ENABLED` is set to `true` (GitHub does not allow reading secrets
inside `if:` conditions, so a variable acts as the gate). To enable deploys,
configure the secrets `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`, the
optional variable `AWS_REGION`, and set `AWS_DEPLOY_ENABLED=true`.

## Scope note

This is a deliberately small, verifiable slice — not a product. The corpus is
invented generic guidance content, the retrieval is plain lexical matching,
and the dialogue spec covers one sample form. The point is that the failure
modes that matter (PII leaking into model calls, untraceable answers,
hallucinated guidance, answering legal questions) are structurally prevented
and covered by tests, in a shape that scales to the real thing.
