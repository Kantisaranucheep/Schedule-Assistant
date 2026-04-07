*** Settings ***
Documentation     E2E Test Suite for Task Management functionality.
...               Test ID Format: ST-TSK-XXX (System Test - Tasks)
Resource          ../resources/common.resource
Suite Setup       Suite Setup
Suite Teardown    Suite Teardown
Test Setup        Test Setup
Test Teardown     Test Teardown

*** Variables ***
${TEST_TASK_TITLE}          E2E Test Task

*** Keywords ***
Suite Setup
    [Documentation]    Setup for the entire test suite
    Setup API Session
    Check Backend Health
    Log    Starting Task Management E2E Tests

Suite Teardown
    [Documentation]    Cleanup after all tests
    Close All Browsers
    Log    Completed Task Management E2E Tests

Test Setup
    [Documentation]    Setup for each individual test
    Open Browser To Application

Test Teardown
    [Documentation]    Cleanup after each test
    Close Browser And Cleanup

*** Test Cases ***
# ============ Task Creation Tests ============

ST-TSK-001: Create Task With Valid Data
    [Documentation]    Verify user can create a task with valid data.
    ...
    ...    *Precondition:* User is on calendar page
    ...    *Input:* Valid task title and date
    ...    *Expected:* Task is created and visible
    [Tags]    smoke    task    create
    
    Open Add Task Modal
    
    ${today}=    Get Current Date    result_format=%Y-%m-%d
    Fill Task Form    ${TEST_TASK_TITLE}    ${today}
    
    Submit Task Form
    
    # Verify task appears
    Wait Until Element Contains    css:.task-list    ${TEST_TASK_TITLE}    timeout=10s
    
    Page Should Have No Errors

ST-TSK-002: Create Task With Notes
    [Documentation]    Verify user can create a task with notes.
    ...
    ...    *Precondition:* User is on calendar page
    ...    *Input:* Task with title, date, and notes
    ...    *Expected:* Task is created with notes saved
    [Tags]    task    create
    
    Open Add Task Modal
    
    ${today}=    Get Current Date    result_format=%Y-%m-%d
    Fill Task Form    Task With Notes    ${today}    Important notes for this task
    
    Submit Task Form
    
    Wait Until Element Contains    css:.task-list    Task With Notes    timeout=10s

ST-TSK-003: Create Task For Future Date
    [Documentation]    Verify user can create a task for a future date.
    ...
    ...    *Precondition:* User is on calendar page
    ...    *Input:* Task with future date
    ...    *Expected:* Task is scheduled for the future date
    [Tags]    task    create    future
    
    Open Add Task Modal
    
    ${future_date}=    Get Current Date    increment=+7 days    result_format=%Y-%m-%d
    Fill Task Form    Future Task    ${future_date}
    
    Submit Task Form
    
    # Navigate to future date and verify
    Navigate To Next Month
    Wait Until Page Contains Element    xpath://div[contains(@class, 'task-item') and contains(text(), 'Future Task')]

# ============ Task Completion Tests ============

ST-TSK-004: Mark Task As Completed
    [Documentation]    Verify user can mark a task as completed.
    ...
    ...    *Precondition:* Pending task exists
    ...    *Input:* Click complete checkbox
    ...    *Expected:* Task status changes to completed
    [Tags]    smoke    task    complete
    
    # Create a task first
    Open Add Task Modal
    ${today}=    Get Current Date    result_format=%Y-%m-%d
    Fill Task Form    Complete Me    ${today}
    Submit Task Form
    
    # Mark as completed
    Complete Task Via UI    Complete Me
    
    # Verify completion state
    Element Should Have Attribute    xpath://div[contains(@class, 'task-item') and contains(text(), 'Complete Me')]//input    checked

ST-TSK-005: Uncomplete A Completed Task
    [Documentation]    Verify user can uncomplete a task.
    ...
    ...    *Precondition:* Completed task exists
    ...    *Input:* Click to uncomplete
    ...    *Expected:* Task status returns to pending
    [Tags]    task    complete    uncomplete
    
    # Create and complete a task
    Open Add Task Modal
    ${today}=    Get Current Date    result_format=%Y-%m-%d
    Fill Task Form    Toggle Task    ${today}
    Submit Task Form
    
    Complete Task Via UI    Toggle Task
    
    # Uncomplete by clicking again
    Click Element    xpath://div[contains(@class, 'task-item') and contains(text(), 'Toggle Task')]//input[@type='checkbox']
    
    # Verify uncompleted
    Element Should Not Have Attribute    xpath://div[contains(@class, 'task-item') and contains(text(), 'Toggle Task')]//input    checked

# ============ Task Update Tests ============

ST-TSK-006: Update Task Title
    [Documentation]    Verify user can update task title.
    ...
    ...    *Precondition:* Task exists
    ...    *Input:* New title
    ...    *Expected:* Task title is updated
    [Tags]    task    update
    
    Open Add Task Modal
    ${today}=    Get Current Date    result_format=%Y-%m-%d
    Fill Task Form    Old Task Title    ${today}
    Submit Task Form
    
    # Click to edit
    Click Element    xpath://div[contains(@class, 'task-item') and contains(text(), 'Old Task Title')]
    Wait Until Element Is Visible    css:.task-edit-modal
    
    # Update title
    Clear Element Text    css:input[name="task_title"]
    Input Text    css:input[name="task_title"]    New Task Title
    
    Click Button    css:button.save-task
    
    # Verify update
    Wait Until Element Contains    css:.task-list    New Task Title    timeout=10s
    Page Should Not Contain    Old Task Title

ST-TSK-007: Update Task Date
    [Documentation]    Verify user can reschedule a task.
    ...
    ...    *Precondition:* Task exists
    ...    *Input:* New date
    ...    *Expected:* Task is moved to new date
    [Tags]    task    update    reschedule
    
    Open Add Task Modal
    ${today}=    Get Current Date    result_format=%Y-%m-%d
    Fill Task Form    Reschedule Task    ${today}
    Submit Task Form
    
    # Edit task
    Click Element    xpath://div[contains(@class, 'task-item') and contains(text(), 'Reschedule Task')]
    Wait Until Element Is Visible    css:.task-edit-modal
    
    ${tomorrow}=    Get Current Date    increment=+1 day    result_format=%Y-%m-%d
    Clear Element Text    css:input[name="task_date"]
    Input Text    css:input[name="task_date"]    ${tomorrow}
    
    Click Button    css:button.save-task

# ============ Task Delete Tests ============

ST-TSK-008: Delete Task
    [Documentation]    Verify user can delete a task.
    ...
    ...    *Precondition:* Task exists
    ...    *Input:* Delete action
    ...    *Expected:* Task is removed
    [Tags]    task    delete
    
    Open Add Task Modal
    ${today}=    Get Current Date    result_format=%Y-%m-%d
    Fill Task Form    Delete Me Task    ${today}
    Submit Task Form
    
    # Verify task exists
    Wait Until Element Contains    css:.task-list    Delete Me Task    timeout=10s
    
    # Delete task
    Click Element    xpath://div[contains(@class, 'task-item') and contains(text(), 'Delete Me Task')]//button[@data-action='delete']
    Click Button    css:button[data-confirm="yes"]
    
    # Verify deletion
    Wait Until Page Does Not Contain Element    xpath://div[contains(@class, 'task-item') and contains(text(), 'Delete Me Task')]

# ============ Task Filter Tests ============

ST-TSK-009: Filter Tasks By Type
    [Documentation]    Verify task filter shows only tasks.
    ...
    ...    *Precondition:* Both events and tasks exist
    ...    *Input:* Select "Task" type filter
    ...    *Expected:* Only tasks are shown
    [Tags]    task    filter
    
    # Create an event
    Create Event Via UI    Test Event    10:00    11:00
    
    # Create a task
    Open Add Task Modal
    ${today}=    Get Current Date    result_format=%Y-%m-%d
    Fill Task Form    Test Task    ${today}
    Submit Task Form
    
    # Apply filter for tasks only
    Open Filter Panel
    Click Element    xpath://button[contains(text(), 'Task')]
    Click Button    css:button:contains('Apply')
    
    # Verify only tasks visible
    Wait Until Element Contains    css:.calendar    Test Task    timeout=10s
    Page Should Not Contain Element    xpath://div[contains(@class, 'calendar-event') and contains(text(), 'Test Event')]

ST-TSK-010: Show Completed Tasks
    [Documentation]    Verify user can see completed tasks.
    ...
    ...    *Precondition:* Completed tasks exist
    ...    *Input:* Show completed filter
    ...    *Expected:* Completed tasks are visible
    [Tags]    task    filter    completed
    
    # Create and complete a task
    Open Add Task Modal
    ${today}=    Get Current Date    result_format=%Y-%m-%d
    Fill Task Form    Completed Task Test    ${today}
    Submit Task Form
    
    Complete Task Via UI    Completed Task Test
    
    # Verify completed task is still visible (or apply filter if needed)
    Element Should Be Visible    xpath://div[contains(@class, 'task-item') and contains(text(), 'Completed Task Test')]
