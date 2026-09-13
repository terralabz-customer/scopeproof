# ScopeProof architecture

![Six-block local ScopeProof architecture](architecture.svg)

This diagram describes the local implementation in `scopeproof/core.py` and `scopeproof/server.py`. The README records the separate real-model and browser checks observed on 13 September 2026; the diagram itself is an explanation of the data flow.

## Data flow

1. **Brief and review interface.** A browser collects a brief or a synthetic demo and displays the resulting scope. It also provides the export action.
2. **FastAPI application.** The local server receives the brief, coordinates the workflow and returns the output for review.
3. **Strands agent.** The agent calls `read_catalog` for four synthetic services and immutable source segments, then `validate_scope` with service IDs, capability IDs and source-segment assessments. It cannot supply new evidence text or prices.
4. **Ollama model.** A local model supplies language interpretation and structured selections. Configuration requires an explicit installed model and a loopback host. Remote model hosts and model IDs ending in `:cloud` are rejected.
5. **Catalog and deterministic checks.** Python reconstructs quotes from input segments, checks service capability patterns and quantities, and calculates a sample price only for a fully resolved single-service scope. Missing, mixed, excluded or changed scope remains unpriced.
6. **Review pack and human decision.** The application assembles a ZIP with a Markdown scope review, draft client message, evidence/audit JSON and proposed delivery checklist. A person decides whether to edit or share it. The app does not perform the services listed in the checklist.

## Boundaries

The browser, application, model and catalog run on one computer. Non-loopback Ollama hosts are rejected. No AWS hosting, AgentCore runtime, paid model endpoint, client-messaging integration or payment system is part of this diagram. Strands is the orchestration SDK; Ollama is the model provider. A future deployment would need a separate implementation and description.

Client text is untrusted input. The tool schema accepts IDs and assessments rather than model-authored evidence or money. All source segments remain in the compiled review, including segments the model left unclassified. Instruction-like text is flagged by a pattern check; this is not a claim that every injection or ambiguity is detected.

The compiler uses English patterns and a controlled vocabulary. Unfamiliar phrasing can be marked for clarification even when a person could accept it. Exact source provenance does not prove correct interpretation, completeness or feasibility. The service catalog determines illustrative prices and limits.

The API stores runs in memory and produces downloads on demand. The audit JSON includes the original brief and change request. A ZIP is a review artifact, not an accepted agreement, sent message or completed client delivery.

## What to verify in the final build

- Trace a real brief through Strands and Ollama, then through the validation and export code.
- Confirm that unknown services, altered catalog prices and quotes absent from the brief cannot silently become approved facts.
- Confirm that sample output and any offline preview are visibly distinguished from a live agent result.
- Confirm that the exported pack represents the result the reviewer saw.
- Record how errors, long model responses and unavailable Ollama are presented.

The README records completed checks. Further test cases are needed to assess how often the model or controlled vocabulary misses valid or ambiguous requests.
