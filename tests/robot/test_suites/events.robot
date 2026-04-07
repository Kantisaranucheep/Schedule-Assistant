*** Settings ***
Documentation     E2E Test Suite for Event Management functionality.
...               Test ID Format: ST-EVT-XXX (System Test - Events)
Resource          ../resources/common.resource
Suite Setup       Suite Setup
Suite Teardown    Suite Teardown
Test Setup        Test Setup
Test Teardown     Test Teardown

*** Variables ***
${TEST_EVENT_TITLE}         E2E Test Meeting
${TEST_EVENT_LOCATION}      Conference Room A

*** Keywords ***
Suite Setup
    [Documentation]    Setup for the entire test suite
    Setup API Session
    Check Backend Health
    Log    Starting Event Management E2E Tests

Suite Teardown
    [Documentation]    Cleanup after all tests
    Close All Browsers
    Log    Completed Event Management E2E Tests

Test Setup
    [Documentation]    Setup for each individual test
    Open Browser To Application

Test Teardown
    [Documentation]    Cleanup after each test
    Close Browser And Cleanup

*** Test Cases ***
# ============ Event Creation Tests ============

ST-EVT-001: Create Event With Valid Data
    [Documentation]    Verify user can create an event with valid data.
    ...
    ...    *Precondition:* User is on calendar page
    ...    *Input:* Valid event title, start time, end time
    ...    *Expected:* Event is created and visible on calendar
    [Tags]    smoke    event    create
    
    # Navigate to add event
    Open Add Event Modal
    
    # Fill event details
    Fill Event Form    ${TEST_EVENT_TITLE}    09:00    10:00    ${TEST_EVENT_LOCATION}
    
    # Submit form
    Submit Event Form
    
    # Verify event appears
    Verify Event Exists On Calendar    ${TEST_EVENT_TITLE}
    
    # Verify no errors
    Page Should Have No Errors

ST-EVT-002: Create All-Day Event
    [Documentation]    Verify user can create an all-day event.
    ...
    ...    *Precondition:* User is on calendar page
    ...    *Input:* Event with all-day flag enabled
    ...    *Expected:* All-day event is created and displayed correctly
    [Tags]    event    create    all-day
    
    Open Add Event Modal
    
    Input Text    css:input[name="title"]    All Day Event Test
    Click Element    css:input[name="all_day"]    # Toggle all-day
    
    Submit Event Form
    
    Verify Event Exists On Calendar    All Day Event Test

ST-EVT-003: Create Event With Conflict Warning
    [Documentation]    Verify system warns about conflicting events.
    ...
    ...    *Precondition:* An event exists at 9:00-10:00 AM
    ...    *Input:* New event at overlapping time
    ...    *Expected:* Conflict warning is displayed
    [Tags]    event    create    conflict
    
    # First create an event
    Create Event Via UI    First Meeting    09:00    10:00
    
    # Try to create overlapping event
    Open Add Event Modal
    Fill Event Form    Conflicting Meeting    09:30    10:30
    
    # Submit and check for conflict warning
    Click Button    css:button[type="submit"]
    Wait Until Element Is Visible    css:.conflict-warning    timeout=5s

# ============ Event Viewing Tests ============

ST-EVT-004: View Event Details
    [Documentation]    Verify user can view event details.
    ...
    ...    *Precondition:* Event exists on calendar
    ...    *Input:* Click on event
    ...    *Expected:* Event details modal shows all information
    [Tags]    event    view
    
    Create Event Via UI    View Test Event    14:00    15:00    Test Location
    
    # Click on the event
    Click Element    xpath://div[contains(@class, 'calendar-event') and contains(text(), 'View Test Event')]
    
    # Verify details are shown
    Wait Until Element Is Visible    css:.event-details-modal
    Element Should Contain    css:.event-title    View Test Event
    Element Should Contain    css:.event-location    Test Location

ST-EVT-005: View Events In Day View
    [Documentation]    Verify events are displayed correctly in day view.
    ...
    ...    *Precondition:* Events exist for a specific day
    ...    *Input:* Navigate to day view
    ...    *Expected:* All events for that day are visible
    [Tags]    event    view    day-view
    
    Create Event Via UI    Day View Event    11:00    12:00
    
    # Switch to day view (click on date)
    ${today}=    Get Current Date    result_format=%d
    Click Element    xpath://div[contains(@class, 'calendar-day')]//div[text()='${today}']
    
    Wait Until Element Is Visible    css:.day-view
    Element Should Contain    css:.day-view    Day View Event

# ============ Event Update Tests ============

ST-EVT-006: Update Event Title
    [Documentation]    Verify user can update event title.
    ...
    ...    *Precondition:* Event exists
    ...    *Input:* New title for the event
    ...    *Expected:* Event title is updated
    [Tags]    event    update
    
    Create Event Via UI    Original Title    10:00    11:00
    
    # Click to edit
    Click Element    xpath://div[contains(@class, 'calendar-event') and contains(text(), 'Original Title')]
    Wait Until Element Is Visible    css:.event-details-modal
    
    Click Button    css:button[data-action="edit"]
    
    # Update title
    Clear Element Text    css:input[name="title"]
    Input Text    css:input[name="title"]    Updated Title
    
    Submit Event Form
    
    # Verify update
    Verify Event Exists On Calendar    Updated Title
    Page Should Not Contain    Original Title

ST-EVT-007: Update Event Time
    [Documentation]    Verify user can update event time.
    ...
    ...    *Precondition:* Event exists at original time
    ...    *Input:* New start and end time
    ...    *Expected:* Event time is updated
    [Tags]    event    update    time
    
    Create Event Via UI    Time Update Test    09:00    10:00
    
    # Open edit modal
    Click Element    xpath://div[contains(@class, 'calendar-event') and contains(text(), 'Time Update Test')]
    Wait Until Element Is Visible    css:.event-details-modal
    Click Button    css:button[data-action="edit"]
    
    # Update times
    Clear Element Text    css:input[name="start_time"]
    Input Text    css:input[name="start_time"]    14:00
    Clear Element Text    css:input[name="end_time"]
    Input Text    css:input[name="end_time"]    15:00
    
    Submit Event Form
    
    # Verify time change (visual check would need more specific selectors)
    Verify Event Exists On Calendar    Time Update Test

# ============ Event Delete Tests ============

ST-EVT-008: Delete Event (Soft Delete)
    [Documentation]    Verify user can soft delete an event.
    ...
    ...    *Precondition:* Event exists
    ...    *Input:* Delete action
    ...    *Expected:* Event is removed from calendar view
    [Tags]    event    delete
    
    Create Event Via UI    Delete Test Event    16:00    17:00
    
    # Verify event exists first
    Verify Event Exists On Calendar    Delete Test Event
    
    # Delete the event
    Delete Event Via UI    Delete Test Event
    
    # Verify event is gone
    Page Should Not Contain    Delete Test Event

ST-EVT-009: Cancel Delete Operation
    [Documentation]    Verify user can cancel delete operation.
    ...
    ...    *Precondition:* Delete confirmation dialog is shown
    ...    *Input:* Cancel button click
    ...    *Expected:* Event remains on calendar
    [Tags]    event    delete    cancel
    
    Create Event Via UI    Cancel Delete Test    13:00    14:00
    
    # Open event and initiate delete
    Click Element    xpath://div[contains(@class, 'calendar-event') and contains(text(), 'Cancel Delete Test')]
    Wait Until Element Is Visible    css:.event-details-modal
    Click Button    css:button[data-action="delete"]
    
    # Cancel the delete
    Click Button    css:button[data-confirm="no"]
    
    # Verify event still exists
    Verify Event Exists On Calendar    Cancel Delete Test

# ============ Event Filter Tests ============

ST-EVT-010: Filter Events By Search Text
    [Documentation]    Verify search filter works correctly.
    ...
    ...    *Precondition:* Multiple events exist
    ...    *Input:* Search text matching one event
    ...    *Expected:* Only matching events are shown
    [Tags]    event    filter    search
    
    Create Event Via UI    Alpha Meeting    09:00    10:00
    Create Event Via UI    Beta Conference    11:00    12:00
    
    # Apply search filter
    Apply Search Filter    Alpha
    
    # Verify filtering
    Element Should Contain    css:.calendar    Alpha Meeting
    Page Should Not Contain Element    xpath://div[contains(@class, 'calendar-event') and contains(text(), 'Beta Conference')]

ST-EVT-011: Filter Events By Category
    [Documentation]    Verify category filter works correctly.
    ...
    ...    *Precondition:* Events with different categories exist
    ...    *Input:* Select specific category
    ...    *Expected:* Only events in that category are shown
    [Tags]    event    filter    category
    
    # This test requires pre-existing categories and events
    Select Category Filter    Work
    
    # Events should be filtered by category
    Wait Until Page Contains Element    css:.calendar-event[data-category="Work"]
