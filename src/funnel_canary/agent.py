"""ProblemSolvingAgent for closed-loop problem solving."""

import json
import uuid
from typing import Any

from openai import OpenAI

from .cognitive import CognitiveState, MinimalCommitmentPolicy, StrategyGate
from .cognitive.strategy import StrategyDecision
from .config import Config
from .context import ContextManager, Summarizer
from .memory import Fact, MemoryStore, SessionSummary
from .prompts import PromptBuilder
from .provenance import (
    GroundedAnswerGenerator,
    Observation,
    ObservationType,
    ProvenanceRegistry,
)
from .skills import Skill, SkillMetadata, SkillRegistry
from .tools import ToolRegistry, create_default_registry


class ProblemSolvingAgent:
    """Agent that solves problems using a closed-loop approach with tools.

    Features:
    - Progressive skill loading
    - Context management with sliding window
    - Persistent memory across sessions
    - Modular prompt building
    - Provenance tracking for anti-hallucination (v0.0.4)
    """

    def __init__(
        self,
        config: Config | None = None,
        max_iterations: int = 10,
        enable_memory: bool = True,
        enable_skills: bool = True,
        enable_cognitive: bool = True,
        enable_grounding: bool = True,
        window_size: int = 10,
        token_budget: int = 8000,
        confidence_threshold: float = 0.7,
        stall_threshold: int = 3,
    ):
        """Initialize the agent with configuration.

        Args:
            config: Configuration object. If None, loads from environment.
            max_iterations: Maximum number of iterations to prevent infinite loops.
            enable_memory: Whether to enable persistent memory.
            enable_skills: Whether to enable skill system.
            enable_cognitive: Whether to enable cognitive state system.
            enable_grounding: Whether to enable provenance tracking and grounding.
            window_size: Context window size for recent messages.
            token_budget: Approximate token budget for context.
            confidence_threshold: Confidence threshold for strategy decisions.
            stall_threshold: Number of stalled iterations before pivoting.
        """
        self.config = config or Config.from_env()
        self.max_iterations = max_iterations

        # Initialize OpenAI client
        self.client = OpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
        )

        # Initialize tool registry
        self.tool_registry = create_default_registry()

        # Initialize skill registry
        self.skill_registry = SkillRegistry() if enable_skills else None
        if self.skill_registry:
            self.skill_registry.discover_skills()

        # Initialize memory store
        self.memory = MemoryStore() if enable_memory else None

        # Initialize context manager with summarizer
        summarizer = Summarizer()  # Rule-based by default
        self.context_manager = ContextManager(
            window_size=window_size,
            token_budget=token_budget,
            summarizer=summarizer,
        )

        # Initialize prompt builder
        self.prompt_builder = PromptBuilder()

        # Initialize cognitive system
        self.enable_cognitive = enable_cognitive
        if self.enable_cognitive:
            self.strategy_gate = StrategyGate(
                confidence_threshold=confidence_threshold,
                stall_threshold=stall_threshold,
            )
            self.safety_policy = MinimalCommitmentPolicy()
        else:
            self.strategy_gate = None
            self.safety_policy = None

        # Initialize provenance system (v0.0.4)
        self.enable_grounding = enable_grounding
        self.provenance_registry: ProvenanceRegistry | None = None
        self.grounded_generator: GroundedAnswerGenerator | None = None
        if self.enable_grounding:
            self.grounded_generator = GroundedAnswerGenerator()

        # Session tracking
        self._session_id = str(uuid.uuid4())[:8]
        self._current_skill: Skill | None = None

    def solve(self, problem: str) -> str:
        """Solve a problem using the closed-loop approach.

        Args:
            problem: The problem statement to solve.

        Returns:
            The final answer or solution.
        """
        # Reset context for new problem
        self.context_manager.clear()
        self._current_skill = None

        # Initialize provenance registry for this session (v0.0.4)
        if self.enable_grounding:
            self.provenance_registry = ProvenanceRegistry()
            # Record user input as observation
            user_observation = Observation(
                content=problem[:500],
                source_type=ObservationType.USER_INPUT,
                source_id="user",
                confidence=0.8,  # User input has 80% confidence
                scope="problem_statement",
            )
            self.provenance_registry.add_observation(user_observation)

        # Initialize cognitive state if enabled
        cognitive_state = None
        if self.enable_cognitive:
            cognitive_state = CognitiveState(
                goal_statement=problem,
                confidence=0.3,  # Start with low confidence
            )

        # Match and load skill if enabled
        if self.skill_registry:
            skill_meta = self.skill_registry.match_skill(problem)
            if skill_meta:
                self._current_skill = self.skill_registry.load_full_skill(
                    skill_meta.name
                )

        # Build system prompt
        system_prompt = self._build_system_prompt(problem, cognitive_state)

        # Get memory context
        memory_context = None
        if self.memory:
            memory_context = self.memory.build_memory_context(problem)

        # Add user message
        self.context_manager.add_user_message(problem)

        # Get tools to use
        tools = self._get_tools_for_current_skill()
        tools_schema = self.tool_registry.to_openai_schema(tools)

        # Main loop
        final_answer = ""
        for iteration in range(self.max_iterations):
            try:
                # Update cognitive state if enabled
                if cognitive_state:
                    cognitive_state.increment_iteration()

                # Evaluate strategy if cognitive state enabled
                if cognitive_state and self.strategy_gate:
                    # v0.0.4: Pass provenance registry for observation-based decisions
                    strategy_path = self.strategy_gate.evaluate(
                        cognitive_state,
                        provenance_registry=self.provenance_registry if self.enable_grounding else None,
                    )

                    # Handle strategy decisions
                    if strategy_path.decision == StrategyDecision.CONCLUDE:
                        # High confidence - can conclude
                        print(f"\n【策略】{strategy_path.reason}")
                        # Continue to get final answer from LLM
                    elif strategy_path.decision == StrategyDecision.DEGRADE:
                        # Low confidence but need to output
                        print(f"\n【策略】{strategy_path.reason}")
                        final_answer = f"基于当前信息的部分答案（置信度: {cognitive_state.confidence:.0%}）\n\n"
                        # Let LLM provide best current answer
                    elif strategy_path.decision == StrategyDecision.PIVOT:
                        print(f"\n【策略】{strategy_path.reason} - 尝试不同方法")
                        # For now, just continue - full pivot logic can be added later
                    elif strategy_path.decision == StrategyDecision.REQUEST_MORE_INFO:
                        # v0.0.4: Need more observations
                        print(f"\n【策略】{strategy_path.reason}")
                        # Continue to let LLM call tools

                # Build messages for API call
                messages = self.context_manager.build_messages(
                    system_prompt,
                    memory_context=memory_context,
                )

                # Make API call with error handling
                try:
                    response = self.client.chat.completions.create(
                        model=self.config.model_name,
                        messages=messages,
                        tools=tools_schema if tools_schema else None,
                        temperature=0.7,
                    )
                except Exception as api_error:
                    print(f"\n【错误】API 调用失败: {str(api_error)}")

                    # Update cognitive state if enabled
                    if cognitive_state:
                        cognitive_state.add_uncertainty(f"API error: {type(api_error).__name__}")

                    # Decide whether to retry or gracefully degrade
                    if iteration < self.max_iterations - 1:
                        print("尝试继续...")
                        continue
                    else:
                        # Last iteration - return partial answer
                        final_answer = self._generate_partial_answer(problem, cognitive_state)
                        break

                message = response.choices[0].message

                # Add to context (convert to dict for storage)
                self.context_manager.add_message(self._message_to_dict(message))

                # Display reasoning/thinking if present
                if message.content:
                    print(message.content)

                # Check if we have tool calls to execute
                if message.tool_calls:
                    print("\n【执行】")
                    for tool_call in message.tool_calls:
                        try:
                            result = self._execute_tool_call(tool_call, cognitive_state)
                        except Exception as tool_error:
                            # Log error but continue with other tools
                            error_msg = f"工具执行失败: {str(tool_error)}"
                            print(f"  {error_msg}")
                            result = error_msg

                        # Add tool result to context (always add, even on error)
                        self.context_manager.add_tool_result(
                            tool_call.id,
                            result,
                        )

                    # Mark progress if cognitive state enabled
                    if cognitive_state:
                        cognitive_state.mark_progress()
                        # Update confidence slightly after successful tool execution
                        cognitive_state.update_confidence(
                            min(cognitive_state.confidence + 0.1, 0.9)
                        )
                else:
                    # No tool calls - might be stalling
                    if cognitive_state:
                        cognitive_state.mark_stall()

                # If no tool calls and finish_reason is "stop", we have the final answer
                if response.choices[0].finish_reason == "stop" and not message.tool_calls:
                    final_answer = message.content or ""
                    break

            except Exception as e:
                # Catch-all for unexpected errors in the iteration
                print(f"\n【错误】迭代 {iteration + 1} 失败: {str(e)}")

                if cognitive_state:
                    cognitive_state.add_uncertainty(f"Iteration error: {type(e).__name__}")

                if iteration < self.max_iterations - 1:
                    print("尝试继续...")
                    continue
                else:
                    final_answer = self._generate_partial_answer(problem, cognitive_state)
                    break

        if not final_answer:
            final_answer = "达到最大迭代次数，未能完成问题解决。"

        # Apply grounded answer generation if enabled (v0.0.4)
        if self.enable_grounding:
            final_answer = self._generate_grounded_answer(final_answer)

        # Save session summary if memory is enabled
        if self.memory:
            self._save_session_summary(problem, final_answer)

        return final_answer

    def _build_system_prompt(self, problem: str, cognitive_state: CognitiveState | None = None) -> str:
        """Build system prompt based on current state.

        Args:
            problem: The problem being solved.
            cognitive_state: Optional cognitive state for context.

        Returns:
            Assembled system prompt.
        """
        self.prompt_builder.reset()

        # Add tool descriptions
        self.prompt_builder.with_tools(self.tool_registry)

        # Add grounding enforcement if enabled (v0.0.4)
        if self.enable_grounding:
            self.prompt_builder.with_grounding_enforcement()
            # Add provenance context if registry has observations
            if self.provenance_registry:
                self.prompt_builder.with_provenance_context(self.provenance_registry)

        # Add skill content if available
        if self._current_skill:
            self.prompt_builder.with_skill(self._current_skill)

            # Add relevant components based on skill
            skill_name = self._current_skill.name
            if skill_name == "calculation":
                self.prompt_builder.with_component("calculation")
                # Only override output format if grounding is disabled
                if not self.enable_grounding:
                    self.prompt_builder.with_output_format("calculation")
            elif skill_name == "research":
                self.prompt_builder.with_component("research")
                if not self.enable_grounding:
                    self.prompt_builder.with_output_format("research")
            elif skill_name == "problem_decomposition":
                self.prompt_builder.with_component("thinking")
                if not self.enable_grounding:
                    self.prompt_builder.with_output_format("decomposition")
            elif skill_name == "clarification":
                self.prompt_builder.with_component("clarification")
            # v0.0.5: New skill mappings
            elif skill_name == "critical_thinking":
                self.prompt_builder.with_component("critical")
            elif skill_name == "comparative_analysis":
                self.prompt_builder.with_component("comparative")
            elif skill_name == "creative_generation":
                self.prompt_builder.with_component("creative")
            elif skill_name == "learning_assistant":
                self.prompt_builder.with_component("learning")
            elif skill_name == "deep_research":
                self.prompt_builder.with_component("research")
            elif skill_name == "summarization":
                self.prompt_builder.with_component("thinking")
            elif skill_name == "decision_support":
                self.prompt_builder.with_component("thinking")
            elif skill_name == "code_analysis":
                self.prompt_builder.with_component("thinking")
            elif skill_name == "planning":
                self.prompt_builder.with_component("thinking")
            elif skill_name == "reflection":
                self.prompt_builder.with_component("thinking")

        # Add memory facts if available
        if self.memory:
            facts = self.memory.get_relevant_facts(problem, limit=3)
            if facts:
                self.prompt_builder.with_memory(facts)

        # Add cognitive context if available
        if cognitive_state:
            cognitive_context = cognitive_state.to_context()
            if cognitive_context:
                self.prompt_builder.with_cognitive_state(cognitive_context)

        return self.prompt_builder.build()

    def _get_tools_for_current_skill(self) -> list[Any]:
        """Get tools for the current skill or all tools.

        Returns:
            List of tools to use.
        """
        if self._current_skill:
            # Only provide tools declared by the skill
            return self.tool_registry.get_for_skill(self._current_skill.tools)
        else:
            # Provide all tools
            return self.tool_registry.get_all()

    def _execute_tool_call(
        self,
        tool_call: Any,
        cognitive_state: CognitiveState | None = None,
    ) -> str:
        """Execute a tool call and display results.

        Args:
            tool_call: Tool call from API response.
            cognitive_state: Optional cognitive state to update with observation info.

        Returns:
            Tool execution result.
        """
        function_name = tool_call.function.name
        try:
            arguments = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError:
            arguments = {}

        # Display tool call
        args_display = ", ".join(f'{k}="{v}"' for k, v in arguments.items())
        print(f"→ {function_name}({args_display})")

        # Execute the tool (returns ExecutionResult with provenance)
        execution_result = self.tool_registry.execute(function_name, arguments)

        # Record observation if grounding is enabled
        if self.enable_grounding and self.provenance_registry:
            if execution_result.observation:
                self.provenance_registry.add_observation(execution_result.observation)

                # v0.0.4: Also update cognitive state with observation info
                if cognitive_state:
                    cognitive_state.record_observation(execution_result.observation.confidence)

        # Get content for display and return
        result = execution_result.content
        print(f"  结果: {result[:200]}{'...' if len(result) > 200 else ''}\n")

        return result

    def _message_to_dict(self, message: Any) -> dict[str, Any]:
        """Convert API message to dictionary.

        Args:
            message: Message from API response.

        Returns:
            Dictionary representation.
        """
        msg_dict: dict[str, Any] = {"role": message.role}

        if message.content:
            msg_dict["content"] = message.content

        if message.tool_calls:
            msg_dict["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in message.tool_calls
            ]

        return msg_dict

    def _generate_partial_answer(
        self,
        problem: str,
        cognitive_state: CognitiveState | None = None,
    ) -> str:
        """Generate a partial answer when errors prevent full completion.

        Args:
            problem: The original problem.
            cognitive_state: Optional cognitive state for context.

        Returns:
            A partial answer with available information.
        """
        parts = ["由于遇到错误，无法完成完整的问题解决。"]

        if cognitive_state:
            parts.append(f"\n当前置信度: {cognitive_state.confidence:.0%}")
            parts.append(f"已完成迭代: {cognitive_state.iteration_count}")

            if cognitive_state.uncertainties:
                parts.append("\n遇到的问题:")
                for uncertainty in cognitive_state.uncertainties[-3:]:
                    parts.append(f"  - {uncertainty}")

        # Try to extract any useful information from conversation history
        messages = self.context_manager.messages
        assistant_contents = []
        for msg in messages:
            if msg.get("role") == "assistant" and msg.get("content"):
                content = msg["content"]
                if len(content) > 50:  # Only include substantial responses
                    assistant_contents.append(content)

        if assistant_contents:
            parts.append("\n\n基于已收集的信息:")
            # Include the last meaningful assistant response
            parts.append(assistant_contents[-1][:500])

        return "\n".join(parts)

    def _save_session_summary(self, problem: str, answer: str) -> None:
        """Save a summary of the current session.

        Args:
            problem: The original problem.
            answer: The final answer.
        """
        if not self.memory:
            return

        summary = SessionSummary(
            session_id=self._session_id,
            summary=f"问题: {problem[:100]}... 回答: {answer[:100]}...",
            key_topics=[],
            facts_learned=[],
        )
        self.memory.save_session_summary(summary)

    def learn_fact(self, content: str, category: str = "general") -> None:
        """Manually add a fact to memory.

        Args:
            content: Fact content.
            category: Fact category.
        """
        if self.memory:
            fact = Fact(content=content, category=category, source="manual")
            self.memory.add_fact(fact)

    def get_available_skills(self) -> list[SkillMetadata]:
        """Get all available skills.

        Returns:
            List of skill metadata.
        """
        if self.skill_registry:
            return self.skill_registry.get_all_metadata()
        return []

    @property
    def session_id(self) -> str:
        """Get the current session ID."""
        return self._session_id

    def _generate_grounded_answer(self, raw_answer: str) -> str:
        """Generate a grounded answer with provenance tracking.

        Args:
            raw_answer: The raw LLM-generated answer.

        Returns:
            Answer with provenance information if grounding is enabled.
        """
        if not self.enable_grounding or not self.grounded_generator:
            return raw_answer

        if not self.provenance_registry:
            return raw_answer

        # Generate grounded answer
        grounded = self.grounded_generator.generate(
            raw_answer=raw_answer,
            registry=self.provenance_registry,
        )

        # Return formatted output if degraded, otherwise just the content
        if grounded.degradation_level.value > 1:  # Not FULL_ANSWER
            return grounded.to_formatted_output()

        return grounded.content

    def get_provenance_summary(self) -> str | None:
        """Get a summary of the current provenance tracking.

        Returns:
            Provenance summary string, or None if grounding is disabled.
        """
        if not self.enable_grounding or not self.provenance_registry:
            return None

        if not self.grounded_generator:
            return None

        return self.grounded_generator.format_provenance_summary(
            self.provenance_registry
        )

    def get_observation_count(self) -> int:
        """Get the number of observations recorded.

        Returns:
            Number of observations, or 0 if grounding is disabled.
        """
        if not self.provenance_registry:
            return 0
        return self.provenance_registry.get_observation_count()

