"""Grounded output format template for anti-hallucination.

Provides structured output format that includes:
- Observation data with sources
- Reasoning process with provenance
- Confidence assessment
- Final answer with limitations
"""

GROUNDED_FORMAT = """
## 输出格式（有据回答）

【观测数据】
- 来源：{工具名称}
- 内容：{关键信息摘要}
- 时效：{信息时间范围}

【推理过程】
1. 基于 [观测ID]，可以确定...
2. 结合 [观测ID]，进一步推断...
3. （如有推断）由于没有直接观测，这是基于{依据}的推测

【置信度评估】
- ✅ 高置信度（有直接观测支持）：{列出}
- ⚠️ 中置信度（推测/常识）：{列出}
- ❓ 低置信度（无证据）：{列出}

【答案】
{最终答案}
- 事实部分：{有观测支持的内容}
- 推断部分：{逻辑推导的内容，标注"推断"}
- 不确定部分：{无法确定的内容，标注"未知"或"需要更多信息"}

【信息局限性】
- 时效性：{数据的时间范围和可能的过期风险}
- 范围限制：{信息覆盖的范围和未覆盖的方面}
- 置信度说明：{整体置信度评估}
"""

DEGRADED_FORMAT_PARTIAL = """
## 输出格式（部分信息）

【已知信息】
{已获取的观测数据}

【缺失信息】
{需要但未获取的信息}

【部分答案】
基于现有信息，我可以说明：
{可以回答的部分}

⚠️ **不确定说明**：
{以下部分无法确定}
- {列出不确定的方面}

【建议操作】
{获取更多信息的建议}
"""

DEGRADED_FORMAT_REFUSE = """
## 输出格式（无法回答）

【问题分析】
{对问题的理解}

【信息现状】
❌ 当前没有足够的观测数据来回答此问题

【缺失信息】
需要以下信息才能回答：
- {列出需要的信息1}
- {列出需要的信息2}

【建议】
- 可以尝试搜索：{建议的搜索查询}
- 或者您可以提供：{用户可以补充的信息}

【说明】
为避免提供不准确的信息，我选择不进行猜测。
"""

# Format registry
GROUNDED_FORMATS = {
    "grounded": GROUNDED_FORMAT,
    "partial": DEGRADED_FORMAT_PARTIAL,
    "refuse": DEGRADED_FORMAT_REFUSE,
}
