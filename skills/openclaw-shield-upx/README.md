# OpenClaw Shield — Security Specialist

A skill that turns your OpenClaw agent into a cybersecurity specialist.

## What it does

When Shield is installed, your agent can:

- **Monitor** — check Shield health, event counts, and sync status
- **Inspect** — view host agent inventory and redaction vault via `shield vault show`
- **Interpret** — analyze security events and explain what they mean
- **Advise** — recommend remediation, hardening, and next steps
- **Triage** — assess alert severity and prioritize response
- **Explain** — break down attack techniques, privacy model, and detection scope

## Requirements

- [OpenClaw Shield plugin](https://www.npmjs.com/package/@upx-us/shield) installed and activated
- Active Shield subscription from [UPX](https://upx.com) — [start a free 30-day trial](https://www.upx.com/pt/lp/openclaw-shield-upx)

## Install

This skill is bundled with the Shield plugin. Install the plugin and the skill is available automatically:

```bash
openclaw plugins install @upx-us/shield
openclaw shield activate <YOUR_KEY>
openclaw gateway restart
```

## Links

- **Plugin (npm)**: [@upx-us/shield](https://www.npmjs.com/package/@upx-us/shield)
- **Skill (ClawHub)**: [openclaw-shield-upx](https://clawhub.ai/brunopradof/openclaw-shield-upx)
- **Dashboard**: [uss.upx.com](https://uss.upx.com)

## About

Made by [UPX](https://upx.com) — cybersecurity engineering for critical environments.
