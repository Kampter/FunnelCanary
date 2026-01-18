"""Provenance system for FunnelCanary anti-hallucination.

Implements the four axioms:
- Axiom A: Correctness comes from "world state"
- Axiom B: World state only enters through "authoritative observations"
- Axiom C: From observation to conclusion must be "auditable"
- Axiom D: Any unverifiable part must be explicitly degraded

Provides:
- Observation: Authoritative observation from trusted sources
- Claim: Derived statement with provenance chain
- TransformStep: Single step in reasoning chain
- ProvenanceRegistry: Central registry for observations and claims
- ObservationType: Types of authoritative observations
- ClaimType: Types of claims based on evidence strength
- DegradationLevel: Degradation levels for outputs
- ClaimExtractor: Extract claims from LLM outputs
- GroundedAnswerGenerator: Generate grounded answers with degradation
- GroundedAnswer: Answer with full provenance tracking
"""

from .extractor import ClaimExtractor, ExtractedClaim
from .generator import GroundedAnswer, GroundedAnswerGenerator
from .models import (
    Claim,
    ClaimType,
    DegradationLevel,
    Observation,
    ObservationType,
    ProvenanceRegistry,
    TransformStep,
)

__all__ = [
    # Core models
    "Observation",
    "ObservationType",
    "Claim",
    "ClaimType",
    "TransformStep",
    "ProvenanceRegistry",
    "DegradationLevel",
    # Extractor
    "ClaimExtractor",
    "ExtractedClaim",
    # Generator
    "GroundedAnswerGenerator",
    "GroundedAnswer",
]
