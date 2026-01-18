# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync

# Run the CLI
uv run python main.py "问题描述"
```

## Architecture (v0.0.3)

FunnelCanary is a CLI-based AI Agent that solves problems using first principles thinking with a closed-loop approach.

### Core Flow

```
main.py → ProblemSolvingAgent.solve() → Tool Calling Loop → Structured Answer
```

### System Architecture

```
ProblemSolvingAgent
├── Cognitive System (策略决策)
│   ├── CognitiveState      # 认知状态追踪
│   ├── StrategyGate        # 策略门控
│   └── MinimalCommitmentPolicy  # 安全策略
├── Context Management (上下文管理)
│   ├── ContextManager      # 滑动窗口管理
│   └── Summarizer          # 消息摘要
├── Memory System (记忆系统)
│   ├── MemoryStore         # 持久化存储
│   ├── Fact                # 事实记录
│   └── SessionSummary      # 会话摘要
├── Skill System (技能系统)
│   ├── SkillRegistry       # 技能注册
│   └── SkillLoader         # 动态加载
├── Tool System (工具系统)
│   ├── ToolRegistry        # 工具注册
│   └── Tools: web_search, read_url, ask_user, python_exec
└── Prompt System (提示词系统)
    └── PromptBuilder       # 模块化提示词构建
```

### Key Modules

| Module | Path | Description |
|--------|------|-------------|
| Agent | `src/funnel_canary/agent.py` | ProblemSolvingAgent - 核心循环 |
| Cognitive | `src/funnel_canary/cognitive/` | 认知状态与策略决策 |
| Context | `src/funnel_canary/context/` | 上下文窗口管理 |
| Memory | `src/funnel_canary/memory/` | 跨会话持久化记忆 |
| Skills | `src/funnel_canary/skills/` | 可扩展技能系统 |
| Tools | `src/funnel_canary/tools/` | 工具注册与执行 |
| Prompts | `src/funnel_canary/prompts/` | 模块化提示词 |
| Config | `src/funnel_canary/config.py` | 配置管理 |

### Tools Available

| Tool | Function | Description |
|------|----------|-------------|
| `web_search` | 网络搜索 | 搜索互联网获取信息 |
| `read_url` | 读取网页 | 获取指定URL内容 |
| `ask_user` | 询问用户 | 向用户请求澄清信息 |
| `python_exec` | 执行代码 | 运行Python代码并返回结果 |

### Configuration (via `.env`)

```bash
OPENAI_API_KEY=your_api_key    # Required
OPENAI_BASE_URL=https://...    # Optional, default: OpenAI
MODEL_NAME=gpt-4               # Optional, default: gpt-4
```

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
git tag -a v0.0.3 -m "Release v0.0.3: description"
git push origin v0.0.3
```

## Version History

### v0.0.3 (Current)
- 稳定性测试通过 (20/20 测试用例)
- 完善错误处理机制
- 认知状态系统优化

### v0.0.2
- 架构优化：模块化重构
- 新增认知系统 (Cognitive System)
- 新增上下文管理 (Context Management)
- 新增持久化记忆 (Memory System)
- 新增技能系统 (Skill System)
- 工具系统重构 (Tool Registry)

### v0.0.1
- 初始版本：问题解构 Agent
- 基础工具调用循环
- 四个核心工具
