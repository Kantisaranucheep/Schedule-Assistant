"""
API Router tests for Tasks endpoints.

Test ID Format: IT-TSK-XXX (Integration Tests)
"""

import uuid
from datetime import date, timedelta

import pytest
import pytest_asyncio
from httpx import AsyncClient

from tests.conftest import create_task_data


class TestTasksRouterList:
    """Test cases for GET /tasks endpoint."""

    @pytest.mark.asyncio
    async def test_list_tasks_for_calendar(self, client: AsyncClient, sample_task, sample_calendar):
        """
        IT-TSK-001: List tasks for calendar
        
        Precondition: Calendar has tasks
        Input: GET /tasks?calendar_id={id}
        Expected: Returns list containing the tasks
        """
        response = await client.get(f"/tasks?calendar_id={sample_calendar.id}")
        
        assert response.status_code == 200
        tasks = response.json()
        assert len(tasks) >= 1

    @pytest.mark.asyncio
    async def test_list_tasks_with_date_filter(self, client: AsyncClient, sample_calendar):
        """
        IT-TSK-002: List tasks within date range
        
        Precondition: Calendar has tasks at various dates
        Input: GET /tasks?calendar_id={id}&start_date={}&end_date={}
        Expected: Returns only tasks within date range
        """
        today = date.today()
        params = {
            "calendar_id": str(sample_calendar.id),
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=30)).isoformat(),
        }
        
        response = await client.get("/tasks", params=params)
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestTasksRouterGet:
    """Test cases for GET /tasks/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_task_success(self, client: AsyncClient, sample_task):
        """
        IT-TSK-003: Get existing task by ID
        
        Precondition: Task exists
        Input: GET /tasks/{task_id}
        Expected: Returns task data with 200 status
        """
        response = await client.get(f"/tasks/{sample_task.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_task.id)
        assert data["title"] == sample_task.title

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, client: AsyncClient):
        """
        IT-TSK-004: Get non-existent task
        
        Precondition: None
        Input: GET /tasks/{random_uuid}
        Expected: Returns 404 with error message
        """
        response = await client.get(f"/tasks/{uuid.uuid4()}")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestTasksRouterCreate:
    """Test cases for POST /tasks endpoint."""

    @pytest.mark.asyncio
    async def test_create_task_success(self, client: AsyncClient, sample_calendar):
        """
        IT-TSK-005: Create task with valid data
        
        Precondition: Calendar exists
        Input: POST /tasks with valid task data
        Expected: Returns created task with 201 status
        """
        task_data = create_task_data(sample_calendar.id, title="New API Task")
        
        response = await client.post("/tasks", json=task_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New API Task"
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_create_task_with_category(self, client: AsyncClient, sample_calendar, sample_category):
        """
        IT-TSK-006: Create task with category
        
        Precondition: Calendar and Category exist
        Input: POST /tasks with category_id
        Expected: Returns created task with category association
        """
        task_data = create_task_data(
            sample_calendar.id,
            title="Categorized Task",
            category_id=str(sample_category.id),
        )
        
        response = await client.post("/tasks", json=task_data)
        
        assert response.status_code == 201
        assert response.json()["category_id"] == str(sample_category.id)

    @pytest.mark.asyncio
    async def test_create_task_invalid_data(self, client: AsyncClient, sample_calendar):
        """
        IT-TSK-007: Create task with invalid data
        
        Precondition: Calendar exists
        Input: POST /tasks with missing required fields
        Expected: Returns 422 validation error
        """
        invalid_data = {
            "calendar_id": str(sample_calendar.id),
            # Missing required fields: title, date
        }
        
        response = await client.post("/tasks", json=invalid_data)
        
        assert response.status_code == 422


class TestTasksRouterUpdate:
    """Test cases for PATCH /tasks/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_task_success(self, client: AsyncClient, sample_task):
        """
        IT-TSK-008: Update task with valid data
        
        Precondition: Task exists
        Input: PATCH /tasks/{id} with update data
        Expected: Returns updated task with 200 status
        """
        update_data = {"title": "Updated via API"}
        
        response = await client.patch(f"/tasks/{sample_task.id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated via API"

    @pytest.mark.asyncio
    async def test_update_task_status(self, client: AsyncClient, sample_task):
        """
        IT-TSK-009: Update task status
        
        Precondition: Task exists with status 'pending'
        Input: PATCH /tasks/{id} with status='completed'
        Expected: Returns task with updated status
        """
        update_data = {"status": "completed"}
        
        response = await client.patch(f"/tasks/{sample_task.id}", json=update_data)
        
        assert response.status_code == 200
        assert response.json()["status"] == "completed"

    @pytest.mark.asyncio
    async def test_update_task_not_found(self, client: AsyncClient):
        """
        IT-TSK-010: Update non-existent task
        
        Precondition: None
        Input: PATCH /tasks/{random_uuid} with update data
        Expected: Returns 404
        """
        update_data = {"title": "New Title"}
        
        response = await client.patch(f"/tasks/{uuid.uuid4()}", json=update_data)
        
        assert response.status_code == 404


class TestTasksRouterComplete:
    """Test cases for POST /tasks/{id}/complete endpoint."""

    @pytest.mark.asyncio
    async def test_complete_task_success(self, client: AsyncClient, sample_task):
        """
        IT-TSK-011: Mark task as completed
        
        Precondition: Task exists with status 'pending'
        Input: POST /tasks/{id}/complete
        Expected: Returns task with status 'completed'
        """
        response = await client.post(f"/tasks/{sample_task.id}/complete")
        
        assert response.status_code == 200
        assert response.json()["status"] == "completed"

    @pytest.mark.asyncio
    async def test_complete_task_not_found(self, client: AsyncClient):
        """
        IT-TSK-012: Complete non-existent task
        
        Precondition: None
        Input: POST /tasks/{random_uuid}/complete
        Expected: Returns 404
        """
        response = await client.post(f"/tasks/{uuid.uuid4()}/complete")
        
        assert response.status_code == 404


class TestTasksRouterDelete:
    """Test cases for DELETE /tasks/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_soft_delete_task(self, client: AsyncClient, sample_task):
        """
        IT-TSK-013: Soft delete task
        
        Precondition: Task exists
        Input: DELETE /tasks/{id}?soft=true
        Expected: Returns 204, task marked as cancelled
        """
        response = await client.delete(f"/tasks/{sample_task.id}?soft=true")
        
        assert response.status_code == 204
        
        # Verify task still exists but is cancelled
        get_response = await client.get(f"/tasks/{sample_task.id}")
        assert get_response.status_code == 200
        assert get_response.json()["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_delete_task_not_found(self, client: AsyncClient):
        """
        IT-TSK-014: Delete non-existent task
        
        Precondition: None
        Input: DELETE /tasks/{random_uuid}
        Expected: Returns 404
        """
        response = await client.delete(f"/tasks/{uuid.uuid4()}")
        
        assert response.status_code == 404
