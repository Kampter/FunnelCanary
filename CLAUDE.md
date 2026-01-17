# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync

# Run the CLI
uv run python main.py "问题描述"
```

## Architecture

FunnelCanary is a CLI-based AI Agent that deconstructs problems using first principles thinking.

**Core flow**: `main.py` → `DeconstructionAgent.analyze()` → OpenAI API → Structured report

**Key modules**:
- `src/funnel_canary/agent.py`: `DeconstructionAgent` class - orchestrates LLM calls
- `src/funnel_canary/prompts.py`: System prompt and output format templates (Chinese)
- `src/funnel_canary/config.py`: `Config` dataclass loads from `.env` via `python-dotenv`

**Configuration** (via `.env`):
- `OPENAI_API_KEY` (required)
- `OPENAI_BASE_URL` (default: OpenAI)
- `MODEL_NAME` (default: gpt-4)

## Version Management

### Branch Strategy (GitHub Flow)

```
main (生产分支，始终可部署)
 └── feature/xxx (功能分支)
 └── fix/xxx (修复分支)
 └── docs/xxx (文档更新)
 └── refactor/xxx (重构)
```

### Semantic Versioning

```
v{MAJOR}.{MINOR}.{PATCH}

MAJOR: 不兼容的 API 变更
MINOR: 向后兼容的功能新增
PATCH: 向后兼容的 Bug 修复
```

### Commit Convention

```
<type>(<scope>): <description>

Types:
- feat: 新功能
- fix: Bug 修复
- docs: 文档变更
- refactor: 重构
- test: 测试
- chore: 构建/工具变更
```

Examples:
- `feat(agent): add tool calling loop`
- `feat(tools): implement web_search`
- `docs: update README`
- `fix(config): handle missing API key`

### Release Process

```bash
git tag -a v0.0.1 -m "Release v0.0.1: description"
git push origin v0.0.1
```
