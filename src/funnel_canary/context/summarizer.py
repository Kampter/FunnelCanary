"""Summarizer for conversation history compression."""

from typing import Any, Callable


class Summarizer:
    """Summarizes conversation history to reduce context size.

    Can use either an LLM-based summarizer or a simple rule-based one.
    """

    def __init__(
        self,
        llm_summarize_fn: Callable[[str], str] | None = None,
        max_summary_length: int = 500,
    ) -> None:
        """Initialize the summarizer.

        Args:
            llm_summarize_fn: Optional function that takes text and returns summary.
                              If None, uses rule-based summarization.
            max_summary_length: Maximum length of generated summary.
        """
        self._llm_summarize = llm_summarize_fn
        self._max_summary_length = max_summary_length

    def summarize(
        self,
        messages: list[dict[str, Any]],
        existing_summary: str | None = None,
    ) -> str:
        """Summarize a list of messages.

        Args:
            messages: Messages to summarize.
            existing_summary: Optional existing summary to build upon.

        Returns:
            Summary string.
        """
        if self._llm_summarize:
            return self._llm_summarize_messages(messages, existing_summary)
        else:
            return self._rule_based_summarize(messages, existing_summary)

    def _llm_summarize_messages(
        self,
        messages: list[dict[str, Any]],
        existing_summary: str | None,
    ) -> str:
        """Use LLM to summarize messages."""
        # Format messages for summarization
        formatted = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if isinstance(content, str) and content:
                formatted.append(f"[{role}]: {content[:200]}")

        text_to_summarize = "\n".join(formatted)

        if existing_summary:
            prompt = f"现有摘要：{existing_summary}\n\n新对话内容：\n{text_to_summarize}\n\n请更新摘要，保留关键信息："
        else:
            prompt = f"请总结以下对话的关键信息：\n{text_to_summarize}"

        return self._llm_summarize(prompt)  # type: ignore

    def _rule_based_summarize(
        self,
        messages: list[dict[str, Any]],
        existing_summary: str | None,
    ) -> str:
        """Use rule-based approach to summarize messages."""
        key_points = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if not isinstance(content, str):
                continue

            # Extract key information based on role
            if role == "user":
                # Keep user questions/requests (shortened)
                if len(content) > 100:
                    key_points.append(f"用户问题: {content[:100]}...")
                else:
                    key_points.append(f"用户问题: {content}")

            elif role == "assistant":
                # Extract conclusions or answers
                if "【答案】" in content:
                    answer_start = content.find("【答案】")
                    answer = content[answer_start:answer_start + 200]
                    key_points.append(f"回答: {answer}")
                elif len(content) > 150:
                    key_points.append(f"助手回复: {content[:100]}...")

            elif role == "tool":
                # Note tool usage
                tool_id = msg.get("tool_call_id", "")
                key_points.append(f"工具调用结果 ({tool_id[:20]})")

        # Combine with existing summary
        if existing_summary:
            summary_parts = [f"之前的对话: {existing_summary}"]
        else:
            summary_parts = []

        summary_parts.extend(key_points)

        # Truncate if too long
        summary = "\n".join(summary_parts)
        if len(summary) > self._max_summary_length:
            summary = summary[:self._max_summary_length] + "..."

        return summary


def create_llm_summarizer(
    client: Any,
    model: str = "gpt-4",
) -> Summarizer:
    """Create a summarizer that uses an LLM.

    Args:
        client: OpenAI client instance.
        model: Model to use for summarization.

    Returns:
        Configured Summarizer instance.
    """

    def llm_summarize(prompt: str) -> str:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是一个对话摘要助手，请简洁地总结对话的关键信息。"},
                {"role": "user", "content": prompt},
            ],
            max_tokens=300,
            temperature=0.3,
        )
        return response.choices[0].message.content or ""

    return Summarizer(llm_summarize_fn=llm_summarize)
