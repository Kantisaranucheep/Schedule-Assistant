"""Tests for authentication endpoints."""

import pytest
from httpx import AsyncClient


class TestAuthRouter:
    """Test cases for auth endpoints."""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, sample_user):
        response = await client.post(
            "/auth/login",
            json={
                "username": sample_user.username,
                "password": sample_user.password,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == sample_user.username
        assert data["email"] == sample_user.email
        assert data["message"] == "Login successful"

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client: AsyncClient, sample_user):
        response = await client.post(
            "/auth/login",
            json={
                "username": sample_user.username,
                "password": "wrong-password",
            },
        )

        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Invalid username or password"
