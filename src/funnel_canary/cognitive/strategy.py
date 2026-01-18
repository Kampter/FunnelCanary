"""Strategy gate for decision branching."""

from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional

from .state import CognitiveState


class StrategyDecision(Enum):
    """Possible strategy decisions at each iteration."""

    CONTINUE = auto()   # Continue current path
    DEEPEN = auto()     # Dig deeper into current approach
    PIVOT = auto()      # Switch method/skill
    ASK_USER = auto()   # Request user clarification
    DEGRADE = auto()    # Output with uncertainty acknowledgment
    CONCLUDE = auto()   # Output final answer


@dataclass
class StrategyPath:
    """Result of strategy evaluation."""

    decision: StrategyDecision
    reason: str
    suggested_action: Optional[str] = None


class StrategyGate:
    """
    Implements human-like strategy branching logic.

    Decision tree:
    1. High confidence + no critical uncertainties → CONCLUDE
    2. Stalled >= 3 iterations → PIVOT or DEGRADE
    3. Goal clarity uncertainty → ASK_USER
    4. Data sufficiency uncertainty → DEEPEN
    5. Too many uncertainties (>= 5) → DEGRADE
    6. Default → CONTINUE
    """

    def __init__(
        self,
        confidence_threshold: float = 0.7,
        stall_threshold: int = 3,
        uncertainty_limit: int = 5,
    ):
        self.confidence_threshold = confidence_threshold
        self.stall_threshold = stall_threshold
        self.uncertainty_limit = uncertainty_limit

    def evaluate(self, state: CognitiveState) -> StrategyPath:
        """
        Evaluate cognitive state and decide on strategy branch.

        Args:
            state: Current cognitive state

        Returns:
            StrategyPath with decision and reasoning
        """
        # Rule 1: High confidence → CONCLUDE
        if state.confidence >= self.confidence_threshold and len(state.uncertainties) == 0:
            return StrategyPath(
                decision=StrategyDecision.CONCLUDE,
                reason=f"置信度达到 {state.confidence:.0%}，无关键不确定性",
            )

        # Rule 2: Stalled → PIVOT or DEGRADE
        if state.has_stalled(self.stall_threshold):
            if state.confidence < 0.3:
                return StrategyPath(
                    decision=StrategyDecision.DEGRADE,
                    reason=f"停滞 {state.stall_count} 轮且置信度低，降级输出",
                    suggested_action="输出当前最佳答案并说明不确定性",
                )
            else:
                return StrategyPath(
                    decision=StrategyDecision.PIVOT,
                    reason=f"停滞 {state.stall_count} 轮，需要切换策略",
                    suggested_action="考虑切换技能或方法",
                )

        # Rule 3: Goal clarity issues → ASK_USER
        goal_uncertainties = [u for u in state.uncertainties if "目标" in u or "需求" in u]
        if goal_uncertainties:
            return StrategyPath(
                decision=StrategyDecision.ASK_USER,
                reason="存在目标理解不确定性",
                suggested_action=f"询问用户关于: {goal_uncertainties[0]}",
            )

        # Rule 4: Data sufficiency issues → DEEPEN
        data_uncertainties = [u for u in state.uncertainties if "数据" in u or "信息" in u]
        if data_uncertainties:
            return StrategyPath(
                decision=StrategyDecision.DEEPEN,
                reason="需要更多数据或信息",
                suggested_action="继续深入探索当前路径",
            )

        # Rule 5: Too many uncertainties → DEGRADE
        if len(state.uncertainties) >= self.uncertainty_limit:
            return StrategyPath(
                decision=StrategyDecision.DEGRADE,
                reason=f"不确定性过多 ({len(state.uncertainties)} 个)",
                suggested_action="输出部分答案并说明限制",
            )

        # Rule 6: Default → CONTINUE
        return StrategyPath(
            decision=StrategyDecision.CONTINUE,
            reason="继续当前策略",
        )
