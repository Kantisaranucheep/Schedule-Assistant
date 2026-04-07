"""
Tests for Health Check endpoint.

Test ID Format: IT-HLT-XXX
"""

import pytest
from httpx import AsyncClient


class TestHealthRouter:
    """Test cases for Health Check endpoints."""

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """
        IT-HLT-001: Health check returns healthy status
        
        Precondition: Application is running
        Input: GET /health
        Expected: Returns 200 with status 'healthy'
        """
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client: AsyncClient):
        """
        IT-HLT-002: Root endpoint returns API info
        
        Precondition: Application is running
        Input: GET /
        Expected: Returns 200 with app name and version
        """
        response = await client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "docs" in data
