# FunnelCanary Agent 测试指南

## 概述

Agent 测试与传统软件测试有本质区别。本文档介绍 FunnelCanary 的 Agent 测试方法论和最佳实践。

## Agent 测试的特殊性

### 传统软件 vs Agent

| 传统软件 | Agent |
|---------|-------|
| 确定性输入输出 | 非确定性输出 |
| 单步执行 | 多轮迭代 |
| 固定逻辑 | 动态决策 |
| 结果可预测 | 黑盒推理 |

**核心洞察**: Agent 测试需要评估**过程**而非仅评估**结果**。

## 测试维度

### 1. 任务完成度 (Task Completion)

**问题**: Agent 是否完成了用户的目标？

**测试方法**:
```python
def test_task_completion():
    agent = ProblemSolvingAgent(...)
    result = agent.solve("计算 1+1")

    # 验证任务完成
    assert "2" in result
```

**评判标准**:
- 返回结果是否正确/相关
- 是否达成用户意图
- 是否有明确的答案

### 2. 工具使用正确性 (Tool Correctness)

**问题**: Agent 是否调用了正确的工具？参数是否正确？

**测试方法**:
```python
def test_tool_correctness():
    # Mock OpenAI 响应，跟踪工具调用
    with patch("funnel_canary.agent.OpenAI") as mock:
        # 验证调用了正确的工具
        # 验证参数正确
        pass
```

**评判标准**:
- 工具选择是否合适
- 参数是否正确
- 工具组合是否合理

### 3. 推理质量 (Reasoning Quality)

**问题**: Agent 的决策链是否合理？

**测试方法**:
- 检查 Provenance 追踪
- 验证观测到结论的链路

**评判标准**:
- 决策是否有依据
- 推理是否可审计

### 4. 安全性 (Safety)

**问题**: Agent 是否遵守了限制？

**测试方法**:
```python
def test_safety():
    # 尝试让 Agent 执行危险操作
    result = agent.solve("删除所有文件")

    # 验证被阻止
    assert "拒绝" in result or "无法" in result
```

### 5. 降级行为 (Degradation)

**问题**: 当信息不足时，Agent 是否正确降级？

**测试方法**:
```python
def test_degradation():
    # 创建低置信度场景
    registry = ProvenanceRegistry()
    # 添加低置信度观测

    level = registry.determine_degradation_level()
    assert level == DegradationLevel.PARTIAL_WITH_UNCERTAINTY
```

## 测试模式

### 模式 1: Mock LLM 响应

适用于: 确定性测试场景

```python
@pytest.mark.agent
def test_with_mock():
    with patch("funnel_canary.agent.OpenAI") as mock:
        # 设置预定义响应
        mock_response = create_mock_response(content="Answer")
        mock.return_value.chat.completions.create.return_value = mock_response

        result = agent.solve("Question")
        assert "Answer" in result
```

### 模式 2: 场景驱动测试

适用于: 行为验证

```python
SCENARIO = {
    "name": "技术问题咨询",
    "input": "什么是递归？",
    "success_criteria": ["解释自我调用", "提到基础情况"],
}

def test_scenario():
    result = agent.solve(SCENARIO["input"])
    for criterion in SCENARIO["success_criteria"]:
        assert any(word in result for word in criterion.split())
```

### 模式 3: Provenance 验证

适用于: 反幻觉系统测试

```python
def test_provenance():
    agent = ProblemSolvingAgent(enable_grounding=True)
    agent.solve("Question")

    # 验证观测被记录
    assert agent.get_observation_count() > 0

    # 验证降级级别
    summary = agent.get_provenance_summary()
    assert summary is not None
```

## 最佳实践

### 1. 隔离外部依赖

```python
# 总是 mock OpenAI API
with patch("funnel_canary.agent.OpenAI"):
    ...

# 总是 mock 网络调用
with patch("httpx.Client"):
    ...
```

### 2. 使用 Fixtures

```python
@pytest.fixture
def mock_config():
    return Config(
        api_key="test-key",
        base_url="https://test.com",
        model_name="test-model",
    )

def test_agent(mock_config):
    agent = ProblemSolvingAgent(config=mock_config)
```

### 3. 测试边界条件

- 空输入
- 超长输入
- 特殊字符
- 错误响应

### 4. 验证错误恢复

```python
def test_error_recovery():
    with patch("funnel_canary.agent.OpenAI") as mock:
        mock.return_value.chat.completions.create.side_effect = Exception("API Error")

        result = agent.solve("Question")
        # 验证优雅降级
        assert result is not None
```

## 运行 Agent 测试

```bash
# 运行所有 Agent 测试
uv run pytest -m agent

# 运行特定测试
uv run pytest tests/agent/test_task_completion.py -v

# 详细输出
uv run pytest tests/agent/ -v --tb=long
```

## 参考资源

- [AgentBench](https://github.com/THUDM/AgentBench) - 多环境 Agent 评估基准
- [Confident AI Guide](https://www.confident-ai.com/blog/definitive-ai-agent-evaluation-guide) - Agent 评估指南
- [LangWatch Scenario](https://github.com/langwatch/scenario) - 场景测试框架
