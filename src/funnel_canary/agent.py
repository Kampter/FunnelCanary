"""ProblemSolvingAgent for closed-loop problem solving."""

import json
import uuid
from typing import Any

from openai import OpenAI

from .config import Config
from .context import ContextManager, Summarizer
from .memory import Fact, MemoryStore, SessionSummary
from .prompts import PromptBuilder
from .skills import Skill, SkillMetadata, SkillRegistry
from .tools import ToolRegistry, create_default_registry


class ProblemSolvingAgent:
    """Agent that solves problems using a closed-loop approach with tools.

    Features:
    - Progressive skill loading
    - Context management with sliding window
    - Persistent memory across sessions
    - Modular prompt building
    """

    def __init__(
        self,
        config: Config | None = None,
        max_iterations: int = 10,
        enable_memory: bool = True,
        enable_skills: bool = True,
        window_size: int = 10,
        token_budget: int = 8000,
    ):
        """Initialize the agent with configuration.

        Args:
            config: Configuration object. If None, loads from environment.
            max_iterations: Maximum number of iterations to prevent infinite loops.
            enable_memory: Whether to enable persistent memory.
            enable_skills: Whether to enable skill system.
            window_size: Context window size for recent messages.
            token_budget: Approximate token budget for context.
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

        # Match and load skill if enabled
        if self.skill_registry:
            skill_meta = self.skill_registry.match_skill(problem)
            if skill_meta:
                self._current_skill = self.skill_registry.load_full_skill(
                    skill_meta.name
                )

        # Build system prompt
        system_prompt = self._build_system_prompt(problem)

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
            # Build messages for API call
            messages = self.context_manager.build_messages(
                system_prompt,
                memory_context=memory_context,
            )

            # Make API call
            response = self.client.chat.completions.create(
                model=self.config.model_name,
                messages=messages,
                tools=tools_schema if tools_schema else None,
                temperature=0.7,
            )

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
                    result = self._execute_tool_call(tool_call)

                    # Add tool result to context
                    self.context_manager.add_tool_result(
                        tool_call.id,
                        result,
                    )

            # If no tool calls and finish_reason is "stop", we have the final answer
            if response.choices[0].finish_reason == "stop" and not message.tool_calls:
                final_answer = message.content or ""
                break

        if not final_answer:
            final_answer = "达到最大迭代次数，未能完成问题解决。"

        # Save session summary if memory is enabled
        if self.memory:
            self._save_session_summary(problem, final_answer)

        return final_answer

    def _build_system_prompt(self, problem: str) -> str:
        """Build system prompt based on current state.

        Args:
            problem: The problem being solved.

        Returns:
            Assembled system prompt.
        """
        self.prompt_builder.reset()

        # Add tool descriptions
        self.prompt_builder.with_tools(self.tool_registry)

        # Add skill content if available
        if self._current_skill:
            self.prompt_builder.with_skill(self._current_skill)

            # Add relevant components based on skill
            skill_name = self._current_skill.name
            if skill_name == "calculation":
                self.prompt_builder.with_component("calculation")
                self.prompt_builder.with_output_format("calculation")
            elif skill_name == "research":
                self.prompt_builder.with_component("research")
                self.prompt_builder.with_output_format("research")
            elif skill_name == "problem_decomposition":
                self.prompt_builder.with_component("thinking")
                self.prompt_builder.with_output_format("decomposition")
            elif skill_name == "clarification":
                self.prompt_builder.with_component("clarification")

        # Add memory facts if available
        if self.memory:
            facts = self.memory.get_relevant_facts(problem, limit=3)
            if facts:
                self.prompt_builder.with_memory(facts)

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

    def _execute_tool_call(self, tool_call: Any) -> str:
        """Execute a tool call and display results.

        Args:
            tool_call: Tool call from API response.

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

        # Execute the tool
        result = self.tool_registry.execute(function_name, arguments)
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
