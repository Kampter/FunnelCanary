# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync

# Run the CLI
uv run python main.py "问题描述"
```

## Architecture (v0.0.6)

FunnelCanary is a CLI-based AI Agent that solves problems using first principles thinking with a closed-loop approach. v0.0.6 extends the tool system with Agent SDK compatible tools.

### Core Flow

```
main.py → ProblemSolvingAgent.solve() → Tool Calling Loop → Grounded Answer
```

### System Architecture

```
ProblemSolvingAgent
├── Provenance System (反幻觉系统) [v0.0.4]
│   ├── ProvenanceRegistry  # 观测与声明注册
│   ├── Observation         # 权威观测记录
│   ├── Claim              # 可审计声明
│   ├── ClaimExtractor     # 声明提取器
│   └── GroundedAnswerGenerator  # 有据答案生成
├── Cognitive System (策略决策)
│   ├── CognitiveState      # 认知状态追踪
│   ├── StrategyGate        # 策略门控 (含观测评估)
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
│   ├── ToolResult          # 带溯源的工具结果
│   └── Tools: web_search, read_url, ask_user, python_exec, Read, Glob, Bash
└── Prompt System (提示词系统)
    ├── PromptBuilder       # 模块化提示词构建
    ├── GroundingComponent  # 反幻觉提示组件
    └── GroundedFormat      # 有据输出格式
```

### Key Modules

| Module | Path | Description |
|--------|------|-------------|
| Agent | `src/funnel_canary/agent.py` | ProblemSolvingAgent - 核心循环 |
| Provenance | `src/funnel_canary/provenance/` | 反幻觉溯源系统 [v0.0.4] |
| Cognitive | `src/funnel_canary/cognitive/` | 认知状态与策略决策 |
| Context | `src/funnel_canary/context/` | 上下文窗口管理 |
| Memory | `src/funnel_canary/memory/` | 跨会话持久化记忆 |
| Skills | `src/funnel_canary/skills/` | 可扩展技能系统 |
| Tools | `src/funnel_canary/tools/` | 工具注册与执行 |
| Prompts | `src/funnel_canary/prompts/` | 模块化提示词 |
| Config | `src/funnel_canary/config.py` | 配置管理 |

### Human-Capability-Based Skills (v0.0.5)

Skills mapped from human cognitive abilities:

| Skill | Human Ability | Triggers | Tools |
|-------|--------------|----------|-------|
| `critical_thinking` | 批判性思维 | 验证、证据、可信、真假 | web_search, read_url |
| `comparative_analysis` | 对比分析 | 比较、对比、区别、优劣 | web_search, read_url |
| `deep_research` | 深度研究 | 深入、详细、全面、调研 | web_search, read_url, Read, Glob |
| `summarization` | 摘要总结 | 总结、概括、要点、摘要 | web_search, read_url |
| `learning_assistant` | 学习辅导 | 学习、教我、解释、入门 | web_search, ask_user |
| `decision_support` | 决策支持 | 决定、选择、建议、推荐 | web_search, ask_user |
| `creative_generation` | 创意生成 | 创意、想法、头脑风暴 | python_exec, ask_user |
| `code_analysis` | 代码分析 | 代码、分析、调试、解读 | python_exec, Read, Glob, Bash |
| `planning` | 规划执行 | 计划、规划、步骤、安排 | ask_user, Glob, Bash |
| `reflection` | 反思回顾 | 回顾、反思、总结经验 | ask_user |

### Anti-Hallucination System (v0.0.4)

Based on four axioms:
- **Axiom A**: Correctness comes from "world state" - facts must have observation support
- **Axiom B**: World state only enters through authoritative observations (tools/user/rules)
- **Axiom C**: From observation to conclusion must be auditable
- **Axiom D**: Any unverifiable part must be explicitly degraded

Key components:
```python
# Observation - records authoritative data
Observation(content, source_type, source_id, confidence, ttl_seconds)

# Claim - derived statement with provenance
Claim(statement, claim_type, source_observations, transform_chain)

# ProvenanceRegistry - central tracking
registry.add_observation(obs)
registry.determine_degradation_level()

# GroundedAnswerGenerator - degradation logic
generator.generate(raw_answer, registry) → GroundedAnswer
```

### Tools Available

| Tool | Category | TTL | Risk | Description |
|------|----------|-----|------|-------------|
| `web_search` | web | 1h | SAFE | 搜索互联网获取信息 |
| `read_url` | web | 2h | SAFE | 获取指定URL内容 |
| `ask_user` | interaction | - | SAFE | 向用户请求澄清信息 |
| `python_exec` | compute | - | SAFE | 运行Python代码（沙箱环境） |
| `Read` | filesystem | - | SAFE | 读取本地文件内容 |
| `Glob` | filesystem | - | SAFE | 按模式搜索文件 |
| `Bash` | compute | - | MEDIUM | 执行 Shell 命令 |

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
git tag -a v0.0.4 -m "Release v0.0.4: description"
git push origin v0.0.4
```

## Version History

### v0.0.6 (Current)
- Agent SDK 兼容工具扩展 (Agent SDK Compatible Tools)
  - `Read`: 读取本地文件内容
  - `Glob`: 按模式搜索文件（支持 **/*.py 等通配符）
  - `Bash`: 执行 Shell 命令（含安全黑名单）
- 新增 filesystem 工具分类
- 技能-工具映射增强
  - code_analysis: + Read, Glob, Bash
  - deep_research: + Read, Glob
  - planning: + Glob, Bash
- 工具设计遵循七大原则
  - 能力对齐、最小权限、可观测性
  - 接口清晰、结果流通、分类聚类、降级机制

### v0.0.5
- 基于人类能力的技能扩展 (Human-Capability-Based Skills)
  - critical_thinking: 批判性思维、事实核查
  - comparative_analysis: 系统性对比分析
  - deep_research: 深度研究与报告
  - summarization: 摘要总结
  - learning_assistant: 学习辅导
  - decision_support: 决策支持
  - creative_generation: 创意生成
  - code_analysis: 代码分析
  - planning: 规划执行
  - reflection: 反思回顾
- 提示词组件扩展 (Prompt Components)
  - CRITICAL_THINKING_COMPONENT
  - COMPARATIVE_ANALYSIS_COMPONENT
  - CREATIVE_GENERATION_COMPONENT
  - LEARNING_ASSISTANT_COMPONENT
- 技能映射增强 (Skill Mapping)
  - Agent 自动加载技能对应的 prompt 组件

### v0.0.4
- 反幻觉系统 (Anti-Hallucination)
  - 溯源系统 (Provenance System)
  - 观测追踪 (Observation Tracking)
  - 可审计声明 (Auditable Claims)
  - 降级机制 (Degradation Mechanism)
- 提示词增强 (Prompt Enhancement)
  - 事实来源原则 (Grounding Component)
  - 有据输出格式 (Grounded Output Format)
- 工具系统增强 (Tool System)
  - ToolResult 带溯源
  - TTL 配置支持
- 认知系统增强 (Cognitive Enhancement)
  - 观测状态追踪
  - 基于观测的策略决策

### v0.0.3
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
