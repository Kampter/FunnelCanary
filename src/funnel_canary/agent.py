"""ProblemSolvingAgent for closed-loop problem solving."""

import json

from openai import OpenAI

from .config import Config
from .prompts import SYSTEM_PROMPT
from .tools import TOOLS, execute_tool


class ProblemSolvingAgent:
    """Agent that solves problems using a closed-loop approach with tools."""

    def __init__(self, config: Config | None = None, max_iterations: int = 10):
        """Initialize the agent with configuration.

        Args:
            config: Configuration object. If None, loads from environment.
            max_iterations: Maximum number of iterations to prevent infinite loops.
        """
        self.config = config or Config.from_env()
        self.max_iterations = max_iterations
        self.client = OpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
        )

    def solve(self, problem: str) -> str:
        """Solve a problem using the closed-loop approach.

        Args:
            problem: The problem statement to solve.

        Returns:
            The final answer or solution.
        """
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": problem},
        ]

        for iteration in range(self.max_iterations):
            response = self.client.chat.completions.create(
                model=self.config.model_name,
                messages=messages,
                tools=TOOLS,
                temperature=0.7,
            )

            message = response.choices[0].message
            messages.append(message)

            # Display reasoning/thinking if present
            if message.content:
                print(message.content)

            # Check if we have tool calls to execute
            if message.tool_calls:
                print("\n【执行】")
                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        arguments = {}

                    # Display tool call
                    args_display = ", ".join(f'{k}="{v}"' for k, v in arguments.items())
                    print(f"→ {function_name}({args_display})")

                    # Execute the tool
                    result = execute_tool(function_name, arguments)
                    print(f"  结果: {result[:200]}{'...' if len(result) > 200 else ''}\n")

                    # Add tool result to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    })

            # If no tool calls and finish_reason is "stop", we have the final answer
            if response.choices[0].finish_reason == "stop" and not message.tool_calls:
                return message.content or ""

        return "达到最大迭代次数，未能完成问题解决。"
