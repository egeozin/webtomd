# Contributing to webtomd

Thanks for your interest in contributing! This project uses uv for all dev workflows and aims to stay self‑contained.

## Development Setup

- Install Python 3.9+ and uv
- Clone the repo, then:
  - `uv sync`
  - Run CLI help: `uv run webtomd --help`
  - Run tests: `uv run pytest`

Optional extras:
- Browser fetch: `uv sync --extra browser && uv run playwright install --with-deps chromium`
- LLM eval: copy `.env.example` to `.env` and set `OPENAI_API_KEY`

## Pull Requests

- Keep changes focused and minimal; follow existing style and structure
- Add/update tests when changing behavior
- Update README/docs if CLI flags or behavior change
- Ensure `uv run pytest` passes locally

## Commit and Branching

- Use clear commit messages; conventional commits appreciated
- Open PRs against the default branch (main)

## Code Style

- Python: standard formatting is fine; no enforced linter/formatter at this time
- Keep functions small and readable; follow existing module boundaries

## Running the Demo

- `uv run python scripts/demo_webtomd.py --url https://example.com/`

## Reporting Issues

- Use the issue template on the repository
- Include steps to reproduce, expected vs actual behavior, and environment details

Thanks again for helping improve webtomd!

