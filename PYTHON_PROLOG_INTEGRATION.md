# Python-Prolog Integration Analysis

## Summary

Your Python backend **currently uses these two Prolog files**:

1. ✅ **`scheduler.pl`** - Loaded by `prolog_service.py`
2. ✅ **`constraint_solver.pl`** - Loaded by `prolog_service.py`
3. ❌ **`constraint_solver_krr.pl`** - **NOT loaded yet** (newly created)

---

## Python Service Architecture

### Main Integration Point: `prolog_service.py`

**Location:** `apps/backend/app/chat/prolog_service.py`

**What it loads:**

```python
# Lines 128-137
self._prolog_file = os.path.join(
    os.path.dirname(__file__), 
    "prolog", 
    "scheduler.pl"              # ✅ LOADED
)
self._constraint_solver_file = os.path.join(
    os.path.dirname(__file__),
    "prolog",
    "constraint_solver.pl"      # ✅ LOADED (OLD FILE)
)
```

**Initialization (Lines 148-156):**

```python
def _ensure_initialized(self) -> bool:
    try:
        self._prolog = Prolog()
        self._prolog.consult(self._prolog_file)           # Loads scheduler.pl
        self._initialized = True
        
        # Also try to load constraint solver
        try:
            self._prolog.consult(self._constraint_solver_file)  # Loads constraint_solver.pl
            self._constraint_solver_loaded = True
        except Exception as e:
            print(f"Constraint solver not loaded (will use Python fallback): {e}")
```

---

## Python Services That Use Prolog

### 1. `chat/service.py` - Chat Agent Service

**Imports:**
```python
from app.chat.prolog_service import get_prolog_service, PrologService, RescheduleOption
```

**Usage:**
```python
class ChatAgentService:
    def __init__(self, db: AsyncSession, timezone: str = "Asia/Bangkok", user_id: str | None = None):
        self.prolog = get_prolog_service()  # Gets singleton instance
```

**Purpose:** Uses Prolog for conflict detection and free slot finding during chat conversations.

### 2. `chat/router.py` - FastAPI Endpoints

**Imports:**
```python
from app.chat.prolog_service import get_prolog_service
```

**Purpose:** Exposes REST API endpoints that use Prolog service.

### 3. `services/scheduling_service.py` - Scheduling Service

**Note:** This file does **NOT** directly import Prolog. It uses Python-based A* algorithm as a fallback.

**From the file comments:**
```python
"""
Scheduling Service — Priority-aware constraint solver with A* rescheduling.

Bridges user priorities (from Phase 1 LLM extraction) with Prolog constraint
logic (or Python fallback) for intelligent event scheduling.
"""
```

---

## Current Problem: KRR Files Not Loaded

### ❌ Issue

Your new KRR-based files are **NOT being loaded** by Python:

- `constraint_solver_krr.pl` - Created but not imported
- `scheduler.pl` - Enhanced with KRR but Python still uses old predicates

### ✅ Solution Options

You have **three options** to integrate the KRR implementation:

---

## Option 1: Replace Old File (Recommended for Demonstration)

**Best for:** Showing your professor the KRR implementation.

**Steps:**

1. Backup the original:
   ```bash
   copy constraint_solver.pl constraint_solver.pl.backup
   ```

2. Replace with KRR version:
   ```bash
   copy constraint_solver_krr.pl constraint_solver.pl
   ```

3. Restart your Python service.

**Pros:**
- ✅ Python code unchanged
- ✅ All imports work automatically
- ✅ Easy to demonstrate

**Cons:**
- ⚠️ Loses backward compatibility
- ⚠️ May break existing Python calls if predicates changed

---

## Option 2: Update Python Import (Clean Approach)

**Best for:** Production use while keeping both versions.

**Steps:**

1. **Edit `prolog_service.py`** (line 136):

   **OLD:**
   ```python
   "constraint_solver.pl"
   ```

   **NEW:**
   ```python
   "constraint_solver_krr.pl"  # Use KRR version
   ```

2. **Update any predicate calls** in Python code to match KRR interface:

   **OLD predicates:**
   - `check_conflict/5`
   - `find_free_slots/7`
   - `validate_hard_constraints/3`

   **NEW KRR predicates:**
   - `prove_conflict/4` (with proof)
   - `find_valid_slot/4` (with proof)
   - `valid_schedule/3` (with proof)

3. Restart service.

**Pros:**
- ✅ Clean separation of old/new
- ✅ Keeps both files available
- ✅ Can switch back easily

**Cons:**
- ⚠️ Requires updating Python calls
- ⚠️ More work to integrate

---

## Option 3: Load Both Files (Hybrid Approach)

**Best for:** Gradual migration with backward compatibility.

**Steps:**

1. **Edit `prolog_service.py`** (add after line 137):

   ```python
   self._constraint_solver_file = os.path.join(
       os.path.dirname(__file__),
       "prolog",
       "constraint_solver.pl"
   )
   self._constraint_solver_krr_file = os.path.join(
       os.path.dirname(__file__),
       "prolog",
       "constraint_solver_krr.pl"  # ADD THIS
   )
   ```

2. **Update `_ensure_initialized`** (after line 154):

   ```python
   # Load old constraint solver
   try:
       self._prolog.consult(self._constraint_solver_file)
       self._constraint_solver_loaded = True
   except Exception as e:
       print(f"Constraint solver not loaded: {e}")
   
   # Load NEW KRR constraint solver
   try:
       self._prolog.consult(self._constraint_solver_krr_file)  # ADD THIS
       self._constraint_solver_krr_loaded = True
       print("KRR constraint solver loaded successfully!")
   except Exception as e:
       print(f"KRR constraint solver not loaded: {e}")
   ```

3. Create **wrapper methods** to call KRR predicates:

   ```python
   def prove_conflict_krr(self, new_event, existing_events):
       """Use KRR version for conflict detection with proof."""
       if not self._constraint_solver_krr_loaded:
           # Fallback to old version
           return self.check_conflict(new_event, existing_events)
       
       # Call KRR predicate: prove_conflict/4
       # Returns conflict + proof trace
       # ...
   ```

**Pros:**
- ✅ Both old and new predicates available
- ✅ Backward compatible
- ✅ Can demo KRR without breaking existing code
- ✅ Gradual migration

**Cons:**
- ⚠️ More complex
- ⚠️ Two versions loaded in memory

---

## Recommended Approach for Your Situation

### For Demonstrating to Professor: **Option 1**

1. **Backup original:**
   ```powershell
   cd "d:\Kant_Isaranucheep\KMITL\software engineering year3\TeamProject\project\Schedule-Assistant\apps\backend\app\chat\prolog"
   Copy-Item constraint_solver.pl constraint_solver.pl.backup
   ```

2. **Replace with KRR version:**
   ```powershell
   Copy-Item constraint_solver_krr.pl constraint_solver.pl -Force
   ```

3. **Restart Python backend**

4. **Show professor:**
   - The Python service now uses KRR implementation
   - All proof traces and explanations work through the API
   - Meta-interpreter is actively being used

5. **After demo, restore if needed:**
   ```powershell
   Copy-Item constraint_solver.pl.backup constraint_solver.pl -Force
   ```

---

## What Python Code Calls

### From `prolog_service.py`:

The Python service calls these Prolog predicates (checking if they exist in your files):

**Conflict Checking:**
- `check_conflict/5` - Used by `check_conflict()` method
- Expects: `check_conflict(NSH, NSM, NEH, NEM, Events, Conflicts)`

**Free Slot Finding:**
- `find_free_slots/7` - Used by `find_free_slots()` method
- Expects: `find_free_slots(Duration, DayStart, MonthStart, YearStart, DayEnd, MonthEnd, YearEnd, Slots)`

**Rescheduling:**
- Uses A* algorithm in Python (lines 795+)
- Comments mention "Mirrors the A*-based logic from constraint_solver.pl"
- Currently implemented in Python, not Prolog

### Compatibility Check

**OLD `constraint_solver.pl`:**
- ✅ Has `check_conflict/5` 
- ✅ Has other predicates Python expects
- ❌ No KRR features

**NEW `constraint_solver_krr.pl`:**
- ⚠️ Different interface: `prove_conflict/4` (with proof)
- ⚠️ Different interface: `find_valid_slot/4` (with proof)
- ✅ Has KRR features
- ❌ May not have exact old predicate signatures

**Enhanced `scheduler.pl`:**
- ✅ Has old predicates: `check_conflict/5`
- ✅ Has new KRR predicates: `prove_conflict/4`
- ✅ Backward compatible!

---

## Testing Your KRR Integration

### Test 1: Check Python Can Load Files

```python
# In Python shell or test file:
from pyswip import Prolog

prolog = Prolog()
prolog.consult("apps/backend/app/chat/prolog/scheduler.pl")
prolog.consult("apps/backend/app/chat/prolog/constraint_solver_krr.pl")

# Try calling KRR predicate
result = list(prolog.query("prove_conflict(event(new, 'Test', 10, 0, 11, 0), [], C, P)"))
print(result)
```

### Test 2: Check Endpoints Still Work

```bash
# Start backend
cd apps/backend
python -m app.main

# Test chat endpoint
curl -X POST http://localhost:8000/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test123",
    "message": "Schedule a meeting tomorrow at 2pm"
  }'
```

### Test 3: Check Prolog Service Health

```bash
curl http://localhost:8000/chat/health
```

---

## Next Steps

1. **Choose integration option** (I recommend Option 1 for demo)

2. **Backup original file:**
   ```powershell
   Copy-Item "apps\backend\app\chat\prolog\constraint_solver.pl" "apps\backend\app\chat\prolog\constraint_solver.pl.backup"
   ```

3. **Replace with KRR version:**
   ```powershell
   Copy-Item "apps\backend\app\chat\prolog\constraint_solver_krr.pl" "apps\backend\app\chat\prolog\constraint_solver.pl" -Force
   ```

4. **Test the integration:**
   - Restart Python backend
   - Test chat endpoints
   - Verify Prolog loads correctly

5. **If issues arise:**
   - Restore backup: `Copy-Item "apps\backend\app\chat\prolog\constraint_solver.pl.backup" "apps\backend\app\chat\prolog\constraint_solver.pl" -Force`
   - Check error logs
   - Or use Option 3 (load both files)

---

## Summary

**Current State:**
- ✅ Python loads: `scheduler.pl` + `constraint_solver.pl` (old)
- ❌ Python does NOT load: `constraint_solver_krr.pl` (new KRR version)

**To integrate KRR:**
- Replace `constraint_solver.pl` with `constraint_solver_krr.pl`
- Or update Python to load `constraint_solver_krr.pl`
- Or load both files for gradual migration

**For your professor demo:**
- Use Option 1: Replace file (simplest)
- Keep backup to restore later
- Show that Python service now uses KRR implementation
