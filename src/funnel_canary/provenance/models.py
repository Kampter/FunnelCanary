"""Core data models for the provenance system.

Implements the four axioms of the anti-hallucination system:
- Axiom A: Correctness comes from "world state"
- Axiom B: World state only enters through "authoritative observations"
- Axiom C: From observation to conclusion must be "auditable"
- Axiom D: Any unverifiable part must be explicitly degraded
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any
import uuid


class ObservationType(Enum):
    """Types of authoritative observations (Axiom B)."""

    TOOL_RETURN = auto()    # Tool/API returns - confidence 100%
    USER_INPUT = auto()     # User statements - confidence 80%
    DEFINED_RULE = auto()   # System rules - formally verifiable


class ClaimType(Enum):
    """Types of claims based on evidence strength."""

    FACT = "fact"              # Directly supported by observation
    INFERENCE = "inference"    # Derived through reasoning
    HYPOTHESIS = "hypothesis"  # Speculative, low evidence


class DegradationLevel(Enum):
    """Degradation levels for outputs (Axiom D implementation)."""

    FULL_ANSWER = auto()           # High confidence, complete answer
    PARTIAL_WITH_UNCERTAINTY = auto()  # Medium confidence, with uncertainty note
    REQUEST_MORE_INFO = auto()     # Low confidence, request more observations
    REFUSE = auto()                # Insufficient info, refuse to answer


@dataclass
class TransformStep:
    """A single step in the reasoning chain (Axiom C implementation).

    Records how information transforms from observations to conclusions.
    """

    operation: str           # "extract" | "aggregate" | "infer" | "combine"
    description: str         # Human-readable description
    input_ids: list[str] = field(default_factory=list)  # Input observation/claim IDs
    confidence_delta: float = 0.0  # Confidence change (-1.0 to 1.0)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "operation": self.operation,
            "description": self.description,
            "input_ids": self.input_ids,
            "confidence_delta": self.confidence_delta,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TransformStep":
        """Create from dictionary."""
        return cls(
            operation=data["operation"],
            description=data["description"],
            input_ids=data.get("input_ids", []),
            confidence_delta=data.get("confidence_delta", 0.0),
        )


@dataclass
class Observation:
    """An authoritative observation from the world (Axiom A & B implementation).

    Represents a piece of information that has been observed from a trusted source.
    All facts must ultimately trace back to observations.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    content: str = ""                           # Observation content
    source_type: ObservationType = ObservationType.TOOL_RETURN
    source_id: str = ""                         # Tool name / user ID / rule ID
    timestamp: datetime = field(default_factory=datetime.now)
    confidence: float = 1.0                     # Confidence [0.0, 1.0]
    scope: str = ""                             # Applicable scope
    ttl_seconds: int | None = None              # Time-to-live (None = never expires)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Set default confidence based on source type."""
        if self.confidence == 1.0 and self.source_type == ObservationType.USER_INPUT:
            self.confidence = 0.8

    def is_expired(self, current_time: datetime | None = None) -> bool:
        """Check if observation has expired based on TTL."""
        if self.ttl_seconds is None:
            return False

        current_time = current_time or datetime.now()
        age_seconds = (current_time - self.timestamp).total_seconds()
        return age_seconds > self.ttl_seconds

    def remaining_ttl(self, current_time: datetime | None = None) -> int | None:
        """Get remaining TTL in seconds, or None if never expires."""
        if self.ttl_seconds is None:
            return None

        current_time = current_time or datetime.now()
        age_seconds = (current_time - self.timestamp).total_seconds()
        remaining = self.ttl_seconds - int(age_seconds)
        return max(0, remaining)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "content": self.content,
            "source_type": self.source_type.name,
            "source_id": self.source_id,
            "timestamp": self.timestamp.isoformat(),
            "confidence": self.confidence,
            "scope": self.scope,
            "ttl_seconds": self.ttl_seconds,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Observation":
        """Create from dictionary."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        else:
            timestamp = datetime.now()

        source_type_str = data.get("source_type", "TOOL_RETURN")
        source_type = ObservationType[source_type_str]

        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            content=data.get("content", ""),
            source_type=source_type,
            source_id=data.get("source_id", ""),
            timestamp=timestamp,
            confidence=data.get("confidence", 1.0),
            scope=data.get("scope", ""),
            ttl_seconds=data.get("ttl_seconds"),
            metadata=data.get("metadata", {}),
        )

    def to_context(self) -> str:
        """Generate context string for prompt injection."""
        source_label = {
            ObservationType.TOOL_RETURN: "工具返回",
            ObservationType.USER_INPUT: "用户输入",
            ObservationType.DEFINED_RULE: "系统规则",
        }.get(self.source_type, "未知来源")

        lines = [f"[{self.id}] 来源: {source_label} ({self.source_id})"]
        lines.append(f"    内容: {self.content[:200]}...")
        lines.append(f"    置信度: {self.confidence:.0%}")

        if self.ttl_seconds:
            remaining = self.remaining_ttl()
            if remaining is not None:
                lines.append(f"    剩余有效期: {remaining}秒")

        return "\n".join(lines)


@dataclass
class Claim:
    """A claim derived from observations (Axiom C implementation).

    Represents a statement that has been derived from one or more observations
    through a chain of transformations.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    statement: str = ""                         # The claim content
    claim_type: ClaimType = ClaimType.FACT
    source_observations: list[str] = field(default_factory=list)  # Observation IDs
    transform_chain: list[TransformStep] = field(default_factory=list)
    confidence: float = 1.0                     # Computed confidence
    scope: str = ""                             # Applicable scope
    created_at: datetime = field(default_factory=datetime.now)

    def compute_confidence(self, observations: dict[str, "Observation"]) -> float:
        """Compute confidence based on source observations and transforms.

        Confidence is calculated as:
        1. Start with minimum confidence of source observations
        2. Apply confidence deltas from transform chain
        3. Clamp to [0.0, 1.0]
        """
        if not self.source_observations:
            return 0.0

        # Get minimum confidence from source observations
        obs_confidences = []
        for obs_id in self.source_observations:
            if obs_id in observations:
                obs = observations[obs_id]
                if not obs.is_expired():
                    obs_confidences.append(obs.confidence)

        if not obs_confidences:
            return 0.0

        # Start with minimum (conservative)
        base_confidence = min(obs_confidences)

        # Apply transform deltas
        for step in self.transform_chain:
            base_confidence += step.confidence_delta

        # Clamp to valid range
        return max(0.0, min(1.0, base_confidence))

    def update_confidence(self, observations: dict[str, "Observation"]) -> None:
        """Update the confidence based on current observations."""
        self.confidence = self.compute_confidence(observations)

    def get_audit_trail(self) -> str:
        """Generate human-readable audit trail (Axiom C)."""
        lines = [f"声明: {self.statement}"]
        lines.append(f"类型: {self.claim_type.value}")
        lines.append(f"置信度: {self.confidence:.0%}")
        lines.append("来源观测:")
        for obs_id in self.source_observations:
            lines.append(f"  - {obs_id}")

        if self.transform_chain:
            lines.append("推导链:")
            for i, step in enumerate(self.transform_chain, 1):
                lines.append(f"  {i}. [{step.operation}] {step.description}")
                if step.input_ids:
                    lines.append(f"     输入: {', '.join(step.input_ids)}")
                lines.append(f"     置信度变化: {step.confidence_delta:+.2f}")

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "statement": self.statement,
            "claim_type": self.claim_type.value,
            "source_observations": self.source_observations,
            "transform_chain": [t.to_dict() for t in self.transform_chain],
            "confidence": self.confidence,
            "scope": self.scope,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Claim":
        """Create from dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        else:
            created_at = datetime.now()

        claim_type_str = data.get("claim_type", "fact")
        claim_type = ClaimType(claim_type_str)

        transform_chain = [
            TransformStep.from_dict(t) for t in data.get("transform_chain", [])
        ]

        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            statement=data.get("statement", ""),
            claim_type=claim_type,
            source_observations=data.get("source_observations", []),
            transform_chain=transform_chain,
            confidence=data.get("confidence", 1.0),
            scope=data.get("scope", ""),
            created_at=created_at,
        )


class ProvenanceRegistry:
    """Registry for observations and claims (central provenance tracking).

    Manages the complete provenance chain from observations to claims,
    implementing Axioms A, B, C, and D.
    """

    def __init__(self) -> None:
        self.observations: dict[str, Observation] = {}
        self.claims: dict[str, Claim] = {}

    def add_observation(self, observation: Observation) -> str:
        """Add an observation to the registry.

        Returns:
            The observation ID.
        """
        self.observations[observation.id] = observation
        return observation.id

    def add_claim(self, claim: Claim) -> str:
        """Add a claim to the registry.

        Automatically updates the claim's confidence based on observations.

        Returns:
            The claim ID.
        """
        claim.update_confidence(self.observations)
        self.claims[claim.id] = claim
        return claim.id

    def get_observation(self, obs_id: str) -> Observation | None:
        """Get an observation by ID."""
        return self.observations.get(obs_id)

    def get_claim(self, claim_id: str) -> Claim | None:
        """Get a claim by ID."""
        return self.claims.get(claim_id)

    def get_valid_observations(
        self,
        min_confidence: float = 0.0,
        current_time: datetime | None = None
    ) -> list[Observation]:
        """Get all valid (non-expired) observations above confidence threshold."""
        current_time = current_time or datetime.now()
        return [
            obs for obs in self.observations.values()
            if not obs.is_expired(current_time) and obs.confidence >= min_confidence
        ]

    def get_valid_claims(
        self,
        min_confidence: float = 0.0,
        claim_type: ClaimType | None = None
    ) -> list[Claim]:
        """Get all claims above confidence threshold, optionally filtered by type."""
        claims = []
        for claim in self.claims.values():
            # Refresh confidence before filtering
            claim.update_confidence(self.observations)

            if claim.confidence >= min_confidence:
                if claim_type is None or claim.claim_type == claim_type:
                    claims.append(claim)

        return claims

    def invalidate_expired(self) -> list[str]:
        """Mark expired observations and return their IDs.

        Note: Does not delete, just identifies expired items for reference.
        """
        current_time = datetime.now()
        expired_ids = [
            obs_id for obs_id, obs in self.observations.items()
            if obs.is_expired(current_time)
        ]
        return expired_ids

    def get_observation_count(self) -> int:
        """Get total number of observations."""
        return len(self.observations)

    def get_claim_count(self) -> int:
        """Get total number of claims."""
        return len(self.claims)

    def get_observations_by_source(self, source_id: str) -> list[Observation]:
        """Get all observations from a specific source."""
        return [
            obs for obs in self.observations.values()
            if obs.source_id == source_id
        ]

    def get_observations_by_type(
        self,
        source_type: ObservationType
    ) -> list[Observation]:
        """Get all observations of a specific type."""
        return [
            obs for obs in self.observations.values()
            if obs.source_type == source_type
        ]

    def determine_degradation_level(
        self,
        required_observations: int = 1,
        min_confidence: float = 0.5
    ) -> DegradationLevel:
        """Determine appropriate degradation level (Axiom D implementation).

        Decision logic:
        - confidence >= 0.8 and sufficient observations → FULL_ANSWER
        - confidence >= 0.5 and some observations → PARTIAL_WITH_UNCERTAINTY
        - has observations but confidence < 0.5 → REQUEST_MORE_INFO
        - no valid observations → REFUSE
        """
        valid_obs = self.get_valid_observations(min_confidence=0.0)

        if not valid_obs:
            return DegradationLevel.REFUSE

        # Calculate average confidence of valid observations
        avg_confidence = sum(o.confidence for o in valid_obs) / len(valid_obs)
        obs_count = len(valid_obs)

        if avg_confidence >= 0.8 and obs_count >= required_observations:
            return DegradationLevel.FULL_ANSWER
        elif avg_confidence >= min_confidence and obs_count > 0:
            return DegradationLevel.PARTIAL_WITH_UNCERTAINTY
        elif obs_count > 0:
            return DegradationLevel.REQUEST_MORE_INFO
        else:
            return DegradationLevel.REFUSE

    def to_context(self, max_observations: int = 5) -> str:
        """Generate context string for prompt injection.

        Includes recent valid observations for the LLM to reference.
        """
        valid_obs = self.get_valid_observations()

        if not valid_obs:
            return "【无有效观测数据】"

        # Sort by timestamp (most recent first) and limit
        sorted_obs = sorted(
            valid_obs,
            key=lambda o: o.timestamp,
            reverse=True
        )[:max_observations]

        lines = ["【当前观测数据】"]
        for obs in sorted_obs:
            lines.append(obs.to_context())

        # Add summary
        expired_count = len(self.invalidate_expired())
        if expired_count > 0:
            lines.append(f"\n（已过期观测: {expired_count} 条）")

        return "\n".join(lines)

    def clear(self) -> None:
        """Clear all observations and claims."""
        self.observations.clear()
        self.claims.clear()

    def to_dict(self) -> dict[str, Any]:
        """Convert registry to dictionary for serialization."""
        return {
            "observations": {
                k: v.to_dict() for k, v in self.observations.items()
            },
            "claims": {
                k: v.to_dict() for k, v in self.claims.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProvenanceRegistry":
        """Create registry from dictionary."""
        registry = cls()

        for obs_data in data.get("observations", {}).values():
            obs = Observation.from_dict(obs_data)
            registry.observations[obs.id] = obs

        for claim_data in data.get("claims", {}).values():
            claim = Claim.from_dict(claim_data)
            registry.claims[claim.id] = claim

        return registry
