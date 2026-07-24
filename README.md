# Tuxo — Personal Telegram Assistant Installer

A guided wizard that stands up your **own, fully independent instance** of Tuxo:
a personal Telegram assistant that remembers what you tell it in an Obsidian
knowledge vault on GitHub, powered by Claude.

Everything the wizard creates lives in **your** accounts — your Telegram bot,
your GitHub vault repo, your AWS infrastructure, and your Anthropic API key.
Nothing is shared with any other installation.

## What it sets up

- **Telegram bot** — created via BotFather; the wizard validates the token and
  auto-discovers your chat ID.
- **GitHub vault** — a private repository that holds your Obsidian notes. The
  bot commits and pushes to it on every write.
- **AWS infrastructure** (Terraform) — ECS Fargate service, ECR image
  repository, Secrets Manager, a weekly vault health-check Lambda, and a monthly
  budget alert. State is kept in a per-account S3 bucket, so your setup is fully
  isolated.
- **Claude access** — a metered Anthropic Console API key (billed per credit),
  which the wizard validates before saving.

## How Tuxo works

```
Telegram ──(long-polling getUpdates)──▶ agent loop (Claude + tools) ──▶ reply
                                              │
                                              └─▶ Obsidian vault on GitHub (git commit + push)
```

- No webhook and no load balancer — the bot long-polls Telegram, which keeps
  the monthly AWS cost low.
- Messages are processed one at a time so vault git operations never race.
- The agent classifies each message (chat, store a note, answer from the vault,
  ingest a file) and acts using vault read/write/list tools.

## Prerequisites

Accounts:

- A Telegram account
- A GitHub account
- An AWS account
- An Anthropic Console API key from
  [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys)
  (pay-as-you-go credits — **not** the Claude Pro/Max subscription)

Command-line tools (the wizard checks these and links to installers if any are
missing):

- `git`
- `docker`
- `terraform` (>= 1.10)
- `aws`
- `gh`

## Usage

```bash
cd instalador
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"   # run from the repo root
python3 setup.py
```

The wizard is **resumable** — if you close the terminal partway through, just
run `python3 setup.py` again and it picks up where it left off.

To see what the wizard would do without touching any of your accounts:

```bash
python3 setup.py --dry-run
```

## Cost

Running Tuxo on AWS Fargate typically costs a few US dollars per month, plus
Anthropic API usage (billed per credit against your key). The wizard sets a
monthly AWS budget alert so you are notified before spending exceeds the limit
you choose.

## Development

```bash
.venv/bin/pytest        # run the test suite
.venv/bin/ruff check .  # lint
```

Each installer step under `instalador/steps/` is independent and testable via
dependency injection (subprocess, boto3 session, and HTTP client are all
injectable), so the tests never touch real services.

## Security & privacy

- Secrets you enter (Telegram token, GitHub token, Anthropic API key) are
  written only to local files (`.env.local`, `infra/terraform.tfvars`) and to
  your own AWS Secrets Manager. These files are gitignored and never committed.
- This installer template ships with placeholders only — fill in your own
  values locally.
