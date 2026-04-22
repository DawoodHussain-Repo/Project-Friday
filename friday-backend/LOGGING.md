# Friday Logging System

## Overview

Friday uses a structured logging system with automatic file rotation and multiple log levels to help diagnose issues and track system behavior.

## Log Files

All logs are stored in `friday-backend/logs/`:

| File | Purpose | Max Size | Backups | Content |
|------|---------|----------|---------|---------|
| `friday.log` | Main application log | 10MB | 5 | INFO level and above |
| `friday_errors.log` | Error-only log | 5MB | 3 | ERROR level only |

## Log Levels

| Level | Console | File | Use Case |
|-------|---------|------|----------|
| DEBUG | ❌ | ❌ | Development debugging (disabled by default) |
| INFO | ❌ | ✅ | Normal operations, state changes, performance metrics |
| WARNING | ✅ | ✅ | Potential issues, slow operations |
| ERROR | ✅ | ✅ | Failures, exceptions with stack traces |

## Log Format

```
YYYY-MM-DD HH:MM:SS | LEVEL    | module:function:line | message
```

Example:
```
2026-04-23 14:32:15 | INFO     | agent.graph:get_graph:158 | Compiling LangGraph state machine...
2026-04-23 14:32:16 | INFO     | agent.graph:_build_checkpointer:112 | AsyncSqliteSaver initialized successfully
2026-04-23 14:32:20 | INFO     | main:event_stream:125 | Starting chat stream | thread_id=abc123 | query_length=45
2026-04-23 14:32:21 | INFO     | main:event_stream:145 | Tool call | thread_id=abc123 | tool=web_search
2026-04-23 14:32:22 | INFO     | main:event_stream:165 | Tool result | thread_id=abc123 | tool=web_search | output_length=1234
2026-04-23 14:32:25 | INFO     | main:event_stream:185 | Final answer generated | thread_id=abc123 | length=567
2026-04-23 14:32:25 | INFO     | main:event_stream:189 | Performance: chat_stream[abc123] completed in 5234.56ms
```

## What Gets Logged

### Graph Operations
- Graph compilation and initialization
- Node execution (agent, tools, validate)
- Stream start/complete with duration
- Client disconnections

### Checkpoint Operations
- Database initialization
- Connection setup/teardown
- Save/load operations (when implemented)

### Tool Execution
- Tool calls with arguments
- Tool results with output length
- Tool failures with error messages

### Performance Metrics
- Operation durations
- Slow operation warnings (>1000ms)
- Token usage (when available)

### Errors
- Full exception stack traces
- Context information (thread_id, operation, state)
- Recovery attempts

## Using the Logger

### In New Modules

```python
from agent.logger import setup_logger

logger = setup_logger(__name__)

# Basic logging
logger.info("Operation completed successfully")
logger.warning("Potential issue detected")
logger.error("Operation failed", exc_info=True)  # Include stack trace

# Structured logging with context
logger.info(f"Processing request | user_id={user_id} | action={action}")
```

### Specialized Logging Functions

```python
from agent.logger import (
    log_function_call,
    log_performance,
    log_graph_event,
    log_tool_execution,
    log_checkpoint_operation,
    log_llm_call,
)

# Log function calls with parameters
log_function_call(logger, "process_data", user_id=123, action="create")

# Log performance metrics
import time
start = time.time()
# ... operation ...
duration_ms = (time.time() - start) * 1000
log_performance(logger, "data_processing", duration_ms)

# Log graph events
log_graph_event(logger, "start", "agent", thread_id, "recursion_limit=25")

# Log tool execution
log_tool_execution(
    logger,
    tool_name="web_search",
    args={"query": "python logging"},
    success=True,
    result="Found 10 results"
)

# Log checkpoint operations
log_checkpoint_operation(logger, "save", thread_id, checkpoint_id, success=True)

# Log LLM calls
log_llm_call(logger, "groq", "llama-3.3-70b", prompt_tokens=150, completion_tokens=50, duration_ms=234.5)
```

## Troubleshooting with Logs

### Finding Errors

```bash
# View recent errors
tail -f friday-backend/logs/friday_errors.log

# Search for specific error
grep "AsyncSqliteSaver" friday-backend/logs/friday_errors.log

# Find all errors for a specific thread
grep "thread_id=abc123" friday-backend/logs/friday.log | grep ERROR
```

### Performance Analysis

```bash
# Find slow operations
grep "Slow operation" friday-backend/logs/friday.log

# Track a specific conversation
grep "thread_id=abc123" friday-backend/logs/friday.log

# View all tool calls
grep "Tool call" friday-backend/logs/friday.log
```

### Debugging Graph Execution

```bash
# Follow graph execution for a thread
grep "thread_id=abc123" friday-backend/logs/friday.log | grep "Graph\|node"

# See all graph events
grep "Graph\[" friday-backend/logs/friday.log
```

## Log Rotation

Logs automatically rotate when they reach their size limit:
- Old logs are renamed with `.1`, `.2`, etc. suffixes
- Oldest logs are deleted when backup count is exceeded
- No manual intervention required

## Configuration

To change log levels or add custom handlers, edit `friday-backend/agent/logger.py`:

```python
# Change file log level
logger = setup_logger(__name__, level=logging.DEBUG)

# Change console log level (show INFO in console)
logger = setup_logger(__name__, console_level=logging.INFO)
```

## Best Practices

1. **Use structured logging**: Include context with `|` separators
   ```python
   logger.info(f"Operation | user={user} | status={status} | duration={ms}ms")
   ```

2. **Log state transitions**: When system state changes
   ```python
   logger.info(f"State transition | from={old_state} | to={new_state}")
   ```

3. **Include identifiers**: Always log thread_id, user_id, request_id
   ```python
   logger.info(f"Processing | thread_id={thread_id} | step={step}")
   ```

4. **Log errors with context**: Use `exc_info=True` for stack traces
   ```python
   try:
       risky_operation()
   except Exception as e:
       logger.error(f"Operation failed | context={ctx}", exc_info=True)
   ```

5. **Avoid logging sensitive data**: Never log passwords, API keys, tokens
   ```python
   # BAD
   logger.info(f"Auth | password={password}")
   
   # GOOD
   logger.info(f"Auth | user={user} | success={success}")
   ```

6. **Use appropriate levels**:
   - DEBUG: Detailed diagnostic info (disabled in production)
   - INFO: Normal operations, state changes
   - WARNING: Unexpected but handled situations
   - ERROR: Failures requiring attention

## Monitoring

For production deployments, consider:
- Log aggregation (ELK stack, Splunk, CloudWatch)
- Alerting on ERROR patterns
- Performance metric dashboards
- Log retention policies
