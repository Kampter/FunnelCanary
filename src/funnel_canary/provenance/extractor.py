"""Claim extractor for parsing LLM outputs.

Extracts structured claims from LLM-generated text responses,
allowing for provenance tracking and validation.
"""

import re
from dataclasses import dataclass, field

from .models import Claim, ClaimType, Observation, TransformStep


@dataclass
class ExtractedClaim:
    """A claim extracted from LLM output with metadata."""

    statement: str
    claim_type: ClaimType
    observation_refs: list[str] = field(default_factory=list)  # Referenced observation IDs
    reasoning: str = ""
    confidence_hint: str = ""  # "high", "medium", "low"


class ClaimExtractor:
    """Extracts claims from LLM-generated text.

    Parses structured output to identify:
    - Factual claims with observation references
    - Inferences with reasoning chains
    - Hypotheses and speculations
    """

    # Patterns for identifying claim types
    FACT_PATTERNS = [
        r"根据.*?[,，]",          # "According to..."
        r"搜索结果显示",            # "Search results show..."
        r"\[观测\w+\]",           # "[Observation ID]"
        r"数据表明",               # "Data indicates..."
        r"结果显示",               # "Results show..."
    ]

    INFERENCE_PATTERNS = [
        r"我推断",                 # "I infer..."
        r"由此可见",               # "From this we can see..."
        r"基于.*?推测",            # "Based on... I speculate..."
        r"因此",                  # "Therefore..."
        r"可以得出",               # "We can conclude..."
    ]

    HYPOTHESIS_PATTERNS = [
        r"如果.*?那么",            # "If... then..."
        r"假设",                  # "Assuming..."
        r"可能",                  # "Possibly..."
        r"或许",                  # "Perhaps..."
        r"推测",                  # "Speculation..."
    ]

    OBSERVATION_REF_PATTERN = r"\[(\w{8})\]"  # Match [8-char-id]

    def __init__(self) -> None:
        self._fact_re = re.compile("|".join(self.FACT_PATTERNS))
        self._inference_re = re.compile("|".join(self.INFERENCE_PATTERNS))
        self._hypothesis_re = re.compile("|".join(self.HYPOTHESIS_PATTERNS))
        self._obs_ref_re = re.compile(self.OBSERVATION_REF_PATTERN)

    def extract_claims(self, text: str) -> list[ExtractedClaim]:
        """Extract claims from LLM output text.

        Args:
            text: LLM-generated response text.

        Returns:
            List of extracted claims with metadata.
        """
        claims = []

        # Split into sentences (simplified)
        sentences = self._split_into_sentences(text)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence) < 10:
                continue

            claim = self._analyze_sentence(sentence)
            if claim:
                claims.append(claim)

        return claims

    def _split_into_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        # Split on Chinese and English punctuation
        sentences = re.split(r'[。！？\n]|(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _analyze_sentence(self, sentence: str) -> ExtractedClaim | None:
        """Analyze a sentence to extract claim information."""
        # Extract observation references
        obs_refs = self._obs_ref_re.findall(sentence)

        # Determine claim type based on patterns
        claim_type = self._determine_claim_type(sentence, obs_refs)

        # Skip if it doesn't look like a meaningful claim
        if not self._is_meaningful_claim(sentence):
            return None

        # Determine confidence hint
        confidence_hint = self._determine_confidence_hint(sentence, claim_type, obs_refs)

        return ExtractedClaim(
            statement=sentence,
            claim_type=claim_type,
            observation_refs=obs_refs,
            confidence_hint=confidence_hint,
        )

    def _determine_claim_type(
        self,
        sentence: str,
        obs_refs: list[str]
    ) -> ClaimType:
        """Determine the type of claim based on content."""
        # If has observation references and fact patterns, it's a fact
        if obs_refs and self._fact_re.search(sentence):
            return ClaimType.FACT

        # Check for inference patterns
        if self._inference_re.search(sentence):
            return ClaimType.INFERENCE

        # Check for hypothesis patterns
        if self._hypothesis_re.search(sentence):
            return ClaimType.HYPOTHESIS

        # Default to inference if has some obs refs but no clear patterns
        if obs_refs:
            return ClaimType.FACT

        # Default to hypothesis for unsupported statements
        return ClaimType.HYPOTHESIS

    def _determine_confidence_hint(
        self,
        sentence: str,
        claim_type: ClaimType,
        obs_refs: list[str]
    ) -> str:
        """Determine confidence level hint."""
        if claim_type == ClaimType.FACT and obs_refs:
            return "high"
        elif claim_type == ClaimType.INFERENCE and obs_refs:
            return "medium"
        else:
            return "low"

    def _is_meaningful_claim(self, sentence: str) -> bool:
        """Check if sentence represents a meaningful claim."""
        # Skip questions
        if sentence.endswith("？") or sentence.endswith("?"):
            return False

        # Skip very short sentences
        if len(sentence) < 15:
            return False

        # Skip metadata/formatting
        skip_patterns = ["【", "】", "---", "===", "输出格式"]
        if any(p in sentence for p in skip_patterns):
            return False

        return True

    def build_claim(
        self,
        extracted: ExtractedClaim,
        observations: dict[str, Observation]
    ) -> Claim:
        """Build a full Claim from extracted data.

        Args:
            extracted: Extracted claim data.
            observations: Available observations for reference.

        Returns:
            A Claim object with provenance information.
        """
        # Build transform chain
        transform_chain = []

        if extracted.observation_refs:
            transform_chain.append(TransformStep(
                operation="extract",
                description=f"从观测数据提取信息",
                input_ids=extracted.observation_refs,
                confidence_delta=0.0,
            ))

        if extracted.claim_type == ClaimType.INFERENCE:
            transform_chain.append(TransformStep(
                operation="infer",
                description="基于观测数据进行逻辑推断",
                input_ids=extracted.observation_refs,
                confidence_delta=-0.1,  # Inference reduces confidence slightly
            ))

        elif extracted.claim_type == ClaimType.HYPOTHESIS:
            transform_chain.append(TransformStep(
                operation="infer",
                description="推测性假设",
                input_ids=extracted.observation_refs,
                confidence_delta=-0.3,  # Hypothesis reduces confidence more
            ))

        claim = Claim(
            statement=extracted.statement,
            claim_type=extracted.claim_type,
            source_observations=extracted.observation_refs,
            transform_chain=transform_chain,
        )

        # Compute confidence
        claim.update_confidence(observations)

        return claim
