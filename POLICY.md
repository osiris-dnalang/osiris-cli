# OSIRIS Local Runtime Policy

This policy governs the canonical OSIRIS repository and its local runtime. It is
deliberately narrower than the project's research and product aspirations.

## Authority model

- Human intent and explicit constraints are inputs, not execution grants.
- Models, agents, Φ/CCCE/W2 values, confidence, classifications, and generated
  explanations may propose work but never authorize it.
- Host-side policy validates schemas, paths, artifacts, budgets, and execution mode.
- An isolated worker may execute only a host-issued, expiring capability.
- Promotion from staging to a protected workspace requires explicit human approval
  bound to the exact candidate and evidence hashes.

## Default-deny capabilities

The following are denied unless a separate policy version, implementation, negative
tests, evidence record, and human approval establish a narrower capability:

- Network access, cloud APIs, remote models, MCP servers, and web research.
- Shell execution, arbitrary subprocesses, native-module loading, and dynamic code
  execution.
- Exchange, broker, wallet, market-order, and financial-account access.
- Quantum hardware submission, publication, public deployment, and automatic Git push.
- Credential discovery, export, rotation, or access to SSH, cloud, provider, or
  browser/session credentials.
- Deletion, recursive cleanup, filesystem mounts, host sockets, and access outside
  an explicit workspace or job root.

## Artifact handling

- Treat `.dna`, model output, archives, generated code, and experiment files as
  untrusted input.
- Require a bounded schema and content hash before an artifact enters a workflow.
- Reject native binaries, unknown executable payloads, oversized files, and
  unsupported archive formats before loader or worker dispatch.
- Store references and hashes instead of raw secrets or unbounded payloads.

## Cloud and external services

The GCP project `dnalang` and the Cloud Shell identity observed during planning are
operator resources, not OSIRIS runtime credentials. Cloud Shell ADC, browser state,
tokens, API keys, service-account keys, and project metadata must not enter agents,
workers, model prompts, repositories, artifacts, MCP, or local ledgers.

No cloud resource creation, API enablement, public endpoint, agent deployment, or
remote provider call is approved by this policy.

## Verification standard

A capability is `verified` only when implementation, focused tests, a declared clean
environment result, boundary documentation, and an evidence record all exist.
Otherwise report `planned`, `partial`, `implemented-unverified`, `blocked`, or
`disabled`. A syntax check alone is not a security or policy verification.
