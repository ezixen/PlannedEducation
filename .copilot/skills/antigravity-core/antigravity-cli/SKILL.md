---
name: antigravity-cli
description: Comprehensive operational manual and tool guide for the Google Antigravity CLI (agy). Covers launching interactive and headless agent sessions, model selection (strongly recommending Gemini 3.8 Flash on High Reasoning to prevent 429 quota exhaustion), authentication and account switching, slash commands, CLI flags, headless automation, reasoning effort levels, and sandbox security.
---

# Google Antigravity CLI (`agy`) — Developer & Agent Manual

The **Antigravity CLI (`agy`)** is a lightweight, high-performance terminal interface for Google Antigravity. It enables interactive agent collaboration, automated headless pipeline execution, model steering, and multi-agent workflows directly from PowerShell, Bash, or CI/CD environments.

---

## 1. System Installation & Locations

- **CLI Binary**: `C:\Users\ezixen\AppData\Local\agy\bin\agy.exe` (available globally on system `PATH` as `agy`)
- **CLI Configuration Directory**: `~/.gemini/antigravity-cli/`
- **Settings File**: `~/.gemini/antigravity-cli/settings.json`
- **Keyring Credential Target**: `gemini:antigravity` (in Windows Credential Manager)

To verify the installation:
```powershell
agy --help
```

---

## 2. ⚡ Recommended Model & Reasoning Configuration (CRITICAL)

> [!IMPORTANT]
> **ALWAYS PREFER `gemini-3.8-flash-high` (Gemini 3.8 Flash on High Reasoning)**.
> Heavyweight models (`gemini-4-argon-*`, `claude-sonnet-5-5-*`, `claude-opus-5-5-*`, and `gpt-oss-120b-*`) have **very low rate limits and strict token quotas** on consumer Google accounts. They quickly trigger `RESOURCE_EXHAUSTED (code 429): Individual quota reached... Resets in ~71-75h`.
>
> In contrast, **`gemini-3.8-flash-high`** (and `gemini-3.8-flash-medium`) has **vastly higher quota limits**, near-instant latency, and provides deep reasoning and code synthesis capability comparable to larger models when set to high reasoning effort.

### Available Models & Rate Limit Profile

| Model Identifier | Display Label | Rate / Quota Limit | Recommended Use |
|:---|:---|:---:|:---|
| **`gemini-3.8-flash-high`** | **Gemini 3.8 Flash (High)** | **Very High (Generous)** | **PRIMARY DEFAULT** for coding, planning, reviews |
| `gemini-3.8-flash-medium` | Gemini 3.8 Flash (Medium) | Very High (Generous) | High speed, quick responses |
| `gemini-3.8-flash-low` | Gemini 3.8 Flash (Low) | Highest | Simple queries, linting |
| `gemini-4-argon-medium` | Gemini 4 Argon (Medium) | Very Low (429 risk) | Special tasks only (resets weekly) |
| `claude-sonnet-5-5-medium` | Claude Sonnet 5.5 | Very Low (429 risk) | Exhausts fast under heavy code tasks |
| `claude-opus-5-5-medium` | Claude Opus 5.5 | Very Low (429 risk) | Heavy quota consumption |
| `gpt-oss-120b-medium` | GPT-OSS 120B | Very Low (429 risk) | Strict rate cap |

### Recommended Invocations

```powershell
# 1. Standard Interactive Session (Recommended):
agy --model gemini-3.8-flash-high

# 2. Non-interactive Prompt with High Reasoning:
agy -p "Analyze git status and write test suite" --model gemini-3.8-flash-high

# 3. Explicit Reasoning Effort:
agy --model gemini-3.8-flash-medium --effort high

# 4. Automated Headless Run (CI/CD):
agy -p "run_tests.py" --model gemini-3.8-flash-high --dangerously-skip-permissions --output-format json
```

### Setting Gemini 3.8 Flash as Default

To avoid specifying `--model` on every run, configure `~/.gemini/antigravity-cli/settings.json`:
```json
{
  "model": "gemini-3.8-flash-high",
  "effort": "high"
}
```

---

## 3. Authentication & Account Management

Antigravity CLI isolates its credentials from other system services. It stores its OAuth tokens in the operating system's native secure keyring (Windows Credential Manager) under target `gemini:antigravity`.

### Current Authenticated Account
- **CLI Account**: `jatepa21@gmail.com`
- Verified from `gemini:antigravity` keyring `id_token` and runtime logs (`OAuth: authenticated successfully as jatepa21@gmail.com`).
- Other Google services on the workstation (Google Drive File Stream, Chrome, Google Cloud SDK) remain untouched.

### A. Logging Out & Switching Accounts
To switch accounts without disturbing other Google services:

1. **Interactive Method (Inside CLI)**:
   ```text
   agy
   /logout
   ```
   Restart `agy` — it will open the browser and prompt you to select an account.

2. **Direct Windows Keyring Purge**:
   To clear only the Antigravity CLI token:
   ```powershell
   cmdkey /delete:gemini:antigravity
   ```
   On next launch (`agy`), select or enter `jatepa21@gmail.com` in the browser OAuth prompt.

### B. Headless / API Key Authentication
For CI/CD or automated scripts without a browser:
1. In `~/.gemini/antigravity-cli/settings.json`:
   ```json
   {
     "modelProvider": "gemini"
   }
   ```
2. Set your Gemini API key in the environment:
   ```powershell
   $env:GEMINI_API_KEY = "your-api-key-here"
   ```

---

## 4. Command-Line Flags & Execution Modes

`agy` supports both interactive Terminal User Interface (TUI) and non-interactive scripted modes.

### Core Command Syntax
```powershell
agy [flags] [subcommand]
```

### Key CLI Flags

| Flag | Short | Description | Example |
|:---|:---:|:---|:---|
| `--model <name>` | | Override the AI model for this session | `agy --model gemini-3.8-flash-high` |
| `--effort <level>` | | Set reasoning effort (`low`, `medium`, `high`, `xhigh`, `max`) | `agy --effort high` |
| `--print` | `-p` | Run a single prompt non-interactively and output response | `agy -p "Review commit diff"` |
| `--prompt-interactive` | `-i` | Run an initial prompt interactively and continue session | `agy -i "Start refactor plan"` |
| `--continue` | `-c` | Resume the most recent conversation session | `agy -c` |
| `--conversation <id>` | | Resume a specific conversation by UUID | `agy --conversation abc-123` |
| `--mode <mode>` | | Set agent execution mode (`accept-edits`, `plan`, `auto`) | `agy --mode plan` |
| `--output-format <fmt>`| | Set output format (`text`, `json`, `stream-json`) | `agy -p "check" --output-format json` |
| `--add-dir <path>` | | Add an external directory to workspace scope | `agy --add-dir D:\Dev\SharedLib` |
| `--dangerously-skip-permissions` | | Auto-approve tool executions without prompting | Useful in automated CI scripts |
| `--sandbox` | | Enable restricted terminal sandbox mode | `agy --sandbox` |

---

## 5. Interactive Slash Commands (Inside `agy`)

When running inside an interactive `agy` session, the following slash commands control behavior:

- `/help`: Display all available interactive slash commands.
- `/logout`: Disconnect account and purge token from keyring.
- `/model`: View or switch active models dynamically (select `gemini-3.8-flash-high`).
- `/effort`: Change reasoning effort level (`low` to `max`).
- `/mode`: Toggle execution mode between `accept-edits`, `plan`, and `auto`.
- `/clear`: Clear terminal history and scrollback.
- `/compact`: Summarize and compact conversation context to free token window.
- `/plugin`: List, install, enable, or disable Antigravity plugins.
- `/quit` or `/exit`: Exit the CLI session (or press `Ctrl+D Ctrl+D`).

---

## 6. Subcommands

Execute subcommands directly from PowerShell or terminal:

```powershell
# List all models available to your account
agy models

# List available agent configurations
agy agents

# Manage plugins
agy plugin list

# Manage Model Context Protocol (MCP) servers
agy mcp list

# Update CLI to the latest upstream release
agy update
```

---

## 7. Troubleshooting & Common Issues

### A. Quota Limits (`RESOURCE_EXHAUSTED 429`)
If you receive:
```text
Error: Individual quota reached. Please upgrade your subscription to increase your limits. Resets in XXh.
```
- **Cause**: The current model (e.g. `gemini-4-argon`, `claude-sonnet-5-5`, `gpt-oss-120b`) has hit its restrictive rate or token ceiling.
- **Immediate Fix**: Switch to `gemini-3.8-flash-high`:
  ```powershell
  agy -p "your prompt" --model gemini-3.8-flash-high
  ```
- **Account Switch**: If an account's entire tier is locked, purge `gemini:antigravity` via `cmdkey /delete:gemini:antigravity` and sign in with an account having active quota.

### B. Non-Interactive Scripts in CI
Always specify `--output-format json` or `--output-format stream-json` with `--dangerously-skip-permissions` and `--model gemini-3.8-flash-high` when calling `agy` from Python or PowerShell pipelines to avoid hanging on interactive prompts.
