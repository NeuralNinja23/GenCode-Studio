# app/core/auth_boundary.py
"""
Auth Boundary Lock - Phase-1 Stabilization

RULES:
1. User is a SYSTEM entity, not a domain entity
2. No /api/users CRUD router allowed
3. Only authentication endpoints: /auth/register, /auth/login, /auth/me
4. Password hashing ONLY in auth module
5. Domain entities reference user_id, never manage users

This eliminates:
- Security regressions (plain password storage)
- Router confusion (User vs domain entities)
- Marcus hard rejections for auth violations
"""
from typing import List, Optional


# ═══════════════════════════════════════════════════════════════════════════
# AUTH BOUNDARY CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

# System entities that should NEVER have domain CRUD routers
SYSTEM_ENTITIES = {"user", "users", "account", "accounts", "auth", "authentication"}

# Required authentication endpoints (immutable)
REQUIRED_AUTH_ENDPOINTS = {
    "register": "/auth/register",
    "login": "/auth/login", 
    "me": "/auth/me"
}

# Forbidden router patterns (will be rejected)
FORBIDDEN_ROUTER_PATTERNS = [
    "/api/users",
    "/users",
    "GET /users/",
    "POST /users/",
    "DELETE /users/",
    "router.get('/users')",
    "router.post('/users')",
]


def is_system_entity(entity_name: str) -> bool:
    """
    Check if an entity is a system entity (User, Auth, etc).
    
    System entities should NOT have domain CRUD routers.
    """
    normalized = entity_name.lower().strip()
    return normalized in SYSTEM_ENTITIES


def validate_entity_list(entities: List[str]) -> dict:
    """
    Validate that entity list doesn't violate auth boundary.
    
    Returns:
        {
            "valid": bool,
            "issues": List[str],
            "filtered_entities": List[str]  # Domain entities only
        }
    """
    issues = []
    domain_entities = []
    
    for entity in entities:
        if is_system_entity(entity):
            issues.append(f"'{entity}' is a system entity - should not have CRUD router")
        else:
            domain_entities.append(entity)
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "domain_entities": domain_entities
    }


def check_router_code_for_violations(router_code: str, entity_name: str) -> Optional[str]:
    """
    Check router code for auth boundary violations.
    
    Returns:
        None if valid, violation message if invalid
    """
    # Check if this is a User router (forbidden)
    if is_system_entity(entity_name):
        return f"FORBIDDEN: '{entity_name}' is a system entity. Only /auth endpoints allowed."
    
    # Check for forbidden patterns in code
    for pattern in FORBIDDEN_ROUTER_PATTERNS:
        if pattern.lower() in router_code.lower():
            return f"FORBIDDEN PATTERN: '{pattern}' detected. Use domain entities only."
    
    # Check for plain password handling (security violation)
    if "password" in router_code.lower():
        # Password should only appear in comparisons or hashing, not direct storage
        if "password:" in router_code or "password =" in router_code:
            # Check if it's being hashed
            if "hash_password" not in router_code and "bcrypt" not in router_code:
                return "SECURITY VIOLATION: Password must be hashed before storage"
    
    return None


def get_auth_guidance() -> str:
    """
    Get guidance text for proper auth implementation.
    
    This should be injected into prompts to prevent auth violations.
    """
    return """
═══════════════════════════════════════════════════════════════════════════
🔒 AUTH BOUNDARY RULES (IMMUTABLE)
═══════════════════════════════════════════════════════════════════════════

USER IS A SYSTEM ENTITY, NOT A DOMAIN ENTITY.

✅ ALLOWED:
- Domain entities: Task, Project, Lead, Contact, Product, Order, etc.
- Domain routers: /api/tasks, /api/projects, /api/leads, etc.
- Reference user_id in domain entities (e.g., task.user_id, project.owner_id)

❌ FORBIDDEN:
- /api/users router (NO CRUD for User)
- /users endpoints (use /auth instead)
- Plain password storage (ALWAYS hash passwords)
- Password handling in domain routers

✅ AUTHENTICATION ENDPOINTS (Fixed):
- POST /auth/register - Create new user account
- POST /auth/login - Authenticate user
- GET /auth/me - Get current user profile

🔐 PASSWORD RULES:
- Passwords ONLY in /auth endpoints
- ALWAYS hash before storage (use bcrypt/passlib)
- Domain routers NEVER touch passwords

EXAMPLE (CORRECT):
```python
# Domain router - references user, doesn't manage users
@router.post("/api/tasks")
async def create_task(task: TaskCreate, user_id: str = Depends(get_current_user)):
    new_task = Task(**task.dict(), user_id=user_id)  # Reference user_id
    await new_task.insert()
    return new_task
```

EXAMPLE (FORBIDDEN):
```python
# ❌ WRONG - This creates a User CRUD router
@router.post("/api/users")
async def create_user(user: UserCreate):
    new_user = User(**user.dict())  # ❌ Plain password storage
    await new_user.insert()
    return new_user
```

═══════════════════════════════════════════════════════════════════════════
"""


def should_skip_entity_for_router(entity_name: str) -> bool:
    """
    Determine if an entity should be skipped for router generation.
    
    Returns True for system entities (User, Auth, etc).
    """
    return is_system_entity(entity_name)
