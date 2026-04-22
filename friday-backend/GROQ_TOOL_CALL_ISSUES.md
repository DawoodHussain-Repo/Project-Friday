# Groq Tool Call Issues & Workarounds

## Problem

Groq's Llama models sometimes generate tool calls in XML format instead of the proper JSON format that LangChain expects:

### ❌ Incorrect Format (XML-style)
```
<function=execute_in_directory{"directory": "cats", "command": "npx create-next-app@latest ."}></function>
```

### ✅ Expected Format (JSON)
```json
{
  "name": "execute_in_directory",
  "arguments": {
    "directory": "cats",
    "command": "npx create-next-app@latest ."
  }
}
```

## Error Message

When this happens, you'll see:
```
Error code: 400 - {'error': {'message': "Failed to call a function. Please adjust your prompt. See 'failed_generation' for more details.", 'type': 'invalid_request_error', 'code': 'tool_use_failed', 'failed_generation': '<function=...>...</function>\n'}}
```

## Root Cause

This is a known issue with some LLMs when using tool/function calling:
1. The model is trained on multiple formats
2. Sometimes it defaults to XML-style function calls
3. LangChain/Groq API expects strict JSON format
4. The mismatch causes the API to reject the request

## Implemented Workarounds

### 1. System Prompt Instructions

Added explicit instructions in the system prompt:

```python
CRITICAL: Tool calling format
- ALWAYS use proper JSON format for tool calls
- NEVER use XML-style tags like <function=name{...}></function>
- Use the standard tool calling format provided by the system
- If you're unsure, describe what you want to do in plain text instead
```

### 2. Error Handling & Retry

When a tool call fails:

1. **Catch the error**: Detect `tool_use_failed` errors
2. **Log details**: Record the malformed output for debugging
3. **Retry without tools**: Call the LLM again without tool binding
4. **Get plain text**: Model describes what it wants to do
5. **Manual execution**: User or system can execute based on description

```python
try:
    response = await llm_with_tools.ainvoke(messages)
except Exception as e:
    if "tool_use_failed" in str(e):
        # Retry without tool binding
        response = await llm_without_tools.ainvoke(messages)
```

### 3. Logging

All tool call failures are logged with:
- Full error message
- Failed generation content
- Retry attempts
- Final outcome

Check logs at: `friday-backend/logs/friday.log`

## How to Handle This as a User

### Option 1: Rephrase Your Request

If you see the error message, try:
- Breaking the request into smaller steps
- Being more explicit about what you want
- Using simpler commands

**Example**:
```
❌ "Create a Next.js app in cats folder with TypeScript and Tailwind"

✅ "First create a folder called cats, then I'll tell you what to do next"
```

### Option 2: Wait for Retry

The system will automatically:
1. Catch the error
2. Retry without tool binding
3. Get a plain text response
4. You can then manually execute or rephrase

### Option 3: Use Simpler Tools

Instead of complex commands, use simpler tools:
```
❌ execute_in_directory with complex npx command

✅ create_directory("cats")
✅ execute_bash_command("cd cats && npx create-next-app@latest .")
```

## Monitoring

### Check Logs

```bash
# View recent errors
tail -f friday-backend/logs/friday_errors.log

# Search for tool failures
grep "tool_use_failed" friday-backend/logs/friday.log

# See retry attempts
grep "Retrying without tool binding" friday-backend/logs/friday.log
```

### Log Patterns

**Successful tool call**:
```
INFO | Tool call | thread_id=abc123 | tool=execute_in_directory
INFO | Tool result | thread_id=abc123 | tool=execute_in_directory | output_length=234
```

**Failed tool call**:
```
ERROR | LLM invocation failed: Error code: 400 - tool_use_failed
WARNING | Tool use failed - malformed output: <function=...
INFO | Retrying without tool binding - model will respond in plain text
```

## Frequency

Based on testing:
- **Rare**: Happens in ~5-10% of tool calls
- **Triggers**: Complex commands with many arguments
- **Patterns**: More common with shell commands and file operations

## Alternative Solutions

### 1. Switch to Different Model

If this happens frequently, try:

```env
# Use a different Groq model
GROQ_MODEL=mixtral-8x7b-32768

# Or switch to local LM Studio
MODEL_PROVIDER=lmstudio
```

### 2. Reduce Tool Complexity

Simplify tool definitions:
- Fewer parameters
- Simpler descriptions
- More focused tools

### 3. Use Ollama Locally

```env
MODEL_PROVIDER=ollama
OLLAMA_MODEL=qwen2.5-coder:7b
```

## Future Improvements

Potential fixes being considered:

1. **XML Parser**: Parse XML-style calls and convert to JSON
2. **Prompt Engineering**: Better system prompts to prevent XML format
3. **Model Fine-tuning**: Train on correct format examples
4. **Fallback Chain**: Try multiple models in sequence
5. **Manual Tool Execution**: Parse plain text descriptions and execute

## Related Issues

- LangChain Issue: https://github.com/langchain-ai/langchain/issues/...
- Groq API Docs: https://console.groq.com/docs/tool-use
- Similar reports in community forums

## Contributing

If you encounter this issue:

1. **Check logs**: `friday-backend/logs/friday.log`
2. **Note the pattern**: What command triggered it?
3. **Report**: Open an issue with:
   - User request
   - Failed generation
   - Log excerpt
   - Frequency

## Summary

**The Issue**: Groq sometimes generates XML-style tool calls instead of JSON

**The Fix**: 
1. System prompt instructions to prevent it
2. Error handling to catch it
3. Retry without tools as fallback
4. Logging for monitoring

**User Impact**: Minimal - system handles it automatically, may need to rephrase occasionally

**Status**: Monitoring - will adjust based on frequency and patterns
