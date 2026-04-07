*** Settings ***
Documentation     API Integration Test Suite.
...               Test ID Format: ST-API-XXX (System Test - API)
Library           RequestsLibrary
Library           Collections
Library           DateTime
Library           String

Suite Setup       Suite Setup
Suite Teardown    Suite Teardown

*** Variables ***
${BACKEND_URL}      http://localhost:8000
${TEST_CALENDAR_ID}    ${EMPTY}

*** Keywords ***
Suite Setup
    [Documentation]    Setup for API tests
    Create Session    api    ${BACKEND_URL}    verify=True
    Log    Starting API Integration Tests

Suite Teardown
    [Documentation]    Cleanup after API tests
    Delete All Sessions
    Log    Completed API Integration Tests

Get Default Calendar ID
    [Documentation]    Gets the default calendar ID from the API
    ${response}=    GET On Session    api    /calendars
    Should Be Equal As Integers    ${response.status_code}    200
    ${calendars}=    Set Variable    ${response.json()}
    ${length}=    Get Length    ${calendars}
    Should Be True    ${length} > 0    No calendars found
    ${calendar_id}=    Set Variable    ${calendars[0]['id']}
    Set Suite Variable    ${TEST_CALENDAR_ID}    ${calendar_id}
    RETURN    ${calendar_id}

*** Test Cases ***
# ============ Health Check Tests ============

ST-API-001: Health Check Returns Healthy
    [Documentation]    Verify health endpoint returns healthy status.
    ...
    ...    *Endpoint:* GET /health
    ...    *Expected:* 200 OK with status "healthy"
    [Tags]    smoke    api    health
    
    ${response}=    GET On Session    api    /health
    
    Should Be Equal As Integers    ${response.status_code}    200
    ${json}=    Set Variable    ${response.json()}
    Should Be Equal    ${json['status']}    healthy

ST-API-002: Root Endpoint Returns API Info
    [Documentation]    Verify root endpoint returns API information.
    ...
    ...    *Endpoint:* GET /
    ...    *Expected:* 200 OK with app name and version
    [Tags]    api    root
    
    ${response}=    GET On Session    api    /
    
    Should Be Equal As Integers    ${response.status_code}    200
    ${json}=    Set Variable    ${response.json()}
    Dictionary Should Contain Key    ${json}    name
    Dictionary Should Contain Key    ${json}    version
    Dictionary Should Contain Key    ${json}    docs

# ============ Calendar API Tests ============

ST-API-003: List Calendars
    [Documentation]    Verify calendars can be listed.
    ...
    ...    *Endpoint:* GET /calendars
    ...    *Expected:* 200 OK with list of calendars
    [Tags]    api    calendar
    
    ${response}=    GET On Session    api    /calendars
    
    Should Be Equal As Integers    ${response.status_code}    200
    ${calendars}=    Set Variable    ${response.json()}
    Should Be True    isinstance(${calendars}, list)

# ============ Event API Tests ============

ST-API-004: Create Event With Valid Data
    [Documentation]    Verify event can be created via API.
    ...
    ...    *Endpoint:* POST /events
    ...    *Input:* Valid event data
    ...    *Expected:* 201 Created with event data
    [Tags]    api    event    create
    
    ${calendar_id}=    Get Default Calendar ID
    
    ${now}=    Get Current Date    result_format=%Y-%m-%dT%H:%M:%S
    ${end}=    Get Current Date    increment=+1 hour    result_format=%Y-%m-%dT%H:%M:%S
    
    ${body}=    Create Dictionary
    ...    calendar_id=${calendar_id}
    ...    title=API Test Event
    ...    start_time=${now}+00:00
    ...    end_time=${end}+00:00
    
    ${response}=    POST On Session    api    /events    json=${body}
    
    Should Be Equal As Integers    ${response.status_code}    201
    ${json}=    Set Variable    ${response.json()}
    Should Be Equal    ${json['title']}    API Test Event
    Dictionary Should Contain Key    ${json}    id

ST-API-005: Get Event By ID
    [Documentation]    Verify event can be retrieved by ID.
    ...
    ...    *Endpoint:* GET /events/{id}
    ...    *Expected:* 200 OK with event details
    [Tags]    api    event    get
    
    ${calendar_id}=    Get Default Calendar ID
    
    # Create an event first
    ${now}=    Get Current Date    result_format=%Y-%m-%dT%H:%M:%S
    ${end}=    Get Current Date    increment=+1 hour    result_format=%Y-%m-%dT%H:%M:%S
    
    ${body}=    Create Dictionary
    ...    calendar_id=${calendar_id}
    ...    title=Get Test Event
    ...    start_time=${now}+00:00
    ...    end_time=${end}+00:00
    
    ${create_response}=    POST On Session    api    /events    json=${body}
    ${event_id}=    Set Variable    ${create_response.json()['id']}
    
    # Get the event
    ${response}=    GET On Session    api    /events/${event_id}
    
    Should Be Equal As Integers    ${response.status_code}    200
    ${json}=    Set Variable    ${response.json()}
    Should Be Equal    ${json['id']}    ${event_id}
    Should Be Equal    ${json['title']}    Get Test Event

ST-API-006: Update Event
    [Documentation]    Verify event can be updated via API.
    ...
    ...    *Endpoint:* PATCH /events/{id}
    ...    *Input:* Updated event data
    ...    *Expected:* 200 OK with updated event
    [Tags]    api    event    update
    
    ${calendar_id}=    Get Default Calendar ID
    
    # Create an event
    ${now}=    Get Current Date    result_format=%Y-%m-%dT%H:%M:%S
    ${end}=    Get Current Date    increment=+1 hour    result_format=%Y-%m-%dT%H:%M:%S
    
    ${body}=    Create Dictionary
    ...    calendar_id=${calendar_id}
    ...    title=Update Test Event
    ...    start_time=${now}+00:00
    ...    end_time=${end}+00:00
    
    ${create_response}=    POST On Session    api    /events    json=${body}
    ${event_id}=    Set Variable    ${create_response.json()['id']}
    
    # Update the event
    ${update_body}=    Create Dictionary    title=Updated Event Title
    ${response}=    PATCH On Session    api    /events/${event_id}    json=${update_body}
    
    Should Be Equal As Integers    ${response.status_code}    200
    ${json}=    Set Variable    ${response.json()}
    Should Be Equal    ${json['title']}    Updated Event Title

ST-API-007: Delete Event
    [Documentation]    Verify event can be deleted via API.
    ...
    ...    *Endpoint:* DELETE /events/{id}
    ...    *Expected:* 204 No Content
    [Tags]    api    event    delete
    
    ${calendar_id}=    Get Default Calendar ID
    
    # Create an event
    ${now}=    Get Current Date    result_format=%Y-%m-%dT%H:%M:%S
    ${end}=    Get Current Date    increment=+1 hour    result_format=%Y-%m-%dT%H:%M:%S
    
    ${body}=    Create Dictionary
    ...    calendar_id=${calendar_id}
    ...    title=Delete Test Event
    ...    start_time=${now}+00:00
    ...    end_time=${end}+00:00
    
    ${create_response}=    POST On Session    api    /events    json=${body}
    ${event_id}=    Set Variable    ${create_response.json()['id']}
    
    # Delete the event
    ${response}=    DELETE On Session    api    /events/${event_id}
    
    Should Be Equal As Integers    ${response.status_code}    204

ST-API-008: Get Non-Existent Event Returns 404
    [Documentation]    Verify 404 is returned for non-existent event.
    ...
    ...    *Endpoint:* GET /events/{non_existent_id}
    ...    *Expected:* 404 Not Found
    [Tags]    api    event    error
    
    ${fake_id}=    Set Variable    00000000-0000-0000-0000-000000000000
    
    ${response}=    GET On Session    api    /events/${fake_id}    expected_status=404
    
    Should Be Equal As Integers    ${response.status_code}    404

# ============ Task API Tests ============

ST-API-009: Create Task With Valid Data
    [Documentation]    Verify task can be created via API.
    ...
    ...    *Endpoint:* POST /tasks
    ...    *Input:* Valid task data
    ...    *Expected:* 201 Created with task data
    [Tags]    api    task    create
    
    ${calendar_id}=    Get Default Calendar ID
    
    ${today}=    Get Current Date    result_format=%Y-%m-%d
    
    ${body}=    Create Dictionary
    ...    calendar_id=${calendar_id}
    ...    title=API Test Task
    ...    date=${today}
    
    ${response}=    POST On Session    api    /tasks    json=${body}
    
    Should Be Equal As Integers    ${response.status_code}    201
    ${json}=    Set Variable    ${response.json()}
    Should Be Equal    ${json['title']}    API Test Task
    Should Be Equal    ${json['status']}    pending

ST-API-010: Complete Task
    [Documentation]    Verify task can be marked as completed via API.
    ...
    ...    *Endpoint:* POST /tasks/{id}/complete
    ...    *Expected:* 200 OK with status "completed"
    [Tags]    api    task    complete
    
    ${calendar_id}=    Get Default Calendar ID
    
    # Create a task
    ${today}=    Get Current Date    result_format=%Y-%m-%d
    
    ${body}=    Create Dictionary
    ...    calendar_id=${calendar_id}
    ...    title=Complete Me Task
    ...    date=${today}
    
    ${create_response}=    POST On Session    api    /tasks    json=${body}
    ${task_id}=    Set Variable    ${create_response.json()['id']}
    
    # Complete the task
    ${response}=    POST On Session    api    /tasks/${task_id}/complete
    
    Should Be Equal As Integers    ${response.status_code}    200
    ${json}=    Set Variable    ${response.json()}
    Should Be Equal    ${json['status']}    completed

# ============ Conflict Detection Tests ============

ST-API-011: Check Event Conflicts
    [Documentation]    Verify event conflict detection works.
    ...
    ...    *Endpoint:* GET /events/conflicts/check
    ...    *Input:* Overlapping time range
    ...    *Expected:* Returns conflict information
    [Tags]    api    event    conflict
    
    ${calendar_id}=    Get Default Calendar ID
    
    # Create an event
    ${now}=    Get Current Date    result_format=%Y-%m-%dT%H:%M:%S
    ${end}=    Get Current Date    increment=+1 hour    result_format=%Y-%m-%dT%H:%M:%S
    
    ${body}=    Create Dictionary
    ...    calendar_id=${calendar_id}
    ...    title=Conflict Base Event
    ...    start_time=${now}+00:00
    ...    end_time=${end}+00:00
    
    POST On Session    api    /events    json=${body}
    
    # Check for conflicts at the same time
    ${params}=    Create Dictionary
    ...    calendar_id=${calendar_id}
    ...    start_time=${now}+00:00
    ...    end_time=${end}+00:00
    
    ${response}=    GET On Session    api    /events/conflicts/check    params=${params}
    
    Should Be Equal As Integers    ${response.status_code}    200
    ${json}=    Set Variable    ${response.json()}
    Should Be Equal    ${json['has_conflicts']}    ${True}
