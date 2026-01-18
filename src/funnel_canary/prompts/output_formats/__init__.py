"""Output format templates."""

from .grounded import (
    DEGRADED_FORMAT_PARTIAL,
    DEGRADED_FORMAT_REFUSE,
    GROUNDED_FORMAT,
    GROUNDED_FORMATS,
)

ANALYSIS_FORMAT = """
## 输出格式

【问题理解】
- 目标状态：{用户想要什么}
- 当前状态：{当前的认知/数据}
- 差距：{需要填补的信息/执行的操作}

【分析过程】
{你的推理步骤}

【答案】
{基于分析给出的答案}
"""

RESEARCH_FORMAT = """
## 输出格式

【搜索策略】
{搜索关键词和原因}

【发现的信息】
{从搜索中获得的关键信息}

【信息整合】
{如何整合多个来源的信息}

【答案】
{基于研究给出的答案}
"""

CALCULATION_FORMAT = """
## 输出格式

【问题分析】
- 已知条件：{列出所有已知信息}
- 求解目标：{需要计算什么}

【计算过程】
{逐步计算，每步说明}

【结果验证】
{验证结果的合理性}

【答案】
{最终计算结果}
"""

DECOMPOSITION_FORMAT = """
## 输出格式

【原始问题】
{用户的原始问题}

【识别的假设】
- 显性假设：{明确陈述的假设}
- 隐性假设：{潜在的未陈述假设}

【基本要素分解】
{将问题分解为基本组成部分}

【第一性原则分析】
{从基本原理出发的分析}

【答案】
{基于分析的结论}
"""

# Format registry
OUTPUT_FORMATS = {
    "default": ANALYSIS_FORMAT,
    "research": RESEARCH_FORMAT,
    "calculation": CALCULATION_FORMAT,
    "decomposition": DECOMPOSITION_FORMAT,
    "grounded": GROUNDED_FORMAT,
    "partial": DEGRADED_FORMAT_PARTIAL,
    "refuse": DEGRADED_FORMAT_REFUSE,
}

__all__ = [
    "ANALYSIS_FORMAT",
    "RESEARCH_FORMAT",
    "CALCULATION_FORMAT",
    "DECOMPOSITION_FORMAT",
    "GROUNDED_FORMAT",
    "DEGRADED_FORMAT_PARTIAL",
    "DEGRADED_FORMAT_REFUSE",
    "OUTPUT_FORMATS",
    "GROUNDED_FORMATS",
]
