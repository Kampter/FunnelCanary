# FunnelCanary

基于第一性原理思维的 AI Agent，帮助用户系统性解决问题。

## v0.0.3 功能

**ProblemSolvingAgent** - 使用闭环方法解决问题的智能代理

### 核心特性

- **工具调用循环** - 自动调用工具获取信息、执行操作
- **认知状态系统** - 追踪分析进度，智能决策下一步策略
- **上下文管理** - 滑动窗口管理对话历史，防止上下文溢出
- **持久化记忆** - 跨会话保存关键事实和摘要
- **技能系统** - 可扩展的技能注册与动态加载
- **错误恢复** - 优雅处理工具调用失败等异常情况

### 可用工具

| 工具 | 功能 |
|------|------|
| `web_search` | 搜索互联网获取最新信息 |
| `read_url` | 读取指定网页内容 |
| `ask_user` | 向用户请求澄清信息 |
| `python_exec` | 执行Python代码并返回结果 |

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

### 输出示例

```
【问题理解】
- 目标状态：...
- 当前状态：...
- 差距：...

【分析过程】
...

【执行】
→ web_search(query="...")
  结果: ...

【答案】
...
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
│   ├── prompts.py            # 提示词模板
│   ├── tools.py              # 工具实现
│   ├── cognitive/            # 认知状态系统
│   │   ├── state.py          # 认知状态
│   │   ├── strategy.py       # 策略决策
│   │   └── safety.py         # 安全策略
│   ├── context/              # 上下文管理
│   │   ├── manager.py        # 上下文管理器
│   │   └── summarizer.py     # 消息摘要
│   ├── memory/               # 持久化记忆
│   │   └── store.py          # 记忆存储
│   ├── skills/               # 技能系统
│   │   ├── registry.py       # 技能注册
│   │   └── loader.py         # 动态加载
│   ├── tools/                # 工具系统
│   │   ├── registry.py       # 工具注册
│   │   └── categories/       # 工具分类
│   └── prompts/              # 提示词模块
│       └── builder.py        # 提示词构建
└── tests/
    └── stability_test_report.md  # 稳定性测试报告
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

### v0.0.3 (Current)
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
