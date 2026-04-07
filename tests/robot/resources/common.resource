*** Settings ***
Documentation     Common resources and keywords for Schedule Assistant E2E tests.
Library           SeleniumLibrary
Library           RequestsLibrary
Library           Collections
Library           DateTime
Library           String

*** Variables ***
${BROWSER}                  chrome
${FRONTEND_URL}             http://localhost:3000
${BACKEND_URL}              http://localhost:8000
${IMPLICIT_WAIT}            10s
${EXPLICIT_WAIT}            15s
${SCREENSHOT_DIR}           ${CURDIR}/../results/screenshots

# API Endpoints
${API_EVENTS}               ${BACKEND_URL}/events
${API_TASKS}                ${BACKEND_URL}/tasks
${API_CALENDARS}            ${BACKEND_URL}/calendars
${API_CATEGORIES}           ${BACKEND_URL}/categories
${API_HEALTH}               ${BACKEND_URL}/health

*** Keywords ***
# ============ Browser Setup/Teardown ============

Open Browser To Application
    [Documentation]    Opens browser and navigates to the application
    Open Browser    ${FRONTEND_URL}    ${BROWSER}
    Maximize Browser Window
    Set Selenium Implicit Wait    ${IMPLICIT_WAIT}
    Wait Until Page Contains Element    css:body    timeout=${EXPLICIT_WAIT}

Close Browser And Cleanup
    [Documentation]    Closes browser and cleans up test data
    ${safe_name}=    Replace String    ${TEST NAME}    :    _
    ${safe_name}=    Replace String    ${safe_name}    /    _
    ${safe_name}=    Replace String    ${safe_name}    \\    _
    Capture Page Screenshot    ${SCREENSHOT_DIR}/final_${safe_name}.png
    Close All Browsers

# ============ API Setup Keywords ============

Setup API Session
    [Documentation]    Creates a requests session for API testing
    Create Session    api    ${BACKEND_URL}    verify=True

Check Backend Health
    [Documentation]    Verifies the backend API is responding
    ${response}=    GET On Session    api    /health
    Should Be Equal As Integers    ${response.status_code}    200
    ${json}=    Set Variable    ${response.json()}
    Should Be Equal    ${json['status']}    healthy

# ============ Navigation Keywords ============

Navigate To Month View
    [Documentation]    Navigates to the month view of the calendar
    Click Element    css:[data-testid="month-view-btn"]
    Wait Until Element Is Visible    css:.month-grid

Navigate To Day View
    [Documentation]    Navigates to the day view
    [Arguments]    ${date_key}
    Click Element    css:[data-date="${date_key}"]
    Wait Until Element Is Visible    css:.day-view

Select Date
    [Documentation]    Selects a specific date on the calendar
    [Arguments]    ${day_number}
    Click Element    xpath://div[contains(@class, 'calendar-day') and text()='${day_number}']
    Wait Until Element Is Visible    css:.day-selected

Navigate To Next Month
    [Documentation]    Clicks the next month navigation button
    Click Element    css:[data-testid="next-month-btn"]
    Sleep    0.5s

Navigate To Previous Month
    [Documentation]    Clicks the previous month navigation button
    Click Element    css:[data-testid="prev-month-btn"]
    Sleep    0.5s

# ============ Event Keywords ============

Open Add Event Modal
    [Documentation]    Opens the modal to add a new event
    Click Element    css:[title="Add Event"]
    Wait Until Element Is Visible    css:.modal-content    timeout=${EXPLICIT_WAIT}

Fill Event Form
    [Documentation]    Fills the event creation/edit form
    [Arguments]    ${title}    ${start_time}=09:00    ${end_time}=10:00    ${location}=${EMPTY}    ${notes}=${EMPTY}
    Input Text    css:input[name="title"]    ${title}
    Input Text    css:input[name="start_time"]    ${start_time}
    Input Text    css:input[name="end_time"]    ${end_time}
    Run Keyword If    '${location}' != '${EMPTY}'    Input Text    css:input[name="location"]    ${location}
    Run Keyword If    '${notes}' != '${EMPTY}'    Input Text    css:textarea[name="notes"]    ${notes}

Submit Event Form
    [Documentation]    Submits the event form
    Click Button    css:button[type="submit"]
    Wait Until Element Is Not Visible    css:.modal-content    timeout=${EXPLICIT_WAIT}

Create Event Via UI
    [Documentation]    Creates an event through the UI
    [Arguments]    ${title}    ${start_time}=09:00    ${end_time}=10:00    ${location}=${EMPTY}
    Open Add Event Modal
    Fill Event Form    ${title}    ${start_time}    ${end_time}    ${location}
    Submit Event Form
    Wait Until Element Contains    css:.calendar-event    ${title}    timeout=${EXPLICIT_WAIT}

Verify Event Exists On Calendar
    [Documentation]    Verifies an event is visible on the calendar
    [Arguments]    ${event_title}
    Wait Until Element Contains    css:.calendar-event    ${event_title}    timeout=${EXPLICIT_WAIT}

Delete Event Via UI
    [Documentation]    Deletes an event through the UI
    [Arguments]    ${event_title}
    Click Element    xpath://div[contains(@class, 'calendar-event') and contains(text(), '${event_title}')]
    Wait Until Element Is Visible    css:.event-details-modal
    Click Button    css:button[data-action="delete"]
    Click Button    css:button[data-confirm="yes"]
    Wait Until Element Is Not Visible    xpath://div[contains(text(), '${event_title}')]

# ============ Task Keywords ============

Open Add Task Modal
    [Documentation]    Opens the modal to add a new task
    Click Element    css:[data-testid="add-task-btn"]
    Wait Until Element Is Visible    css:.task-modal

Fill Task Form
    [Documentation]    Fills the task creation form
    [Arguments]    ${title}    ${date}    ${notes}=${EMPTY}
    Input Text    css:input[name="task_title"]    ${title}
    Input Text    css:input[name="task_date"]    ${date}
    Run Keyword If    '${notes}' != '${EMPTY}'    Input Text    css:textarea[name="task_notes"]    ${notes}

Submit Task Form
    [Documentation]    Submits the task form
    Click Button    css:button.submit-task
    Wait Until Element Is Not Visible    css:.task-modal

Complete Task Via UI
    [Documentation]    Marks a task as completed
    [Arguments]    ${task_title}
    Click Element    xpath://div[contains(@class, 'task-item') and contains(text(), '${task_title}')]//input[@type='checkbox']
    Wait Until Element Has Attribute    xpath://div[contains(@class, 'task-item') and contains(text(), '${task_title}')]    data-completed    true

# ============ Filter Keywords ============

Open Filter Panel
    [Documentation]    Opens the filter panel
    Click Element    css:[title="Filter"]
    Wait Until Element Is Visible    css:.filter-panel

Apply Search Filter
    [Documentation]    Applies a search filter
    [Arguments]    ${search_text}
    Input Text    css:input[placeholder="Search events..."]    ${search_text}
    Sleep    0.5s    # Wait for debounce

Select Category Filter
    [Documentation]    Selects a category filter
    [Arguments]    ${category_name}
    Open Filter Panel
    Click Element    xpath://button[contains(text(), '${category_name}')]

Clear All Filters
    [Documentation]    Clears all active filters
    Open Filter Panel
    Click Button    css:button:contains('Reset')
    Click Button    css:button:contains('Apply')

# ============ Chat Keywords ============

Open Chat Panel
    [Documentation]    Opens the AI chat panel
    Click Element    css:[data-testid="chat-toggle"]
    Wait Until Element Is Visible    css:.chat-panel

Send Chat Message
    [Documentation]    Sends a message in the chat
    [Arguments]    ${message}
    Input Text    css:.chat-input    ${message}
    Click Button    css:button[data-testid="send-message"]
    Wait Until Element Is Visible    css:.chat-response    timeout=${EXPLICIT_WAIT}

Verify Chat Response Contains
    [Documentation]    Verifies chat response contains expected text
    [Arguments]    ${expected_text}
    Element Should Contain    css:.chat-response    ${expected_text}

# ============ API Test Keywords ============

Create Event Via API
    [Documentation]    Creates an event using the API
    [Arguments]    ${calendar_id}    ${title}    ${start_time}    ${end_time}
    ${body}=    Create Dictionary
    ...    calendar_id=${calendar_id}
    ...    title=${title}
    ...    start_time=${start_time}
    ...    end_time=${end_time}
    ${response}=    POST On Session    api    /events    json=${body}
    Should Be Equal As Integers    ${response.status_code}    201
    RETURN    ${response.json()}

Get Events Via API
    [Documentation]    Gets events from the API
    [Arguments]    ${calendar_id}
    ${response}=    GET On Session    api    /events    params=calendar_id=${calendar_id}
    Should Be Equal As Integers    ${response.status_code}    200
    RETURN    ${response.json()}

Delete Event Via API
    [Documentation]    Deletes an event using the API
    [Arguments]    ${event_id}
    ${response}=    DELETE On Session    api    /events/${event_id}
    Should Be Equal As Integers    ${response.status_code}    204

# ============ Assertion Keywords ============

Page Should Have No Errors
    [Documentation]    Checks that there are no visible error messages
    Page Should Not Contain    Error
    Page Should Not Contain Element    css:.error-message

Toast Should Show Success
    [Documentation]    Verifies a success toast message appears
    [Arguments]    ${expected_text}=${EMPTY}
    Wait Until Element Is Visible    css:.toast-success    timeout=5s
    Run Keyword If    '${expected_text}' != '${EMPTY}'    Element Should Contain    css:.toast-success    ${expected_text}

Take Screenshot On Failure
    [Documentation]    Takes a screenshot when a test fails
    ${safe_name}=    Replace String    ${TEST NAME}    :    _
    ${safe_name}=    Replace String    ${safe_name}    /    _
    ${safe_name}=    Replace String    ${safe_name}    \\    _
    Run Keyword If Test Failed    Capture Page Screenshot    ${SCREENSHOT_DIR}/failure_${safe_name}.png
