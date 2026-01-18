"""Context manager for conversation history."""

from typing import Any, Callable

from .summarizer import Summarizer


class ContextManager:
    """Manages conversation context with sliding window and summarization.

    Features:
    - Sliding window to keep recent messages
    - Token budget management
    - Automatic summarization of older messages
    - Memory integration support
    """

    def __init__(
        self,
        window_size: int = 10,
        token_budget: int = 8000,
        summarizer: Summarizer | None = None,
    ) -> None:
        """Initialize the context manager.

        Args:
            window_size: Number of recent messages to keep in full.
            token_budget: Approximate token budget for context.
            summarizer: Optional summarizer for compressing history.
        """
        self._messages: list[dict[str, Any]] = []
        self._window_size = window_size
        self._token_budget = token_budget
        self._summarizer = summarizer
        self._summary: str | None = None
        self._summary_up_to_index: int = 0

    def add_message(self, message: dict[str, Any]) -> None:
        """Add a message to the conversation history.

        Args:
            message: Message dict with 'role' and 'content' keys.
        """
        self._messages.append(message)
        self._maybe_compress()

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant message.

        Args:
            content: Message content.
        """
        self.add_message({"role": "assistant", "content": content})

    def add_user_message(self, content: str) -> None:
        """Add a user message.

        Args:
            content: Message content.
        """
        self.add_message({"role": "user", "content": content})

    def add_tool_result(self, tool_call_id: str, content: str) -> None:
        """Add a tool result message.

        Args:
            tool_call_id: ID of the tool call.
            content: Tool result content.
        """
        self.add_message({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content,
        })

    def build_messages(
        self,
        system_prompt: str,
        memory_context: str | None = None,
    ) -> list[dict[str, Any]]:
        """Build the message list for API call.

        Args:
            system_prompt: System prompt to use.
            memory_context: Optional memory context to include.

        Returns:
            List of messages ready for API call.
        """
        messages: list[dict[str, Any]] = []

        # System message
        system_content = system_prompt
        if memory_context:
            system_content += f"\n\n## 相关记忆\n\n{memory_context}"
        messages.append({"role": "system", "content": system_content})

        # Add summary if available
        if self._summary:
            messages.append({
                "role": "system",
                "content": f"【对话历史摘要】\n{self._summary}",
            })

        # Add recent messages (within window), adjusted to preserve tool pairs
        window_start = max(0, len(self._messages) - self._window_size)
        window_start = self._adjust_window_for_tool_pairs(window_start)
        for msg in self._messages[window_start:]:
            messages.append(msg)

        # Validate and clean message coherence to prevent orphaned tool_results
        messages = self._ensure_message_coherence(messages)

        return messages

    def _adjust_window_for_tool_pairs(self, window_start: int) -> int:
        """Adjust window_start to ensure we don't split tool_use/tool_result pairs.

        If window_start would cut in the middle of a tool sequence, move it back
        to include the assistant message with tool_calls.

        Args:
            window_start: The proposed starting index for the window.

        Returns:
            Adjusted window_start that preserves tool pairs.
        """
        if window_start >= len(self._messages) or window_start == 0:
            return window_start

        # Check if message at window_start is a tool_result
        if self._messages[window_start].get("role") == "tool":
            # Move window back to include the assistant message with tool_calls
            for i in range(window_start - 1, -1, -1):
                msg = self._messages[i]
                if msg.get("role") == "assistant":
                    if msg.get("tool_calls"):
                        return i
                    # Found assistant without tool_calls, stop searching
                    break

        return window_start

    def _ensure_message_coherence(
        self,
        messages: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Remove orphaned tool_result messages that don't have a corresponding tool_use.

        A tool_result is considered orphaned if there is no assistant message
        with a matching tool_call in the preceding messages.

        Args:
            messages: List of messages to validate.

        Returns:
            Cleaned list with orphaned tool_results removed.
        """
        cleaned: list[dict[str, Any]] = []

        for i, msg in enumerate(messages):
            if msg.get("role") == "tool":
                # Check if there's a matching tool_call in preceding messages
                tool_call_id = msg.get("tool_call_id")
                if tool_call_id and self._has_matching_tool_call(cleaned, tool_call_id):
                    cleaned.append(msg)
                # else: skip orphaned tool_result
            else:
                cleaned.append(msg)

        return cleaned

    def _has_matching_tool_call(
        self,
        messages: list[dict[str, Any]],
        tool_call_id: str,
    ) -> bool:
        """Check if any assistant message has a matching tool_call.

        Args:
            messages: List of messages to search.
            tool_call_id: The tool_call_id to match.

        Returns:
            True if a matching tool_call is found.
        """
        for msg in reversed(messages):
            if msg.get("role") == "assistant":
                tool_calls = msg.get("tool_calls", [])
                for tc in tool_calls:
                    if tc.get("id") == tool_call_id:
                        return True
        return False

    def _maybe_compress(self) -> None:
        """Compress history if needed."""
        if self._summarizer is None:
            return

        estimated_tokens = self._estimate_tokens()
        if estimated_tokens <= self._token_budget:
            return

        # Need to summarize older messages
        window_start = max(0, len(self._messages) - self._window_size)
        if window_start <= self._summary_up_to_index:
            return

        # Get messages to summarize
        messages_to_summarize = self._messages[self._summary_up_to_index:window_start]
        if not messages_to_summarize:
            return

        # Generate summary
        new_summary = self._summarizer.summarize(
            messages_to_summarize,
            existing_summary=self._summary,
        )

        self._summary = new_summary
        self._summary_up_to_index = window_start

    def _estimate_tokens(self) -> int:
        """Estimate total tokens in context.

        Uses a rough approximation of 4 characters per token.

        Returns:
            Estimated token count.
        """
        total_chars = 0

        if self._summary:
            total_chars += len(self._summary)

        for msg in self._messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total_chars += len(content)

        return total_chars // 4

    def get_message_count(self) -> int:
        """Get the total number of messages.

        Returns:
            Number of messages in history.
        """
        return len(self._messages)

    def get_summary(self) -> str | None:
        """Get the current summary.

        Returns:
            Summary string or None if not summarized.
        """
        return self._summary

    def clear(self) -> None:
        """Clear all messages and summary."""
        self._messages = []
        self._summary = None
        self._summary_up_to_index = 0

    @property
    def messages(self) -> list[dict[str, Any]]:
        """Get all messages (for debugging/inspection)."""
        return self._messages.copy()
