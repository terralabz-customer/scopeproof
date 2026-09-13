# ScopeProof — Devpost preparation

**Status: prepared; not submitted.** Installation, tests, real model runs, browser/export checks, public source and a reviewed 136-second demo MP4 are complete. Devpost, AWS Builder and YouTube account sign-ins, the required YouTube/Vimeo upload and the final submission receipt remain pending.

## Submission fields

- **Project name:** ScopeProof
- **Tagline:** Turn a client brief into a scope you can explain.
- **Track:** Professional Agents
- **Public source repository:** https://github.com/terralabz-customer/scopeproof
- **Public YouTube or Vimeo video:** PENDING — planned captioned montage of screenshots from actual runs, labeled as edited screenshots rather than real-time screen recording.
- **AWS Builder ID:** PENDING — use the entrant's actual ID in the form, not this public file.
- **Entrant and authorized representative:** PENDING — confirm individual or organization entry.
- **Optional live demo:** None claimed. Local build and setup instructions were tested on Windows.
- **Build start:** 13 September 2026
- **Built with:** Python 3.12, Strands Agents SDK, Ollama, Qwen3 4B Instruct, FastAPI, Pydantic, HTML, CSS, JavaScript.
- **Short description:** A local Strands agent maps freelance briefs to a synthetic service catalog, preserves exact source evidence, withholds uncertain prices and exports a scope review pack.

## Inspiration

Freelance developers have to turn informal client messages into clear scope before agreeing fixed-price work. A brief can mix a small task with extra features or omit essential inputs. ScopeProof explores how an agent can prepare a reviewable scope while leaving the commitment to the freelancer. This prototype has not been validated with customers.

## What it does

ScopeProof reads a brief and optional change request against four synthetic services. It preserves exact source statements, marks included, unclear and excluded requests, and assigns a catalog sample price only when one service is fully resolved. Other scopes remain unpriced. Its ZIP contains a scope review, draft client message, evidence/audit JSON and proposed delivery checklist. The app does not contact clients or perform the proposed development work.

## How we built it

FastAPI connects a browser interface to a Strands agent using local Ollama. The agent calls `read_catalog`, then `validate_scope` with service, capability and source-segment IDs. Python reconstructs evidence from the original input and applies catalog, quantity and vocabulary checks. The model cannot supply evidence text or prices. The Ollama host is restricted to loopback; no AWS or AgentCore deployment is claimed.

## Challenges and decisions

The design separates model interpretation from source evidence and pricing. A narrow compiler preserves source text and withholds a price when required scope is unresolved. This has a tradeoff: its English patterns and controlled vocabulary may reject valid unfamiliar phrasing. Exact provenance is not proof of correct interpretation. Broader semantic reliability remains unmeasured.

## Accomplishments and learning

On 13 September we verified a fresh editable installation on Windows 11 with Python 3.12.10: 28 tests passed, Ruff passed and dependency checks found no broken requirements. Real Strands runs used local Ollama 0.34.0 and qwen3:4b-instruct on a Ryzen 7 5700X CPU with 64 GiB RAM.

A clear landing-page brief produced the USD 120 sample estimate in 33.02 seconds; adding login and Stripe checkout withheld the price in 30.30 seconds. An adversarial instruction example remained unpriced without observed price mutation or disclosure in 33.38 seconds. A CSV-cleanup brief produced the USD 60 sample estimate in 31.28 seconds. Each run used two model calls and two tool calls. These are individual synthetic examples, not a broad benchmark.

The browser's copy action and actual ZIP download were verified; all four files were present and the inspected price and evidence matched the result. A 375-pixel viewport check showed no horizontal overflow or browser errors/warnings. No time savings, client adoption or revenue have been measured.

## Next steps

Evaluate missed and misclassified requests using consented data, support catalog editing and improve unfamiliar-language handling. These are proposed next steps.

## Originality and AI disclosure

ScopeProof's project-specific source, interface, documentation and synthetic examples were created starting 13 September 2026 with AI coding assistance. It uses existing open-source libraries and a separately obtained model; their own licenses apply. The examples do not contain real client data. This submission does not claim that existing Cerebretron code, customers, revenue or past client work were created for this hackathon. Verify the final source inventory and disclose any additional reused material before submission.

## Official requirements checked on 13 September 2026

The [official rules](https://agentsforhumans.devpost.com/rules) require a new working Strands project; public MIT/Apache source with README and architecture; an English description; AWS Builder ID; and a public YouTube/Vimeo demonstration and pitch of at most five minutes. The entry steps also list an AWS account. A live URL and AgentCore deployment are optional. Judges need free access to a working build through 8 October.

The submission deadline is **15 September 2026 at 05:30 Sri Lanka time** (14 September, 17:00 PDT). Winners are expected around 14 October, with payment only after required winner verification; no award or payment is assured. Read the full eligibility and entry terms before submitting.

The [resources page](https://agentsforhumans.devpost.com/resources) says the promotional AWS credits have all been distributed. This build does not depend on obtaining them.

## Completion checklist

- [ ] Confirm entrant details, eligibility and authority to submit.
- [ ] Verify the AWS account and Builder ID requirements with the actual entrant.
- [x] Complete a clean installation and actual Strands/model run.
- [x] Record the model, test results and limitations.
- [x] Check browser copy, the actual export and narrow-screen layout.
- [ ] Record the final published source revision.
- [x] Review source and assets for rights, license notices and private information.
- [x] Publish the authorized public repository with visible MIT license.
- [x] Build and review the 136-second captioned actual-run screenshot montage and pitch.
- [ ] Upload the MP4 to the required public YouTube or Vimeo host.
- [ ] Replace pending fields; align all claims with the recorded build.
- [ ] Complete Devpost and verify the final submission receipt before the deadline.

Unchecked items are outstanding work. Devpost, AWS Builder and YouTube sign-ins still need to be completed. No YouTube/Vimeo publication, submission receipt or award is claimed.
