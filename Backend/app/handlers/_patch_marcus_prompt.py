# Patch to add entity classification guidance to Marcus's contracts prompt
from pathlib import Path

file_path = Path(r'C:\Users\JARVIS\Desktop\Project GenCode\GenCode Studio\Backend\app\handlers\contracts.py')
content = file_path.read_text(encoding='utf-8')

# Find the insertion point (before "YOUR TASK")
old_section = '''═══════════════════════════════════════════════════════
📋 YOUR TASK
═══════════════════════════════════════════════════════

Create `contracts.md` that defines:

1. **Data Models** - Match the shapes in mock.js EXACTLY'''

new_section = '''═══════════════════════════════════════════════════════
🎯 ENTITY CLASSIFICATION RULES (CRITICAL!)
═══════════════════════════════════════════════════════

Before creating API endpoints, you MUST classify each entity correctly:

**AGGREGATE Entities** - Create full CRUD endpoints (/api/X):
✅ Appears as TOP-LEVEL array export in mock.js
   Examples: export const mockTasks = [...], export const mockUsers = [...]
✅ Has independent lifecycle (can be created/updated/deleted on its own)
✅ Needs own MongoDB collection
✅ Has unique ID at root level

**EMBEDDED Entities** - DO NOT create endpoints:
🔒 Appears ONLY as nested object or array INSIDE another entity
   Examples: assignee: {{name, avatar}}, tags: [{{name, color}}]
🔒 No top-level export in mock.js
🔒 Part of parent entity, no independent existence
🔒 No separate API routes needed

**CLASSIFICATION EXAMPLES FROM MOCK.JS:**

```javascript
// Example 1: Task is AGGREGATE (top-level export)
export const mockTasks = [
  {{
    id: "1",
    title: "Task 1",
    assignee: {{name: "John", avatar: "..."}},  // ← Assignee is EMBEDDED
    tags: [{{name: "urgent", color: "red"}}]    // ← Tag is EMBEDDED
  }}
]

// Result:
// ✅ Task: AGGREGATE → Create /api/tasks endpoints
// 🔒 Assignee: EMBEDDED → DO NOT create /api/assignees
// 🔒 Tag: EMBEDDED → DO NOT create /api/tags
```

**HOW TO ANALYZE mock.js:**
1. Find all "export const mock___" declarations
2. Those are AGGREGATE entities (create endpoints)
3. Any nested objects/arrays are EMBEDDED (no endpoints)

═══════════════════════════════════════════════════════
📋 YOUR TASK
═══════════════════════════════════════════════════════

**STEP 1: CLASSIFY ENTITIES (MANDATORY OUTPUT)**

Before writing any endpoints, include this section in contracts.md:

## Entity Classification

For each entity found in mock.js, list:
- **Name**: Entity name (e.g., Task, User, Assignee)
- **Type**: AGGREGATE or EMBEDDED
- **Evidence**: Why? (e.g., "top-level export mockTasks" or "nested in Task.assignee")

Example:
```markdown
## Entity Classification

- **Task**
  - Type: AGGREGATE
  - Evidence: Top-level export (mockTasks = [...])
  - Endpoints: Will create /api/tasks

- **Assignee**
  - Type: EMBEDDED
  - Evidence: Nested object in Task.assignee
  - Endpoints: None (nested data only)
```

⚠️ This classification will be VALIDATED by the system.
Incorrect classifications will be automatically corrected.

**STEP 2: CREATE ENDPOINTS (ONLY FOR AGGREGATE ENTITIES)**

Create `contracts.md` that defines:

1. **Entity Classification** (see above - MANDATORY!)

2. **Data Models** - Match the shapes in mock.js EXACTLY'''

content = content.replace(old_section, new_section)

file_path.write_text(content, encoding='utf-8')
print("✅ Enhanced Marcus's prompt with entity classification guidance!")
print("   - Added AGGREGATE vs EMBEDDED rules")
print("   - Added mock.js analysis instructions")
print("   - Mandatory Entity Classification section in output")
print("   - Classification will be validated by code")
