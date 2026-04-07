# Schedule Assistant - Testing Documentation

## Overview

This document provides comprehensive testing documentation for the Schedule Assistant project, including unit tests, integration tests, and system (E2E) tests.

---

## Test Architecture

### Testing Pyramid

```
                 ┌─────────────────┐
                 │   E2E Tests     │  <- Robot Framework
                 │   (System)      │     Browser + API
                 └────────┬────────┘
                          │
              ┌───────────┴───────────┐
              │   Integration Tests   │  <- Pytest + Jest
              │       (API)           │     HTTP Client
              └───────────┬───────────┘
                          │
       ┌──────────────────┴──────────────────┐
       │           Unit Tests                │  <- Pytest + Jest
       │    (Services, Components)           │     Mock DB, Mock API
       └─────────────────────────────────────┘
```

---

## Test Categories

### 1. Backend Unit Tests (Pytest)

**Location:** `apps/backend/tests/`

| Test File | Coverage | Test IDs |
|-----------|----------|----------|
| `test_event_service.py` | EventService CRUD operations | UT-EVT-001 to UT-EVT-016 |
| `test_task_service.py` | TaskService CRUD operations | UT-TSK-001 to UT-TSK-016 |
| `test_events_router.py` | Events API endpoints | IT-EVT-001 to IT-EVT-014 |
| `test_tasks_router.py` | Tasks API endpoints | IT-TSK-001 to IT-TSK-014 |
| `test_health_router.py` | Health check endpoints | IT-HLT-001 to IT-HLT-002 |

**Running Backend Tests:**
```bash
cd apps/backend

# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_event_service.py -v

# Generate HTML report
pytest --html=test_report.html
```

### 2. Frontend Unit Tests (Jest)

**Location:** `apps/frontend/frontend/__tests__/`

| Test File | Coverage | Test IDs |
|-----------|----------|----------|
| `components/MonthGrid.test.tsx` | MonthGrid component | FE-MG-001 to FE-MG-005 |
| `components/FilterBar.test.tsx` | FilterBar component | FE-FB-001 to FE-FB-010 |
| `services/api.test.ts` | API service functions | FE-API-001 to FE-API-007 |

**Running Frontend Tests:**
```bash
cd apps/frontend/frontend

# Install dependencies
npm install

# Run all tests
npm test

# Run with coverage
npm run test:coverage

# Run in watch mode
npm run test:watch
```

### 3. System Tests (Robot Framework)

**Location:** `tests/robot/`

| Test Suite | Coverage | Test IDs |
|------------|----------|----------|
| `test_suites/events.robot` | Event management E2E | ST-EVT-001 to ST-EVT-011 |
| `test_suites/tasks.robot` | Task management E2E | ST-TSK-001 to ST-TSK-010 |
| `test_suites/api.robot` | API integration | ST-API-001 to ST-API-011 |

**Running Robot Framework Tests:**
```bash
cd tests/robot

# Install dependencies
pip install -r requirements.txt

# Run all tests
robot --outputdir results test_suites/

# Run specific test suite
robot --outputdir results test_suites/events.robot

# Run with specific tags
robot --include smoke --outputdir results test_suites/

# Generate HTML report only
robot --outputdir results --log NONE --report report.html test_suites/
```

---

## Test ID Convention

| Prefix | Category | Description |
|--------|----------|-------------|
| UT-XXX | Unit Test | Service/Component level tests |
| IT-XXX | Integration Test | API endpoint tests |
| FE-XXX | Frontend Test | React component/service tests |
| ST-XXX | System Test | End-to-end tests |

### Test ID Examples:
- `UT-EVT-001`: Unit Test - Event - Test #001 (Create event with valid data)
- `IT-TSK-005`: Integration Test - Task - Test #005 (Create task via API)
- `FE-MG-003`: Frontend - MonthGrid - Test #003 (User interactions)
- `ST-API-007`: System Test - API - Test #007 (Delete event)

---

## Test Case Documentation Format

Each test case follows this documentation structure:

```
Test ID: [ID]
Title: [Descriptive title]
Precondition: [What must be true before the test]
Input: [Test inputs/actions]
Expected Result: [What should happen]
```

### Example:

```
Test ID: UT-EVT-001
Title: Create event with valid data
Precondition: Calendar exists in database
Input: Valid event data (title, start_time, end_time, calendar_id)
Expected Result: Event is created successfully, all fields are populated, status is 'confirmed'
```

---

## Test Reports

### Backend (Pytest)

Generated reports:
- `apps/backend/htmlcov/index.html` - Coverage report
- `apps/backend/test_report.html` - Test execution report

### Frontend (Jest)

Generated reports:
- `apps/frontend/frontend/coverage/lcov-report/index.html` - Coverage report

### System Tests (Robot Framework)

Generated reports:
- `tests/robot/results/report.html` - Summary report
- `tests/robot/results/log.html` - Detailed execution log
- `tests/robot/results/output.xml` - XML results for CI/CD

---

## Coverage Goals

| Component | Target Coverage |
|-----------|-----------------|
| Backend Services | ≥80% |
| Backend Routers | ≥75% |
| Frontend Components | ≥70% |
| Frontend Services | ≥75% |
| E2E Critical Paths | 100% |

---

## Test Data Management

### Fixtures (Backend)
- `conftest.py` contains shared fixtures
- In-memory SQLite database for isolation
- Sample data: users, calendars, categories, events, tasks

### Mocks (Frontend)
- `jest.setup.ts` contains global mocks
- API calls mocked with `jest.fn()`
- Next.js navigation mocked

### Test Data (Robot Framework)
- Test data created/cleaned per test
- API session for direct backend manipulation
- Screenshots saved on failure

---

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: |
          cd apps/backend
          pip install -r requirements.txt
          pytest --cov=app --cov-report=xml

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: |
          cd apps/frontend/frontend
          npm ci
          npm run test:coverage

  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: |
          pip install -r tests/robot/requirements.txt
          robot --outputdir results tests/robot/test_suites/api.robot
```

---

## Troubleshooting

### Common Issues

1. **Backend tests fail with database error**
   - Ensure `aiosqlite` is installed for SQLite async support
   - Check that test database URL is set correctly

2. **Frontend tests fail with module not found**
   - Run `npm install` to ensure all dependencies are installed
   - Check `jest.config.ts` moduleNameMapper settings

3. **Robot Framework browser tests fail**
   - Ensure Chrome/Firefox is installed
   - Install webdriver: `pip install webdriver-manager`

4. **API tests fail with connection refused**
   - Ensure backend server is running on port 8000
   - Check CORS settings if running from different origin

---

## Summary Table

| Test Type | Framework | Location | Run Command |
|-----------|-----------|----------|-------------|
| Backend Unit | Pytest | `apps/backend/tests/` | `pytest` |
| Backend Integration | Pytest + httpx | `apps/backend/tests/` | `pytest` |
| Frontend Unit | Jest | `apps/frontend/frontend/__tests__/` | `npm test` |
| System/E2E | Robot Framework | `tests/robot/` | `robot test_suites/` |
