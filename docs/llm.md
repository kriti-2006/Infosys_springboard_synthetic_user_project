# LLM layer
* All LLM calls go through `llm.py` (`invoke_*` sync from Milestone 2; `ainvoke_structured`, `aembed` for Milestone 3). Provider: OpenRouter; model: `OPENROUTER_MODEL`.
* Every important call has a Pydantic output schema (`schemas_m3.py`): `PersonaAnswer`, `ValidationResult`, `InsightLLMOut`, `UsageEval`. Invalid output => retry/fallback => `LLMError(kind=invalid_output)`; nothing invalid is written to the DB.
* Errors are typed: `timeout` (504), `rate_limit`/`unavailable`/`invalid_output` (502). Rate limits back off 3x longer. A global semaphore bounds concurrent calls.
* Prompts are in the agent modules. Temperatures: answers 0.8, validation 0.0, insights/usage 0.2.
* Cost model: per answer = 1 generation + 1 validation (+1 regeneration on failure). 20 personas x 20 questions ~ 800-1,200 calls; set `SURVEY_LLM_VALIDATION=false` to halve it.
