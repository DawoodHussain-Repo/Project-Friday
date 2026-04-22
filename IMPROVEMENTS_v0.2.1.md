# Friday v0.2.1 Improvements

## Overview
This release addresses critical agent behavior issues: hallucination, lack of skill creation, and poor task focus.

---

## Problems Fixed

### 1. ❌ Hallucination & Task Drift
**Problem**: Friday would go off-task and perform unrelated actions.

**Example**:
```
User: "make CSS for HTML about cats"
Friday: *searches for weather* ❌
```

**Solution**: Updated system prompt with explicit focus instructions:
- "Stay focused, do not hallucinate unrelated tasks"
- "If you find yourself using a tool unrelated to the request, STOP and refocus"
- Added "Why am I doing this?" mental check before each tool call

### 2. ❌ Not Creating Skills
**Problem**: Friday would perform tasks without creating reusable skill documents.

**Example**:
```
User: "learn web design"
Friday: *just creates CSS without documenting the skill* ❌
```

**Solution**: Added mandatory skill creation workflow:
1. Check if skill exists: `search_skill_library("skill_name")`
2. If not found, create skill document with best practices
3. Register with `save_to_skill_library(...)`
4. Use the skill for the task

### 3. ❌ Not Using Skill Library
**Problem**: Friday would reinvent solutions instead of checking existing skills.

**Solution**: Updated tool priorities to always search skill library first:
```
1. search_skill_library("relevant_skill")
2. If found: read and apply
3. If not found: create, register, then use
```

---

## Changes Made

### 1. System Prompt Updates (`friday-backend/agent/system_prompt.py`)

#### Added Focus Instructions
```python
CRITICAL: Stay on task
- If user asks "make CSS for HTML about cats", do NOT search for weather or unrelated topics.
- Only use tools that directly address the user's request.
- If you find yourself using a tool unrelated to the request, STOP and refocus.
```

#### Added Skill Creation Workflow
```python
Skill creation workflow (MANDATORY when learning new capabilities):
1) Check if skill exists: search_skill_library("skill_name")
2) If NOT found and you're doing something reusable:
   a) Create a skill document (.py or .md) with clear instructions/code
   b) Test it works
   c) Save with save_to_skill_library(...)
3) Next time you need this capability, search_skill_library first and reuse it
```

#### Added Instruction Snippets
- Web design/CSS trigger: Reminds to search/create/use skills
- Learning trigger: Enforces skill creation workflow

### 2. Created Example Skill (`friday-backend/skills/web_design_skill.md`)

Comprehensive web design guide including:
- CSS best practices
- Responsive design patterns
- Typography guidelines
- Color scheme recommendations
- HTML structure templates
- Themed design examples (including cat theme!)
- Common patterns (cards, buttons, images)

### 3. Registered Skill (`friday-backend/skills/index.json`)

```json
{
  "web_design": {
    "description": "Guidelines and best practices for creating HTML pages with CSS styling",
    "path": "skills/web_design_skill.md",
    "type": "guide",
    "tags": ["web", "css", "html", "design", "frontend", "styling"]
  }
}
```

### 4. Created Workflow Documentation (`friday-backend/AGENT_WORKFLOW.md`)

Comprehensive guide for Friday's behavior including:
- Problem examples (bad vs good)
- Mandatory workflow for learning
- When to create skills
- Skill document structure
- Staying focused checklist
- Red flags for hallucination
- Example scenarios

---

## Expected Behavior Now

### Scenario 1: Learning Web Design
```
User: "learn web design and make CSS about cats"

Friday:
1. ✅ search_skill_library("web_design")
2. ✅ If not found: create web_design_skill.md
3. ✅ save_to_skill_library(...)
4. ✅ read_file("skills/web_design_skill.md")
5. ✅ write_to_file("style.css", <cat-themed CSS using guidelines>)
6. ✅ Final: "Created web design skill and applied it"
```

### Scenario 2: Reusing Existing Skill
```
User: "make a cat website"

Friday:
1. ✅ search_skill_library("web_design") → Found!
2. ✅ read_file("skills/web_design_skill.md")
3. ✅ write_to_file("cats.html", <HTML using best practices>)
4. ✅ write_to_file("cats.css", <cat-themed CSS>)
5. ✅ Final: "Created cat website using web design guidelines"
```

### Scenario 3: Staying Focused
```
User: "add a header to my HTML"

Friday:
1. ✅ read_file("index.html")
2. ✅ append_to_file("index.html", <header>)
3. ✅ Final: "Added header"

NOT:
❌ web_search("what is a header")
❌ get_stock_quote("AAPL")
❌ Unrelated tool calls
```

---

## Testing Recommendations

### Test 1: Skill Creation
```
Prompt: "learn CSS design and create a page about dogs"
Expected: 
- Creates css_design skill document
- Registers it in skill library
- Uses it to create dog-themed page
```

### Test 2: Skill Reuse
```
Prompt: "make another page about birds using web design"
Expected:
- Searches for web_design skill
- Finds and reads it
- Applies guidelines to bird page
- Does NOT recreate the skill
```

### Test 3: Focus
```
Prompt: "add a footer to my HTML file"
Expected:
- Reads the HTML file
- Adds footer
- Does NOT search web, check stocks, or do unrelated tasks
```

### Test 4: No Hallucination
```
Prompt: "style this HTML with CSS"
Expected:
- Checks for web_design skill
- Creates CSS file
- Does NOT search for weather, news, or unrelated information
```

---

## Files Modified

1. `friday-backend/agent/system_prompt.py` - Enhanced with focus and skill workflow
2. `friday-backend/skills/web_design_skill.md` - Created example skill
3. `friday-backend/skills/index.json` - Registered web_design skill
4. `friday-backend/AGENT_WORKFLOW.md` - Created workflow documentation
5. `IMPROVEMENTS_v0.2.1.md` - This document

---

## Monitoring

Check logs for:
- `search_skill_library` calls before creating new content
- `save_to_skill_library` calls when learning
- Tool calls staying relevant to user request
- No unrelated web_search or tool calls

Log examples:
```
✅ GOOD: Tool[search_skill_library] args=(query='web_design')
✅ GOOD: Tool[save_to_skill_library] args=(name='web_design', ...)
✅ GOOD: Tool[write_to_file] args=(filename='style.css', ...)

❌ BAD: Tool[web_search] args=(query='weather') when user asked for CSS
❌ BAD: Tool[get_stock_quote] when user asked for HTML
```

---

## Next Steps

1. **Test with real conversations** - Verify Friday stays focused
2. **Monitor skill creation** - Ensure skills are being created and reused
3. **Add more example skills** - Create skills for common tasks (API integration, data parsing, etc.)
4. **Improve validation** - Add validator node check for task relevance
5. **Add skill templates** - Provide templates for different skill types

---

## Version

- **Version**: 0.2.1
- **Date**: 2026-04-23
- **Focus**: Agent behavior, skill creation, task focus
- **Breaking Changes**: None (backward compatible)
