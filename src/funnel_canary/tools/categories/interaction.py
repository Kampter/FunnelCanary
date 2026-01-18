"""Interaction tools for user communication."""

from ..base import Tool, ToolMetadata, ToolParameter


def _ask_user(question: str) -> str:
    """Ask the user a clarifying question.

    Args:
        question: The question to ask.

    Returns:
        User's response.
    """
    print(f"\n❓ Agent 询问: {question}")
    response = input("您的回答: ")
    return response


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
