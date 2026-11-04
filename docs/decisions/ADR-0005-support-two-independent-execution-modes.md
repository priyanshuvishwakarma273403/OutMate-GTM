# ADR-0005: Support for Two Independent Execution Modes (Standalone Agent & Claude.ai)

## Status
Accepted

## Context
Users have diverse workflows when conducting GTM research:
- Some users prefer an autonomous standalone Python script, background cron pipeline, or programmatic API that runs unattended.
- Other users prefer interactive research within the Claude.ai conversational chat interface, utilizing Claude's reasoning, markdown tables, and interactive follow-ups.

Building two separate products or maintaining duplicate research logic across two repositories would cause severe maintenance overhead and divergence.

## Decision
We architected Outmate GTM to support **two independent execution modes** from day one:
- **Mode A**: Standalone Python AI Agent using OpenRouter.
- **Mode B**: Claude.ai integration using a remotely hosted MCP server over SSE.

Both modes are powered by the identical shared service kernel.

## Consequences

### Positive
- **Maximum Versatility**: Serves both developer/automated use-cases (Mode A) and conversational/ad-hoc research use-cases (Mode B).
- **Single Source of Truth**: Research heuristics, scraping filters, verification rules, and scoring formulas are updated once in `app/services/` and apply instantly to both execution modes.
- **Independent Failure Domains**: A Claude.ai connection issue does not affect the standalone OpenRouter agent, and vice versa.

### Negative
- Requires designing tools and outputs to be equally consumable by autonomous agent loops and human-facing conversational hosts.

