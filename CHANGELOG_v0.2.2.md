# Friday v0.2.2 Changelog

## Release Date: 2026-04-23

## Summary
Switched from local LM Studio to Groq cloud LLM for better context handling, removed artificial context limits, fixed GitHub Actions tests, and added error handling for malformed tool calls.

---

## Major Changes

### 1. Switched to Groq as Default Provider

**Reason**: Local models couldn't handle the expanded context needed for complex tasks.

**Changes**:
- Default `MODEL_PROVIDER` changed from `lmstudio` to `groq`
- Updated `.env` and `.env.example` to reflect Groq as primary
- LM Studio and Ollama remain available as alternatives

**Configuration**:
```env
MODEL_PROVIDER=groq
GROQ_API_KEY=your_key_here
GROQ_MODEL=llama-3.3-70b-versatile
MAX_TOKENS=8000
```

### 2. Removed Context Limits

**Previous Limits** (designed for 4K context local models):
- `MAX_TOKENS`: 1000-2048
- `MAX_HISTORY_MESSAGES`: 12
- `MAX_INPUT_CHARS`: 9000
- `MAX_SYSTEM_PROMPT_CHARS`: 2800
- `MAX_SKILL_CONTEXT_CHARS`: 1800
- `RECURSION_LIMIT`: 25

**New Limits** (for Groq's 128K context):
- `MAX_TOKENS`: 8000
- `MAX_HISTORY_MESSAGES`: 50
- `MAX_INPUT_CHARS`: 100000
- `MAX_SYSTEM_PROMPT_CHARS`: 30000
- `MAX_SKILL_CONTEXT_CHARS`: 20000
- `RECURSION_LIMIT`: 50

**Benefits**:
- Can handle longer conversations
- More skill context can be loaded
- Larger system prompts with detailed instructions
- More tool calls per conversation

### 3. Fixed GitHub Actions Tests

**Problem**: Tests failing with `ModuleNotFoundError: No module named 'agent'`

**Root Cause**: Python path not set correctly in CI environment

**Solution**:
1. Added `pythonpath = .` to `pytest.ini`
2. Added `PYTHONPATH` environment variable to GitHub Actions workflow
3. Tests now run successfully in CI

**Files Modified**:
- `friday-backend/pytest.ini`
- `.github/workflows/backend-tests.yml`

### 4. Added Error Handling for Malformed Tool Calls

**Problem**: Groq's LLM sometimes generates malformed tool calls in XML format instead of JSON:
```
<function=execute_in_directory{"command": "...", "directory": "..."}></function>
```

**Solution**: Added try-catch in `agent_node` to:
1. Catch `tool_use_failed` errors from Groq
2. Log the error with full details
3. Return a helpful error message to the user
4. Allow the conversation to continue instead of crashing

**Error Handling**:
```python
try:
    response = await llm_with_tools.ainvoke(messages)
except Exception as e:
    if "tool_use_failed" in str(e):
        logger.error(f"Tool use failed: {e}")
        return error_message_to_user
    raise
```

---

## Files Modified

### Configuration Files
1. **friday-backend/.env**
   - Changed `MODEL_PROVIDER` to `groq`
   - Increased all context limits
   - Added missing environment variables

2. **friday-backend/.env.example**
   - Updated to show Groq as recommended provider
   - Documented new context limits
   - Reordered to show Groq first

3. **friday-backend/pytest.ini**
   - Added `pythonpath = .` for proper module resolution

### Code Files
4. **friday-backend/agent/model.py**
   - Changed default provider from `lmstudio` to `groq`
   - Increased default `MAX_TOKENS` from 1000 to 8000

5. **friday-backend/agent/nodes.py**
   - Added logger import
   - Added `re` import for regex matching
   - Added try-catch for malformed tool calls
   - Added error logging and user-friendly error messages
   - Increased default context limits

6. **friday-backend/agent/system_prompt.py**
   - Increased all default context limits (10x-30x larger)
   - Updated truncation messages to remove "local model" references

### CI/CD Files
7. **.github/workflows/backend-tests.yml**
   - Added `PYTHONPATH` environment variable to test steps
   - Ensures tests can find the `agent` module

### Documentation
8. **README.md**
   - Updated prerequisites to show Groq as recommended
   - Updated configuration table with new limits
   - Reordered provider priority

9. **CHANGELOG_v0.2.2.md** (this file)
   - Documented all changes

---

## Migration Guide

### For Existing Users

1. **Update your `.env` file**:
   ```bash
   # Change this line
   MODEL_PROVIDER=lmstudio
   
   # To this
   MODEL_PROVIDER=groq
   GROQ_API_KEY=your_groq_api_key_here
   ```

2. **Get a Groq API key**:
   - Visit https://console.groq.com/
   - Sign up for free account
   - Generate API key
   - Add to `.env`

3. **Optional: Keep using LM Studio**:
   ```env
   MODEL_PROVIDER=lmstudio
   # But note: you may hit context limits with complex tasks
   ```

4. **Update dependencies** (if needed):
   ```bash
   cd friday-backend
   pip install -r requirements.txt
   ```

---

## Testing

### Local Testing
```bash
cd friday-backend
. venv/Scripts/Activate.ps1  # Windows
# or
source venv/bin/activate      # Linux/Mac

# Run all tests
pytest tests/ -v

# Run with PYTHONPATH set
$env:PYTHONPATH="$PWD"
pytest tests/ -v
```

### CI Testing
Tests now pass in GitHub Actions with proper PYTHONPATH configuration.

---

## Known Issues

### 1. Groq Tool Call Formatting
**Issue**: Occasionally Groq generates malformed tool calls in XML format

**Workaround**: Error handler catches this and returns helpful message to user

**Status**: Monitoring - may need to adjust system prompt if it happens frequently

### 2. Context Window Usage
**Issue**: With larger limits, conversations can consume more tokens

**Impact**: May hit Groq rate limits faster on free tier

**Mitigation**: Limits are configurable via environment variables

---

## Performance Impact

### Positive
- ✅ Can handle much longer conversations
- ✅ More context for better decision making
- ✅ Can load larger skill documents
- ✅ Better handling of complex multi-step tasks

### Considerations
- ⚠️ Requires internet connection (Groq is cloud-based)
- ⚠️ May use more API tokens per request
- ⚠️ Slightly higher latency than local models (but faster than local on complex tasks)

---

## Rollback Instructions

If you need to revert to local LM Studio:

1. **Update `.env`**:
   ```env
   MODEL_PROVIDER=lmstudio
   MAX_TOKENS=2048
   MAX_HISTORY_MESSAGES=12
   MAX_INPUT_CHARS=9000
   RECURSION_LIMIT=25
   ```

2. **Restart Friday**:
   ```bash
   # Stop current instance
   # Start with updated config
   ```

3. **Note**: You'll have the old context limits back

---

## Next Steps

1. **Monitor Groq API usage** - Track token consumption
2. **Adjust limits if needed** - Fine-tune based on actual usage
3. **Test complex scenarios** - Verify improved context handling
4. **Update documentation** - Add Groq-specific tips and best practices

---

## Version Info

- **Version**: 0.2.2
- **Previous Version**: 0.2.1
- **Release Type**: Minor (configuration changes, no breaking API changes)
- **Compatibility**: Backward compatible with 0.2.x
