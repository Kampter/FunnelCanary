# FunnelCanary

基于第一性原理思维的 AI Agent，帮助用户系统性解决问题。v0.0.6 扩展 Agent SDK 兼容工具，增强文件操作与系统执行能力。

## v0.0.6 核心特性

### Agent SDK 兼容工具

借鉴 Anthropic Agent SDK 工具设计，新增三个核心工具：

| 工具 | 分类 | 风险级别 | 说明 |
|------|------|----------|------|
| `Read` | filesystem | SAFE | 读取本地文件内容（最大 100KB） |
| `Glob` | filesystem | SAFE | 按模式搜索文件（支持 `**/*.py` 等通配符） |
| `Bash` | compute | MEDIUM | 执行 Shell 命令（含安全黑名单） |

### 工具设计七大原则

| 原则 | 说明 |
|------|------|
| **能力对齐** | 每个工具解决 LLM 的某个根本能力缺陷 |
| **最小权限** | 给予恰好必需的权限，不多不少 |
| **可观测性** | 每次调用产生可追踪的观测记录 |
| **接口清晰** | 从描述就能理解何时使用 |
| **结果流通** | 工具结果回流到决策循环 |
| **分类聚类** | 按功能、权限、调度需求分组 |
| **降级机制** | 不可靠结果必须显式标记并降级使用 |

### Bash 安全机制

危险命令黑名单保护：
- `rm -rf /`, `rm -rf ~` - 防止删除系统/用户目录
- `dd if=`, `mkfs` - 防止磁盘破坏
- `shutdown`, `reboot` - 防止系统关机
- Fork bomb 等恶意模式

## 反幻觉系统 (v0.0.4)

基于四条公理构建的反幻觉系统：

| 公理 | 原则 | 实现 |
|------|------|------|
| **A** | 正确性来自"世界状态" | 事实必须有观测支撑 |
| **B** | 世界状态只能通过权威观测进入 | 工具/用户/规则三类来源 |
| **C** | 从观测到结论必须可审计 | 完整的推导链追踪 |
| **D** | 不可验证部分必须显式降级 | 四级降级机制 |

### 降级机制

| 级别 | 条件 | 输出 |
|------|------|------|
| `FULL_ANSWER` | 高置信度 + 足够观测 | 完整回答 |
| `PARTIAL_WITH_UNCERTAINTY` | 中置信度 + 部分观测 | 带不确定性说明 |
| `REQUEST_MORE_INFO` | 低置信度 | 请求更多信息 |
| `REFUSE` | 无有效观测 | 拒绝回答 |

### 其他核心功能

- **工具调用循环** - 自动调用工具获取信息、执行操作
- **认知状态系统** - 追踪分析进度，智能决策下一步策略
- **上下文管理** - 滑动窗口管理对话历史，防止上下文溢出
- **持久化记忆** - 跨会话保存关键事实和摘要
- **技能系统** - 可扩展的技能注册与动态加载
- **错误恢复** - 优雅处理工具调用失败等异常情况

### 可用工具

| 工具 | 分类 | TTL | 风险 | 说明 |
|------|------|-----|------|------|
| `web_search` | web | 1h | SAFE | 搜索互联网获取最新信息 |
| `read_url` | web | 2h | SAFE | 读取指定网页内容 |
| `ask_user` | interaction | - | SAFE | 向用户请求澄清信息 |
| `python_exec` | compute | - | SAFE | 执行Python代码（沙箱环境） |
| `Read` | filesystem | - | SAFE | 读取本地文件内容 |
| `Glob` | filesystem | - | SAFE | 按模式搜索文件 |
| `Bash` | compute | - | MEDIUM | 执行 Shell 命令 |

## 安装

```bash
# 安装依赖
uv sync

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API_KEY 和 BASE_URL
```

## 使用

```bash
uv run python main.py "你的问题"
```

### 示例

```bash
# 简单问题
uv run python main.py "什么是递归"

# 需要搜索的问题
uv run python main.py "帮我调研最近的AI新闻"

# 需要分析网页
uv run python main.py "帮我分析这个网页 https://example.com"

# 复杂决策问题
uv run python main.py "我应该学React还是Vue"
```

### 输出示例 (v0.0.4 有据输出格式)

```
【观测数据】
- 来源：web_search
- 内容：关键搜索结果...
- 时效：1小时内有效

【推理过程】
1. 基于 [观测X]，可以确定...
2. 结合 [观测Y]，进一步推断...

【置信度评估】
- ✅ 高置信度：有直接观测支持的部分
- ⚠️ 推测/常识：无直接证据的部分
- ❓ 未找到信息：搜索失败的部分

【答案】
...最终答案，区分事实与推断...

【信息局限性】
- 时效性、范围限制等说明
```

## 系统架构

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

## 项目结构

```
FunnelCanary/
├── .env.example              # 环境变量模板
├── pyproject.toml            # 项目配置
├── main.py                   # CLI 入口
├── src/funnel_canary/
│   ├── __init__.py
│   ├── agent.py              # ProblemSolvingAgent 核心
│   ├── config.py             # 配置管理
│   ├── cognitive/            # 认知状态系统
│   │   ├── state.py          # 认知状态 (含观测追踪)
│   │   ├── strategy.py       # 策略决策 (含观测评估)
│   │   └── safety.py         # 安全策略
│   ├── context/              # 上下文管理
│   │   ├── manager.py        # 上下文管理器
│   │   └── summarizer.py     # 消息摘要
│   ├── memory/               # 持久化记忆
│   │   └── store.py          # 记忆存储
│   ├── provenance/           # 反幻觉溯源系统 [v0.0.4]
│   │   ├── __init__.py       # 模块导出
│   │   ├── models.py         # Observation, Claim, ProvenanceRegistry
│   │   ├── extractor.py      # 声明提取器
│   │   └── generator.py      # 有据答案生成器
│   ├── skills/               # 技能系统
│   │   ├── registry.py       # 技能注册
│   │   └── loader.py         # 动态加载
│   ├── tools/                # 工具系统
│   │   ├── base.py           # Tool, ToolResult 基类
│   │   ├── registry.py       # 工具注册
│   │   └── categories/       # 工具分类
│   │       ├── web.py        # web_search, read_url
│   │       ├── compute.py    # python_exec, Bash
│   │       ├── interaction.py # ask_user
│   │       └── filesystem.py # Read, Glob [v0.0.6]
│   └── prompts/              # 提示词模块
│       ├── builder.py        # 提示词构建
│       ├── components/       # 提示词组件
│       │   └── grounding.py  # 反幻觉组件 [v0.0.4]
│       └── output_formats/   # 输出格式
│           └── grounded.py   # 有据输出格式 [v0.0.4]
└── tests/
    └── stability_test_report.md  # 稳定性测试报告
```

## 配置

通过 `.env` 文件配置：

```bash
OPENAI_API_KEY=your_api_key    # Required - API密钥
OPENAI_BASE_URL=https://...    # Optional - 自定义API地址
MODEL_NAME=gpt-4               # Optional - 模型名称
```

## 稳定性测试

v0.0.3 通过了完整的稳定性测试：

| 测试类别 | 通过/总数 |
|---------|----------|
| 基础功能测试 | 5/5 |
| 边界条件测试 | 5/5 |
| 错误处理测试 | 5/5 |
| 真实场景测试 | 5/5 |
| **总计** | **20/20** |

详见 `tests/stability_test_report.md`

## 版本历史

### v0.0.6 (Current)
- **Agent SDK 兼容工具** (Agent SDK Compatible Tools)
  - `Read`: 读取本地文件内容（最大 100KB）
  - `Glob`: 按模式搜索文件（支持 `**/*.py` 等通配符）
  - `Bash`: 执行 Shell 命令（含安全黑名单保护）
- **新增 filesystem 工具分类**
- **技能-工具映射增强**
  - code_analysis: + Read, Glob, Bash
  - deep_research: + Read, Glob
  - planning: + Glob, Bash
- **工具设计遵循七大原则**

### v0.0.5
- **基于人类能力的技能扩展** (Human-Capability-Based Skills)
  - critical_thinking, comparative_analysis, deep_research
  - summarization, learning_assistant, decision_support
  - creative_generation, code_analysis, planning, reflection
- **提示词组件扩展** (Prompt Components)
- **技能映射增强** (Skill Mapping)

### v0.0.4
- **反幻觉系统** (Anti-Hallucination)
  - 溯源系统 (Provenance System)
  - 观测追踪 (Observation Tracking with TTL)
  - 可审计声明 (Auditable Claims)
  - 四级降级机制 (Degradation Levels)
- **提示词增强** (Prompt Enhancement)
  - 事实来源原则 (Grounding Component)
  - 有据输出格式 (Grounded Output Format)
- **工具系统增强** (Tool System)
  - ToolResult 带溯源信息
  - TTL 过期配置支持
- **认知系统增强** (Cognitive Enhancement)
  - 观测状态追踪
  - 基于观测的策略决策

### v0.0.3
- 稳定性测试通过 (20/20)
- 完善错误处理机制
- 认知状态系统优化

### v0.0.2
- 架构优化：模块化重构
- 新增认知系统、上下文管理、持久化记忆、技能系统
- 工具系统重构

### v0.0.1
- 初始版本：问题解构 Agent
- 基础工具调用循环
- 四个核心工具

## License

MIT
