# Error Handling Guide

## Overview

FunnelCanary implements comprehensive error handling to ensure robust operation even when encountering API failures, tool execution errors, or message coherence issues.

## Architecture

### 1. Message Coherence Validation

**Problem:** When the context manager's sliding window compresses conversation history, it can create invalid message sequences where `tool_result` messages are orphaned (their parent `assistant` message with `tool_calls` was removed).

**Solution:** Two-layer protection:

#### Layer 1: Window Adjustment
```python
def _adjust_window_for_tool_pairs(self, window_start: int) -> int:
    """Adjust window to preserve tool_use/tool_result pairs."""
```

- Checks if window would start at a `tool_result` message
- Moves window back to include the corresponding `assistant` message
- Prevents orphaning at the source

#### Layer 2: Coherence Validation
```python
def _ensure_message_coherence(self, messages: list[dict]) -> list[dict]:
    """Remove orphaned tool_results that lack matching tool_use."""
```

- Scans all messages for orphaned `tool_result` entries
- Removes any that don't have a matching `tool_call` in preceding messages
- Acts as a safety net if window adjustment misses edge cases

**Usage:**
```python
messages = self.context_manager.build_messages(system_prompt)
# Messages are automatically validated and cleaned
```

### 2. API Error Handling

**Problem:** API calls can fail due to network issues, rate limits, or service outages, causing the entire agent to crash.

**Solution:** Nested try-except with retry logic:

```python
try:
    response = self.client.chat.completions.create(...)
except Exception as api_error:
    print(f"\n【错误】API 调用失败: {str(api_error)}")

    # Update cognitive state
    if cognitive_state:
        cognitive_state.add_uncertainty(f"API error: {type(api_error).__name__}")

    # Retry or degrade
    if iteration < self.max_iterations - 1:
        print("尝试继续...")
        continue
    else:
        final_answer = self._generate_partial_answer(problem, cognitive_state)
        break
```

**Behavior:**
- **Transient errors:** Retry on next iteration
- **Persistent errors:** Generate partial answer with available information
- **Cognitive tracking:** Records error in uncertainty list

### 3. Tool Execution Error Handling

**Problem:** Individual tool failures shouldn't crash the entire iteration or prevent other tools from executing.

**Solution:** Per-tool error handling:

```python
for tool_call in message.tool_calls:
    try:
        result = self._execute_tool_call(tool_call)
    except Exception as tool_error:
        error_msg = f"工具执行失败: {str(tool_error)}"
        print(f"  {error_msg}")
        result = error_msg

    # Always add tool_result (even on error)
    self.context_manager.add_tool_result(tool_call.id, result)
```

**Benefits:**
- One tool failure doesn't affect others
- Error message passed to LLM for recovery
- Maintains message coherence (tool_result always added)

### 4. Partial Answer Generation

**Problem:** When errors prevent completion, the agent should provide useful information rather than just failing.

**Solution:** `_generate_partial_answer()` method:

```python
def _generate_partial_answer(
    self,
    problem: str,
    cognitive_state: CognitiveState | None = None,
) -> str:
    """Generate partial answer when errors prevent full completion."""
```

**Includes:**
- Error acknowledgment
- Current confidence level
- Completed iterations
- List of encountered problems (last 3)
- Last meaningful assistant response (up to 500 chars)

**Example Output:**
```
由于遇到错误，无法完成完整的问题解决。

当前置信度: 30%
已完成迭代: 2

遇到的问题:
  - API error: ConnectionError
  - Tool execution failed: web_search

基于已收集的信息:
[Last assistant response content...]
```

## Error Recovery Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent Iteration Loop                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ Build Messages   │
                    │ (with validation)│
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   API Call       │
                    └──────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
                 Success             Error
                    │                   │
                    ▼                   ▼
          ┌──────────────────┐  ┌──────────────────┐
          │ Execute Tools    │  │ Log Error        │
          └──────────────────┘  │ Update State     │
                    │            │ Retry/Degrade   │
          ┌─────────┴─────────┐ └──────────────────┘
          │                   │
       Success             Error
          │                   │
          ▼                   ▼
    ┌──────────┐      ┌──────────────┐
    │ Continue │      │ Error Result │
    └──────────┘      │ to Context   │
                      └──────────────┘
```

## Cognitive State Integration

The error handling system integrates with the cognitive state system to make intelligent decisions:

### Confidence Tracking
- Errors decrease confidence
- Successful tool execution increases confidence
- Low confidence triggers graceful degradation

### Uncertainty Tracking
- Each error adds to uncertainty list
- Uncertainties inform strategy decisions
- Displayed in partial answers

### Strategy Decisions
- **CONCLUDE:** High confidence, can provide answer
- **DEGRADE:** Low confidence, provide partial answer
- **PIVOT:** Stalled progress, try different approach

## Testing

### Unit Tests

Test message coherence:
```python
from funnel_canary.context import ContextManager

manager = ContextManager()
messages = [
    {"role": "system", "content": "..."},
    {"role": "tool", "tool_call_id": "orphaned", "content": "..."},
]
cleaned = manager._ensure_message_coherence(messages)
# Orphaned tool_result removed
```

### Integration Tests

Test error recovery:
```python
agent = ProblemSolvingAgent(max_iterations=3)
# Mock API to fail once then succeed
result = agent.solve("Test problem")
# Should recover and complete
```

### Load Tests

Test with many tool calls:
```python
manager = ContextManager(window_size=5)
for i in range(20):
    # Add messages with tool calls
    ...
messages = manager.build_messages("System")
# All tool_results should have matching tool_calls
```

## Configuration

Error handling behavior can be configured:

```python
agent = ProblemSolvingAgent(
    max_iterations=10,          # Max retry attempts
    enable_cognitive=True,      # Enable cognitive state tracking
    confidence_threshold=0.7,   # Threshold for strategy decisions
    stall_threshold=3,          # Iterations before pivot
)
```

## Best Practices

### 1. Always Use Context Manager
```python
# ✅ Good
messages = self.context_manager.build_messages(system_prompt)

# ❌ Bad - bypasses validation
messages = self.context_manager._messages
```

### 2. Handle Tool Errors Gracefully
```python
# ✅ Good
try:
    result = tool.execute(args)
except Exception as e:
    result = f"Error: {str(e)}"
    # Still add to context

# ❌ Bad - let error propagate
result = tool.execute(args)
```

### 3. Provide Context in Errors
```python
# ✅ Good
raise ValueError(f"Invalid parameter 'query': {query}")

# ❌ Bad - no context
raise ValueError("Invalid parameter")
```

### 4. Log Errors for Debugging
```python
# ✅ Good
print(f"\n【错误】API 调用失败: {str(api_error)}")
if cognitive_state:
    cognitive_state.add_uncertainty(f"API error: {type(api_error).__name__}")

# ❌ Bad - silent failure
pass
```

## Monitoring

Key metrics to monitor:

1. **Error Rate:** Frequency of API/tool errors
2. **Recovery Rate:** Percentage of errors recovered from
3. **Partial Answer Rate:** How often partial answers are generated
4. **Coherence Violations:** Orphaned tool_results detected

## Troubleshooting

### Issue: ValidationException about orphaned tool_results

**Cause:** Sliding window removed assistant message with tool_calls

**Solution:** Already handled by `_adjust_window_for_tool_pairs()` and `_ensure_message_coherence()`

**Debug:**
```python
messages = manager.build_messages(system_prompt)
for msg in messages:
    if msg.get("role") == "tool":
        print(f"Tool result: {msg.get('tool_call_id')}")
```

### Issue: Agent crashes on API errors

**Cause:** Unhandled exception in API call

**Solution:** Already handled by try-except in `solve()` loop

**Debug:**
```python
# Check if error handling is enabled
assert hasattr(agent, 'enable_cognitive')
```

### Issue: Tool errors crash iteration

**Cause:** Unhandled exception in tool execution

**Solution:** Already handled by per-tool try-except

**Debug:**
```python
# Test tool execution
try:
    result = agent._execute_tool_call(tool_call)
except Exception as e:
    print(f"Tool error: {e}")
```

## Performance Impact

- **Message validation:** O(n) where n = message count (typically < 100)
- **Window adjustment:** O(k) where k = messages to scan back (typically < 10)
- **Error handling:** Only executes on error path
- **Overall impact:** < 1ms per iteration on happy path

## Future Enhancements

1. **Exponential Backoff:** Implement exponential backoff for API retries
2. **Error Metrics:** Collect and analyze error patterns
3. **Smart Recovery:** Use LLM to suggest recovery strategies
4. **Circuit Breaker:** Temporarily disable failing tools
5. **Error Categorization:** Different handling for different error types
