"""Prompt components for modular prompt building."""

from .grounding import GROUNDING_COMPONENT, PROVENANCE_CONTEXT_TEMPLATE
from .critical import CRITICAL_THINKING_COMPONENT
from .comparative import COMPARATIVE_ANALYSIS_COMPONENT
from .creative import CREATIVE_GENERATION_COMPONENT
from .learning import LEARNING_ASSISTANT_COMPONENT

THINKING_COMPONENT = """
## 思考框架

在处理问题时，请遵循以下思考框架：

1. **问题分解**：将复杂问题分解为更小的子问题
2. **假设识别**：识别问题中的显性和隐性假设
3. **第一性原则**：回归基本原理进行推理
4. **验证检查**：验证你的推理是否合理
"""

CLARIFICATION_COMPONENT = """
## 澄清指南

当问题不明确时：
- 识别缺失的关键信息
- 提出具体、有针对性的问题
- 避免假设用户的意图
- 一次只问一个问题
"""

RESEARCH_COMPONENT = """
## 研究指南

进行信息搜索时：
- 使用精确的搜索关键词
- 验证信息来源的可靠性
- 交叉验证多个来源
- 注意信息的时效性
"""

CALCULATION_COMPONENT = """
## 计算指南

进行计算时：
- 明确列出所有已知条件
- 选择正确的公式或方法
- 逐步展示计算过程
- 验证结果的合理性
"""

__all__ = [
    "THINKING_COMPONENT",
    "CLARIFICATION_COMPONENT",
    "RESEARCH_COMPONENT",
    "CALCULATION_COMPONENT",
    "GROUNDING_COMPONENT",
    "PROVENANCE_CONTEXT_TEMPLATE",
    "CRITICAL_THINKING_COMPONENT",
    "COMPARATIVE_ANALYSIS_COMPONENT",
    "CREATIVE_GENERATION_COMPONENT",
    "LEARNING_ASSISTANT_COMPONENT",
]
