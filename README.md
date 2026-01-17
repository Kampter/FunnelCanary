# FunnelCanary

基于第一性原则思维的 AI Agent，帮助用户系统性解决问题。

## v0.01 功能

问题解构 Agent - 将问题分解为最基本的要素，识别并质疑所有假设。

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
uv run python main.py "火箭发射成本太高"
```

输出：

```
=== 问题解构报告 ===

【原始问题】火箭发射成本太高

【识别的假设】
1. 显性假设：火箭发射需要高成本
2. 隐性假设：必须购买现有供应商的部件
3. 隐性假设：火箭是一次性使用的

【基本要素分解】
- 原材料成本、制造成本、测试成本...

【对假设的质疑】
- "火箭一次性使用" → 可以回收复用吗？
...
```

## 项目结构

```
FunnelCanary/
├── .env.example            # 环境变量模板
├── pyproject.toml          # 项目配置
├── src/
│   └── funnel_canary/
│       ├── __init__.py
│       ├── agent.py        # DeconstructionAgent
│       ├── prompts.py      # 提示词模板
│       └── config.py       # 配置
└── main.py                 # CLI 入口
```
