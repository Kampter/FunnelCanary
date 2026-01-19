# FunnelCanary v0.0.7 测试计划

## 概述

本文档描述 FunnelCanary v0.0.7 的测试策略和测试计划。

## 测试目标

1. **验证工具边界行为** - 确保每个工具在各种边界条件下正确工作
2. **验证系统集成** - 确保各组件正确协作
3. **验证 Agent 行为** - 确保 Agent 能完成实际任务

## 测试层次

### 层次 1: 单元测试 (Unit Tests)

**目的**: 测试单个组件的边界行为

**范围**:
- 工具函数 (Read, Glob, Bash, python_exec, web_search, read_url, ask_user)
- 工具参数验证
- 错误处理

**标记**: `@pytest.mark.unit`

### 层次 2: 集成测试 (Integration Tests)

**目的**: 测试组件间的交互

**范围**:
- Provenance + Cognitive 系统
- Tool + Provenance 追踪
- 错误恢复机制

**标记**: `@pytest.mark.integration`

### 层次 3: Agent 测试 (Agent Tests)

**目的**: 测试端到端场景

**范围**:
- 任务完成度
- 工具调用正确性
- 场景测试
- 降级机制

**标记**: `@pytest.mark.agent`

## 测试优先级

| 优先级 | 测试类型 | 原因 |
|--------|---------|------|
| P0 | 工具边界测试 | 基础功能保障 |
| P0 | 任务完成度测试 | 核心价值验证 |
| P1 | 工具调用正确性 | 中间过程验证 |
| P1 | 多轮对话测试 | 真实使用场景 |
| P2 | 降级机制测试 | 反幻觉系统验证 |
| P2 | 效率评估 | 成本控制 |

## 覆盖率目标

- **总体覆盖率**: ≥ 80%
- **工具代码覆盖率**: ≥ 90%
- **核心逻辑覆盖率**: ≥ 85%

## 运行测试

```bash
# 安装测试依赖
uv sync --dev

# 运行所有测试
uv run pytest

# 运行特定层次
uv run pytest -m unit
uv run pytest -m integration
uv run pytest -m agent

# 运行带覆盖率
uv run pytest --cov=src/funnel_canary --cov-report=html

# 运行特定工具测试
uv run pytest tests/unit/tools/test_read.py -v
```

## CI/CD 集成

建议在以下阶段运行测试:

1. **PR 阶段**: 运行单元测试和集成测试
2. **合并前**: 运行完整测试套件
3. **发布前**: 运行完整测试 + 覆盖率检查

## 测试维护

- 新功能必须包含对应测试
- 修复 Bug 时添加回归测试
- 定期审查测试覆盖率
