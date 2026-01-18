"""Interaction tools for user communication."""

from ..base import Tool, ToolMetadata, ToolParameter, ToolResult


# User input doesn't expire but has lower confidence (subjective)
USER_INPUT_CONFIDENCE = 0.8


def _ask_user(question: str) -> ToolResult:
    """Ask the user a clarifying question.

    Args:
        question: The question to ask.

    Returns:
        ToolResult with user's response and provenance information.
    """
    tool_name = "ask_user"

    try:
        print(f"\n❓ Agent 询问: {question}")
        response = input("您的回答: ")

        # User input uses USER_INPUT source type with 80% confidence
        return ToolResult.from_success(
            content=response,
            tool_name=tool_name,
            confidence=USER_INPUT_CONFIDENCE,
            ttl_seconds=None,  # User input doesn't expire
            scope="user_input",
            metadata={
                "question": question,
            },
        )

    except (EOFError, KeyboardInterrupt):
        return ToolResult.from_error("用户取消输入", tool_name)


# Tool definitions
ask_user = Tool(
    metadata=ToolMetadata(
        name="ask_user",
        description="向用户询问澄清信息。当问题不明确或需要用户提供更多信息时使用。",
        category="interaction",
        parameters=[
            ToolParameter(
                name="question",
                type="string",
                description="要询问用户的问题",
                required=True,
            )
        ],
        skill_bindings=["clarification"],
    ),
    execute=_ask_user,
)

# Export all tools from this category
INTERACTION_TOOLS = [ask_user]
