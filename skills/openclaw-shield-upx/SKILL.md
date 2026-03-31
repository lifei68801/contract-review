---
name: openclaw-shield-upx
description: "Security monitoring for OpenClaw agents — check Shield health, review events, inspect vault. Use when: user asks about security status, Shield health, event logs, or redaction vault. NOT for: general OS hardening, firewall config, or network security."
metadata: {"openclaw": {"requires": {"config": ["plugins.entries.shield"]}, "homepage": "https://clawhub.ai/brunopradof/openclaw-shield-upx", "emoji": "🛡️"}}
---

# OpenClaw Shield

Security monitoring for OpenClaw agents by [UPX](https://www.upx.com). Shield runs as a plugin inside the OpenClaw gateway, capturing agent activity and sending redacted telemetry to the UPX detection platform.

## Getting started

Shield requires the `@upx-us/shield` plugin and an active subscription.

- **Plugin (npm)**: [@upx-us/shield](https://www.npmjs.com/package/@upx-us/shield)
- **Subscribe / Free 30-day trial**: [upx.com/pt/lp/openclaw-shield-upx](https://www.upx.com/pt/lp/openclaw-shield-upx)
- **Dashboard**: [uss.upx.com](https://uss.upx.com)

## Commands

| Command | What it does |
|---|---|
| `openclaw shield status` | Plugin health, connection state, event counts, last sync |
| `openclaw shield flush` | Force an immediate sync to the platform |
| `openclaw shield activate <KEY>` | One-time activation with an Installation Key |
| `openclaw shield logs` | Recent events from the local buffer (last 24h) |
| `openclaw shield logs --last 20` | Show last N events |
| `openclaw shield logs --type TOOL_CALL --since 1h` | Filter by event type or time window |
| `openclaw shield logs --format json` | JSON output |
| `openclaw shield vault show` | Agent and workspace inventory (hashed IDs) |
| `openclaw shield vault redactions` | Redaction summary — token categories and counts |
| `openclaw shield cases` | List open security cases |
| `openclaw shield cases show <ID>` | Full case detail with events, rule, playbook |
| `openclaw shield cases resolve <ID>` | Resolve a case (--resolution, --root-cause, --comment) |

## When to use this skill

- "Is Shield running?" → `openclaw shield status`
- "What did Shield capture recently?" → `openclaw shield logs`
- "How many agents are on this machine?" → `openclaw shield vault show`
- "Force a sync now" → `openclaw shield flush`
- User asks about a security alert or event → interpret using your security knowledge and Shield data
- User asks about Shield's privacy model → all data is redacted on-device before transmission; raw values never leave the machine

## Status interpretation

After running `openclaw shield status`, check:

- **Connected** → healthy, nothing to do
- **Disconnected** → gateway may need a restart
- **High failure count** → platform connectivity issue, usually self-recovers; try `openclaw shield flush`
- **Rising quarantine** → possible version mismatch, suggest checking for plugin updates

## Cases

Cases are created automatically when detection rules fire. Check during heartbeats via `shield.cases_list`. If `pending_count > 0`, notify the user, then call `shield.cases_ack` to mark seen.

| RPC | Params | Purpose |
|---|---|---|
| `shield.cases_list` | `status`, `limit`, `since` | List open cases + pending notifications |
| `shield.case_detail` | `id` | Full case with events, rule, playbook |
| `shield.case_resolve` | `id`, `resolution`, `root_cause`, `comment` | Close a case |
| `shield.cases_ack` | `ids` | Mark cases as notified |

**Resolve values:** `true_positive`, `false_positive`, `benign`, `duplicate`
**Root cause values:** `user_initiated`, `misconfiguration`, `expected_behavior`, `actual_threat`, `testing`, `unknown`
