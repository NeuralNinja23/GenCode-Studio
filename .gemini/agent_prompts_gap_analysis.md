# Agent Prompts Gap Analysis
**Generated**: 2025-12-08T17:44:30+05:30

## Executive Summary

After auditing all 4 agent prompts against the current backend implementation, templates, and infrastructure, I've identified **28 critical gaps** that cause workflow failures and output quality issues.

---

## 🔴 Critical Gaps by Agent

### **DEREK (Implementation Engineer)**

#### Missing Backend Testing Information (CRITICAL)
1. ❌ **No mention of pytest-asyncio marker**: Derek doesn't know to use `@pytest.mark.anyio`
2. ❌ **No conftest.py pattern**: Doesn't know there's auto-fixture for client and DB setup
3. ❌ **No Faker usage guidance**: Library is in template but Derek doesn't know when/how to use it
4. ❌ **Wrong fixture usage**: Instructs `AsyncClient(app=app)` instead of using provided `client` fixture
5. ❌ **No test database awareness**: Doesn't know tests run on `test_database` not production DB

#### Missing Version Information (HIGH)
6. ❌ **No specific library versions**: Should reference requirements.example.txt versions
7. ❌ **No pytest-asyncio version**: Missing `pytest-asyncio==0.24.0`
8. ❌ **No aiohttp version awareness**: Template has `aiohttp==3.11.8`

#### Missing Template Information (HIGH)
9. ❌ **Incomplete requirements.txt guidance**: Missing Faker, pytest-asyncio, aiohttp
10. ❌ **No reference to conftest.py template**: Agents recreate what already exists

#### Backend Patterns (MEDIUM)
11. ❌ **No lifespan pattern explained**: Modern FastAPI startup with `@asynccontextmanager`
12. ❌ **No CORS guidance**: When to add, when not to add
13. ❌ **Incomplete import rule**: Says `from app.main import app` but not WHY (Docker context)

---

### **LUNA (QA Engineer)**

#### Critical Testing Gaps (CRITICAL)
14. ❌ **No anyio pytest marker**: Doesn't know to use `@pytest.mark.anyio` for async backend tests
15. ❌ **No conftest.py fixture usage**: Creates its own client instead of using provided fixture
16. ❌ **No Faker guidance**: Doesn't know Faker is available for test data generation
17. ❌ **Wrong test database**: May use production DB instead of `test_database`

#### Frontend Testing Gaps (HIGH)
18. ❌ **Incomplete Playwright config knowledge**: Knows example exists but not the full pattern
19. ❌ **No sandbox-specific guidance**: Tests run in Docker, baseURL handling is critical

#### Missing Template Awareness (MEDIUM)
20. ❌ **Doesn't know conftest.py provides auto-setup**: Recreates DB initialization in tests

---

### **VICTORIA (Architect)**

#### Architecture Completeness (HIGH)
21. ❌ **No conftest.py in architecture**: Doesn't plan for the test infrastructure that exists
22. ❌ **No pytest-asyncio requirement**: Doesn't include in backend dependencies
23. ❌ **No Faker in test data strategy**: Missing from architecture planning
24. ❌ **No lifespan pattern specification**: Doesn't specify modern FastAPI startup pattern

#### Missing Backend Patterns (MEDIUM)
25. ❌ **No test database separation**: Doesn't specify `test_database` vs production
26. ❌ **Incomplete CORS guidance**: Doesn't specify when/how to configure CORS

---

### **MARCUS (Code Reviewer)**

#### Review Checklist Gaps (HIGH)
27. ❌ **No check for pytest.mark.anyio**: Won't catch missing async test markers
28. ❌ **No check for conftest.py usage**: Won't catch agents recreating fixtures
29. ❌ **No Faker validation**: Won't check if test data generation uses Faker
30. ❌ **No test database check**: Won't verify tests use `test_database`

#### Missing Quality Criteria (MEDIUM)
31. ❌ **No lifespan pattern validation**: Won't check for modern FastAPI startup
32. ❌ **No version compatibility check**: Doesn't validate against requirements.example.txt

---

## 📋 Template vs Agent Knowledge

### Backend Templates (What Exists)
```
backend/
├── reference/
│   └── requirements.example.txt  ← Has ALL dependencies including Faker
├── tests/
│   └── conftest.py  ← Provides client fixture, DB setup, anyio_backend
└── pytest.ini  ← Configures pytest-asyncio mode
```

### What Agents Currently Know
- ✅ Requirements template exists
- ✅ conftest.py exists  
- ❌ **Don't know conftest.py provides fixtures**
- ❌ **Don't know how to use the fixtures**
- ❌ **Don't know Faker is available**
- ❌ **Don't know pytest-asyncio patterns**

---

## 🔧 Required Dependencies (From Templates)

### Backend (requirements.example.txt)
```txt
# Core
fastapi==0.115.5
uvicorn[standard]==0.32.1
pydantic==2.9.2

# Database
motor==3.6.0
beanie==1.26.0
pymongo>=4.9.0

# Testing ← CRITICAL SECTION
pytest==8.3.3
pytest-asyncio==0.24.0  ← Missing from agent knowledge
aiohttp==3.11.8         ← Missing from agent knowledge
Faker==25.2.0           ← Missing from agent knowledge
httpx==0.27.2

# Utils
python-dotenv==1.0.1
typing-extensions==4.12.2
```

### Frontend (package.example.json)
```json
{
  "devDependencies": {
    "@playwright/test": "1.57.0",  ← Agents know this
    "tailwindcss-animate": "^1.0.7" ← Missing from some contexts
  }
}
```

---

## 🎯 Backend Test Pattern (conftest.py)

### What conftest.py Provides (Agents DON'T know this!)
```python
@pytest.fixture(scope="session")
def anyio_backend():
    """Use asyncio backend for async tests."""
    return "asyncio"

@pytest_asyncio.fixture
async def client():
    """HTTP client for testing FastAPI - AUTO-PROVIDED!"""
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    """Auto-initialize test DB before EACH test - AUTO-RUN!"""
    # Drops collections, re-inits Beanie
    # Ensures test isolation
```

### What Derek Currently Generates (WRONG!)
```python
# Derek recreates what conftest.py already provides!
@pytest.fixture
async def async_client():  # ← WRONG: conftest provides 'client'
    client = AsyncIOMotorClient(...)  # ← WRONG: conftest does this
    db = client["test_db"]  # ← WRONG: should use env var
    await init_beanie(...)  # ← WRONG: conftest auto-runs this
```

### What Derek SHOULD Generate (CORRECT!)
```python
import pytest
from faker import Faker  # ← Now available!

fake = Faker()

@pytest.mark.anyio  # ← CRITICAL: async marker
async def test_create_item(client):  # ← Use provided fixture
    """Test item creation with realistic data."""
    item_data = {
        "title": fake.sentence(nb_words=3),
        "description": fake.text(max_nb_chars=100)
    }
    response = await client.post("/api/items/", json=item_data)
    assert response.status_code == 201
```

---

## 🚨 Impact Assessment

### Current Failure Modes (Before Fixes)
1. **Tests don't run**: Missing `@pytest.mark.anyio` → "RuntimeError: no running event loop"
2. **DB conflicts**: Tests recreate DB setup → race conditions, connection leaks
3. **Import errors**: Missing `from faker import Faker` → ModuleNotFoundError
4. **Wrong DB**: Tests hit production DB → test data pollution
5. **Fixture errors**: Tests create own client → conftest auto-setup conflicts

### After Fixes (Expected)
1. ✅ Tests use `@pytest.mark.anyio` marker automatically
2. ✅ Tests use provided `client` fixture (no recreation)
3. ✅ Tests use `Faker` for realistic test data
4. ✅ Tests run on `test_database` (isolation guaranteed)
5. ✅ Tests pass on first attempt (no retry loops)

---

## 📊 Fix Priority

### P0 - CRITICAL (Blocks testing)
1. Add pytest.mark.anyio to Derek, Luna, Marcus
2. Add conftest.py fixture usage to Derek, Luna
3. Add Faker to Derek's backend test generation
4. Add test database awareness to all agents

### P1 - HIGH (Quality issues)
5. Add lifespan pattern to Derek, Victoria
6. Add version-specific guidance to Derek
7. Add conftest.py validation to Marcus
8. Update Luna's Playwright config knowledge

### P2 - MEDIUM (Consistency)
9. Add CORS guidance to Derek, Victoria
10. Improve import rule explanation in Derek
11. Add template awareness to all agents

---

## 🔄 Next Steps

I will now update all 4 agent prompts with the missing critical information:

1. **Derek.py** - Add testing patterns, Faker usage, conftest.py awareness
2. **Luna.py** - Add anyio marker, fixture usage, Faker for backends
3. **Victoria.py** - Add complete test infrastructure to architecture
4. **Marcus.py** - Add validation for new testing patterns

Each update will be surgical and focused on the critical gaps identified above.
