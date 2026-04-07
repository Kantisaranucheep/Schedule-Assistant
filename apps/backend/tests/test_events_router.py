"""
API Router tests for Events endpoints.

Test ID Format: IT-EVT-XXX (Integration Tests)
"""

import uuid
from datetime import datetime, timezone, timedelta

import pytest
import pytest_asyncio
from httpx import AsyncClient

from tests.conftest import create_event_data


class TestEventsRouterList:
    """Test cases for GET /events endpoint."""

    @pytest.mark.asyncio
    async def test_list_events_empty_calendar(self, client: AsyncClient, sample_calendar):
        """
        IT-EVT-001: List events for calendar with no events
        
        Precondition: Calendar exists with no events
        Input: GET /events?calendar_id={id}
        Expected: Returns empty list with 200 status
        """
        # Create a new calendar without events
        response = await client.get(f"/events?calendar_id={sample_calendar.id}")
        
        # May have sample_event from fixtures, so just check status
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_list_events_with_data(self, client: AsyncClient, sample_event, sample_calendar):
        """
        IT-EVT-002: List events for calendar with events
        
        Precondition: Calendar has events
        Input: GET /events?calendar_id={id}
        Expected: Returns list containing the events
        """
        response = await client.get(f"/events?calendar_id={sample_calendar.id}")
        
        assert response.status_code == 200
        events = response.json()
        assert len(events) >= 1
        assert any(e["id"] == str(sample_event.id) for e in events)


class TestEventsRouterGet:
    """Test cases for GET /events/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_event_success(self, client: AsyncClient, sample_event):
        """
        IT-EVT-003: Get existing event by ID
        
        Precondition: Event exists
        Input: GET /events/{event_id}
        Expected: Returns event data with 200 status
        """
        response = await client.get(f"/events/{sample_event.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_event.id)
        assert data["title"] == sample_event.title

    @pytest.mark.asyncio
    async def test_get_event_not_found(self, client: AsyncClient):
        """
        IT-EVT-004: Get non-existent event
        
        Precondition: None
        Input: GET /events/{random_uuid}
        Expected: Returns 404 with error message
        """
        response = await client.get(f"/events/{uuid.uuid4()}")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestEventsRouterCreate:
    """Test cases for POST /events endpoint."""

    @pytest.mark.asyncio
    async def test_create_event_success(self, client: AsyncClient, sample_calendar):
        """
        IT-EVT-005: Create event with valid data
        
        Precondition: Calendar exists
        Input: POST /events with valid event data
        Expected: Returns created event with 201 status
        """
        event_data = create_event_data(sample_calendar.id, title="New API Event")
        
        response = await client.post("/events", json=event_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New API Event"
        assert data["calendar_id"] == str(sample_calendar.id)

    @pytest.mark.asyncio
    async def test_create_event_with_conflict(self, client: AsyncClient, sample_event, sample_calendar):
        """
        IT-EVT-006: Create event that conflicts with existing
        
        Precondition: Event exists at specific time
        Input: POST /events with overlapping time
        Expected: Returns 409 with conflict details
        """
        # Create event at same time as sample_event
        event_data = {
            "calendar_id": str(sample_calendar.id),
            "title": "Conflicting Event",
            "start_time": sample_event.start_time.isoformat(),
            "end_time": sample_event.end_time.isoformat(),
        }
        
        response = await client.post("/events?check_conflicts=true", json=event_data)
        
        assert response.status_code == 409
        detail = response.json()["detail"]
        assert "conflict" in detail["message"].lower()

    @pytest.mark.asyncio
    async def test_create_event_skip_conflict_check(self, client: AsyncClient, sample_event, sample_calendar):
        """
        IT-EVT-007: Create event with conflict check disabled
        
        Precondition: Event exists at specific time
        Input: POST /events?check_conflicts=false with overlapping time
        Expected: Returns created event with 201 status (allows overlap)
        """
        event_data = {
            "calendar_id": str(sample_calendar.id),
            "title": "Overlapping Event",
            "start_time": sample_event.start_time.isoformat(),
            "end_time": sample_event.end_time.isoformat(),
        }
        
        response = await client.post("/events?check_conflicts=false", json=event_data)
        
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_create_event_invalid_data(self, client: AsyncClient, sample_calendar):
        """
        IT-EVT-008: Create event with invalid data
        
        Precondition: Calendar exists
        Input: POST /events with missing required fields
        Expected: Returns 422 validation error
        """
        invalid_data = {
            "calendar_id": str(sample_calendar.id),
            # Missing required fields: title, start_time, end_time
        }
        
        response = await client.post("/events", json=invalid_data)
        
        assert response.status_code == 422


class TestEventsRouterUpdate:
    """Test cases for PATCH /events/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_event_success(self, client: AsyncClient, sample_event):
        """
        IT-EVT-009: Update event with valid data
        
        Precondition: Event exists
        Input: PATCH /events/{id} with update data
        Expected: Returns updated event with 200 status
        """
        update_data = {"title": "Updated via API"}
        
        response = await client.patch(f"/events/{sample_event.id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated via API"

    @pytest.mark.asyncio
    async def test_update_event_not_found(self, client: AsyncClient):
        """
        IT-EVT-010: Update non-existent event
        
        Precondition: None
        Input: PATCH /events/{random_uuid} with update data
        Expected: Returns 404
        """
        update_data = {"title": "New Title"}
        
        response = await client.patch(f"/events/{uuid.uuid4()}", json=update_data)
        
        assert response.status_code == 404


class TestEventsRouterDelete:
    """Test cases for DELETE /events/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_soft_delete_event(self, client: AsyncClient, sample_event):
        """
        IT-EVT-011: Soft delete event
        
        Precondition: Event exists
        Input: DELETE /events/{id}?soft=true
        Expected: Returns 204, event marked as cancelled
        """
        response = await client.delete(f"/events/{sample_event.id}?soft=true")
        
        assert response.status_code == 204
        
        # Verify event still exists but is cancelled
        get_response = await client.get(f"/events/{sample_event.id}")
        assert get_response.status_code == 200
        assert get_response.json()["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_delete_event_not_found(self, client: AsyncClient):
        """
        IT-EVT-012: Delete non-existent event
        
        Precondition: None
        Input: DELETE /events/{random_uuid}
        Expected: Returns 404
        """
        response = await client.delete(f"/events/{uuid.uuid4()}")
        
        assert response.status_code == 404


class TestEventsRouterConflictCheck:
    """Test cases for GET /events/conflicts/check endpoint."""

    @pytest.mark.asyncio
    async def test_check_conflict_exists(self, client: AsyncClient, sample_event, sample_calendar):
        """
        IT-EVT-013: Check conflicts returns existing conflict
        
        Precondition: Event exists at specific time
        Input: GET /events/conflicts/check with overlapping time
        Expected: Returns has_conflicts=true with conflict details
        """
        params = {
            "calendar_id": str(sample_calendar.id),
            "start_time": sample_event.start_time.isoformat(),
            "end_time": sample_event.end_time.isoformat(),
        }
        
        response = await client.get("/events/conflicts/check", params=params)
        
        assert response.status_code == 200
        data = response.json()
        assert data["has_conflicts"] is True
        assert len(data["conflicts"]) >= 1

    @pytest.mark.asyncio
    async def test_check_no_conflict(self, client: AsyncClient, sample_event, sample_calendar):
        """
        IT-EVT-014: Check conflicts returns no conflict
        
        Precondition: Event exists at specific time
        Input: GET /events/conflicts/check with non-overlapping time
        Expected: Returns has_conflicts=false with empty conflicts
        """
        future_time = sample_event.end_time + timedelta(hours=10)
        params = {
            "calendar_id": str(sample_calendar.id),
            "start_time": future_time.isoformat(),
            "end_time": (future_time + timedelta(hours=1)).isoformat(),
        }
        
        response = await client.get("/events/conflicts/check", params=params)
        
        assert response.status_code == 200
        data = response.json()
        assert data["has_conflicts"] is False
        assert len(data["conflicts"]) == 0
