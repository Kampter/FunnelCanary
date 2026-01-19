"""Agent-level scenario tests.

Tests that simulate real user interaction scenarios.
"""

from unittest.mock import MagicMock, patch

import pytest


class MockMessage:
    """Mock OpenAI message object."""

    def __init__(self, content=None, tool_calls=None):
        self.role = "assistant"
        self.content = content
        self.tool_calls = tool_calls


class MockToolCall:
    """Mock OpenAI tool call object."""

    def __init__(self, id, name, arguments):
        self.id = id
        self.function = MagicMock()
        self.function.name = name
        self.function.arguments = arguments


class MockChoice:
    """Mock OpenAI choice object."""

    def __init__(self, message, finish_reason="stop"):
        self.message = message
        self.finish_reason = finish_reason


class MockResponse:
    """Mock OpenAI response object."""

    def __init__(self, choices):
        self.choices = choices


def create_mock_response(content=None, tool_calls=None, finish_reason="stop"):
    """Helper to create mock OpenAI response."""
    message = MockMessage(content=content, tool_calls=tool_calls)
    choice = MockChoice(message, finish_reason=finish_reason)
    return MockResponse([choice])


# Scenario definitions based on the test plan
SCENARIOS = [
    {
        "name": "技术问题咨询",
        "description": "User asks a technical question",
        "input": "Python 的 GIL 是什么？",
        "success_criteria": [
            "包含 Global Interpreter Lock 的解释",
            "提到多线程限制",
        ],
    },
    {
        "name": "简单计算",
        "description": "User asks for a calculation",
        "input": "计算 123 * 456",
        "success_criteria": [
            "返回正确结果 56088",
        ],
    },
    {
        "name": "代码分析",
        "description": "User asks about code",
        "input": "什么是递归函数？",
        "success_criteria": [
            "解释自我调用",
            "提到基础情况",
        ],
    },
]


class TestScenarios:
    """Scenario-based tests."""

    @pytest.mark.agent
    def test_technical_question_scenario(self, mock_config):
        """Scenario: Technical question consultation."""
        with patch("funnel_canary.agent.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # Simulate response about GIL
            mock_response = create_mock_response(
                content="""Python 的 GIL (Global Interpreter Lock) 是 Python 解释器中的一个机制。

**什么是 GIL？**
GIL 是一个互斥锁，确保同一时刻只有一个线程在执行 Python 字节码。

**为什么需要 GIL？**
- 保护 CPython 内存管理的线程安全
- 简化 C 扩展的开发

**多线程限制**
由于 GIL 的存在，Python 的多线程在 CPU 密集型任务中无法实现真正的并行执行。
对于 I/O 密集型任务，多线程仍然有效。

**解决方案**
- 使用多进程 (multiprocessing)
- 使用 C 扩展释放 GIL
- 使用其他 Python 实现 (如 Jython)""",
                finish_reason="stop"
            )
            mock_client.chat.completions.create.return_value = mock_response

            from funnel_canary.agent import ProblemSolvingAgent

            agent = ProblemSolvingAgent(
                config=mock_config,
                max_iterations=5,
                enable_memory=False,
                enable_skills=False,
            )

            with patch("builtins.print"):
                result = agent.solve("Python 的 GIL 是什么？")

            # Verify success criteria
            assert "GIL" in result or "Global Interpreter Lock" in result
            assert "线程" in result or "thread" in result.lower()

    @pytest.mark.agent
    def test_calculation_scenario(self, mock_config):
        """Scenario: Calculation task."""
        with patch("funnel_canary.agent.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # First: python_exec tool call
            tool_call = MockToolCall(
                id="call_1",
                name="python_exec",
                arguments='{"code": "print(123 * 456)"}'
            )

            first_response = create_mock_response(
                content="让我计算一下...",
                tool_calls=[tool_call],
                finish_reason="tool_calls"
            )

            # Second: final answer
            second_response = create_mock_response(
                content="123 × 456 = 56088",
                finish_reason="stop"
            )

            mock_client.chat.completions.create.side_effect = [
                first_response,
                second_response
            ]

            from funnel_canary.agent import ProblemSolvingAgent

            agent = ProblemSolvingAgent(
                config=mock_config,
                max_iterations=5,
                enable_memory=False,
                enable_skills=False,
            )

            with patch("builtins.print"):
                result = agent.solve("计算 123 * 456")

            # Should contain the correct result
            assert "56088" in result

    @pytest.mark.agent
    def test_code_explanation_scenario(self, mock_config):
        """Scenario: Code explanation request."""
        with patch("funnel_canary.agent.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            mock_response = create_mock_response(
                content="""递归函数是一种在函数体内调用自身的编程技术。

**递归的基本要素：**

1. **基础情况 (Base Case)**
   - 递归终止的条件
   - 没有基础情况会导致无限递归

2. **递归情况 (Recursive Case)**
   - 函数调用自身，但参数向基础情况靠近

**示例 - 计算阶乘：**
```python
def factorial(n):
    if n <= 1:  # 基础情况
        return 1
    return n * factorial(n - 1)  # 递归情况
```

**注意事项：**
- 确保有明确的终止条件
- 注意栈溢出风险
- 考虑尾递归优化""",
                finish_reason="stop"
            )
            mock_client.chat.completions.create.return_value = mock_response

            from funnel_canary.agent import ProblemSolvingAgent

            agent = ProblemSolvingAgent(
                config=mock_config,
                max_iterations=5,
                enable_memory=False,
                enable_skills=False,
            )

            with patch("builtins.print"):
                result = agent.solve("什么是递归函数？")

            # Verify success criteria
            assert "递归" in result
            assert "基础" in result or "base" in result.lower()


class TestScenarioEdgeCases:
    """Edge case scenarios."""

    @pytest.mark.agent
    def test_ambiguous_question_scenario(self, mock_config):
        """Scenario: Ambiguous question that may need clarification."""
        with patch("funnel_canary.agent.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # Agent might ask for clarification using ask_user
            tool_call = MockToolCall(
                id="call_1",
                name="ask_user",
                arguments='{"question": "您想了解哪方面的信息？"}'
            )

            first_response = create_mock_response(
                content="这个问题比较模糊，让我请求澄清...",
                tool_calls=[tool_call],
                finish_reason="tool_calls"
            )

            # After getting clarification
            second_response = create_mock_response(
                content="根据您的回答，这里是相关信息...",
                finish_reason="stop"
            )

            mock_client.chat.completions.create.side_effect = [
                first_response,
                second_response
            ]

            from funnel_canary.agent import ProblemSolvingAgent

            agent = ProblemSolvingAgent(
                config=mock_config,
                max_iterations=5,
                enable_memory=False,
                enable_skills=False,
            )

            with patch("builtins.print"):
                with patch("builtins.input", return_value="具体信息"):
                    result = agent.solve("帮我做点什么")

            # Agent should still produce a result
            assert result is not None

    @pytest.mark.agent
    def test_multi_step_task_scenario(self, mock_config):
        """Scenario: Multi-step task requiring multiple tools."""
        with patch("funnel_canary.agent.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # Step 1: Calculate first part
            tool_call_1 = MockToolCall(
                id="call_1",
                name="python_exec",
                arguments='{"code": "result1 = 10 * 10\\nprint(result1)"}'
            )

            # Step 2: Calculate second part
            tool_call_2 = MockToolCall(
                id="call_2",
                name="python_exec",
                arguments='{"code": "result2 = 20 * 20\\nprint(result2)"}'
            )

            first_response = create_mock_response(
                content="开始第一步计算...",
                tool_calls=[tool_call_1],
                finish_reason="tool_calls"
            )

            second_response = create_mock_response(
                content="继续第二步计算...",
                tool_calls=[tool_call_2],
                finish_reason="tool_calls"
            )

            third_response = create_mock_response(
                content="计算完成！\n- 10² = 100\n- 20² = 400\n总和 = 500",
                finish_reason="stop"
            )

            mock_client.chat.completions.create.side_effect = [
                first_response,
                second_response,
                third_response
            ]

            from funnel_canary.agent import ProblemSolvingAgent

            agent = ProblemSolvingAgent(
                config=mock_config,
                max_iterations=10,
                enable_memory=False,
                enable_skills=False,
            )

            with patch("builtins.print"):
                result = agent.solve("计算 10 的平方和 20 的平方，然后求和")

            # Should complete with multiple steps
            assert mock_client.chat.completions.create.call_count == 3
            assert "100" in result or "400" in result or "500" in result
