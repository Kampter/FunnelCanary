"""Strategy gate for decision branching."""

from enum import Enum, auto
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from .state import CognitiveState

if TYPE_CHECKING:
    from ..provenance import ProvenanceRegistry


class StrategyDecision(Enum):
    """Possible strategy decisions at each iteration."""

    CONTINUE = auto()       # Continue current path
    DEEPEN = auto()         # Dig deeper into current approach
    PIVOT = auto()          # Switch method/skill
    ASK_USER = auto()       # Request user clarification
    DEGRADE = auto()        # Output with uncertainty acknowledgment
    CONCLUDE = auto()       # Output final answer
    REQUEST_MORE_INFO = auto()  # Need more observations (v0.0.4)


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
    2. Insufficient observations (v0.0.4) → REQUEST_MORE_INFO
    3. Stalled >= 3 iterations → PIVOT or DEGRADE
    4. Goal clarity uncertainty → ASK_USER
    5. Data sufficiency uncertainty → DEEPEN
    6. Too many uncertainties (>= 5) → DEGRADE
    7. Default → CONTINUE
    """

    def __init__(
        self,
        confidence_threshold: float = 0.7,
        stall_threshold: int = 3,
        uncertainty_limit: int = 5,
        min_observations_for_answer: int = 1,
    ):
        self.confidence_threshold = confidence_threshold
        self.stall_threshold = stall_threshold
        self.uncertainty_limit = uncertainty_limit
        self.min_observations_for_answer = min_observations_for_answer

    def evaluate(
        self,
        state: CognitiveState,
        provenance_registry: "ProvenanceRegistry | None" = None,
    ) -> StrategyPath:
        """
        Evaluate cognitive state and decide on strategy branch.

        Args:
            state: Current cognitive state
            provenance_registry: Optional provenance registry for observation-based decisions

        Returns:
            StrategyPath with decision and reasoning
        """
        # Rule 1: High confidence → CONCLUDE
        if state.confidence >= self.confidence_threshold and len(state.uncertainties) == 0:
            # Additional check: ensure we have observations if provenance is enabled
            if provenance_registry:
                valid_obs = provenance_registry.get_valid_observations(min_confidence=0.5)
                if len(valid_obs) < self.min_observations_for_answer:
                    return StrategyPath(
                        decision=StrategyDecision.REQUEST_MORE_INFO,
                        reason="置信度高但观测数据不足，需要收集更多信息",
                        suggested_action="调用工具获取更多观测数据",
                    )
            return StrategyPath(
                decision=StrategyDecision.CONCLUDE,
                reason=f"置信度达到 {state.confidence:.0%}，无关键不确定性",
            )

        # Rule 2 (v0.0.4): Check observation status from provenance
        if provenance_registry:
            obs_strategy = self._evaluate_observations(provenance_registry)
            if obs_strategy:
                return obs_strategy

        # Rule 3: Stalled → PIVOT or DEGRADE
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

        # Rule 4: Goal clarity issues → ASK_USER
        goal_uncertainties = [u for u in state.uncertainties if "目标" in u or "需求" in u]
        if goal_uncertainties:
            return StrategyPath(
                decision=StrategyDecision.ASK_USER,
                reason="存在目标理解不确定性",
                suggested_action=f"询问用户关于: {goal_uncertainties[0]}",
            )

        # Rule 5: Data sufficiency issues → DEEPEN
        data_uncertainties = [u for u in state.uncertainties if "数据" in u or "信息" in u]
        if data_uncertainties:
            return StrategyPath(
                decision=StrategyDecision.DEEPEN,
                reason="需要更多数据或信息",
                suggested_action="继续深入探索当前路径",
            )

        # Rule 6: Too many uncertainties → DEGRADE
        if len(state.uncertainties) >= self.uncertainty_limit:
            return StrategyPath(
                decision=StrategyDecision.DEGRADE,
                reason=f"不确定性过多 ({len(state.uncertainties)} 个)",
                suggested_action="输出部分答案并说明限制",
            )

        # Rule 7: Default → CONTINUE
        return StrategyPath(
            decision=StrategyDecision.CONTINUE,
            reason="继续当前策略",
        )

    def _evaluate_observations(
        self,
        registry: "ProvenanceRegistry",
    ) -> StrategyPath | None:
        """Evaluate observations from provenance registry.

        Args:
            registry: ProvenanceRegistry with current observations.

        Returns:
            StrategyPath if observation-based decision needed, None otherwise.
        """
        # Get valid observations
        valid_obs = registry.get_valid_observations()
        expired_ids = registry.invalidate_expired()

        # If we have expired observations and few valid ones, request refresh
        if expired_ids and len(valid_obs) < self.min_observations_for_answer:
            return StrategyPath(
                decision=StrategyDecision.REQUEST_MORE_INFO,
                reason=f"有 {len(expired_ids)} 条观测已过期，需要刷新信息",
                suggested_action="重新调用工具获取最新数据",
            )

        # Check average confidence of observations
        if valid_obs:
            avg_confidence = sum(o.confidence for o in valid_obs) / len(valid_obs)

            # If average confidence is low, we need more reliable observations
            if avg_confidence < 0.5 and len(valid_obs) < 3:
                return StrategyPath(
                    decision=StrategyDecision.REQUEST_MORE_INFO,
                    reason=f"观测数据平均置信度较低 ({avg_confidence:.0%})，建议获取更多数据",
                    suggested_action="调用更多工具交叉验证信息",
                )

        # No observation-based intervention needed
        return None
