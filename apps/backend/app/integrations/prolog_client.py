# apps/backend/app/integrations/prolog_client.py
"""Prolog integration client - supports subprocess and service modes."""

import asyncio
import json
import os
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from app.agent.config import get_agent_settings
from app.agent.exceptions import PrologExecutionError


class BasePrologClient(ABC):
    """Abstract base class for Prolog clients."""

    @abstractmethod
    async def query(self, query: str) -> Any:
        """Execute a Prolog query.

        Args:
            query: Prolog query string

        Returns:
            Query result
        """
        pass

    @abstractmethod
    async def assert_fact(self, fact: str) -> bool:
        """Assert a new fact into the knowledge base.

        Args:
            fact: Prolog fact to assert

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def retract_fact(self, fact: str) -> bool:
        """Retract a fact from the knowledge base.

        Args:
            fact: Prolog fact to retract

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if Prolog service is available."""
        pass


class SubprocessPrologClient(BasePrologClient):
    """Prolog client using swipl subprocess.

    This client executes Prolog queries by spawning swipl processes.
    Suitable for local development when swipl is installed.
    """

    def __init__(self, kb_path: Optional[str] = None):
        """Initialize subprocess client.

        Args:
            kb_path: Path to Prolog knowledge base directory
        """
        settings = get_agent_settings()

        # Resolve KB path
        if kb_path:
            self.kb_path = Path(kb_path)
        else:
            # Default: apps/prolog relative to workspace root
            backend_dir = Path(__file__).parent.parent.parent
            self.kb_path = backend_dir.parent.parent / "prolog"

        self.main_file = self.kb_path / "main.pl"

    async def query(self, query: str) -> Any:
        """Execute a Prolog query via subprocess.

        Args:
            query: Prolog query (without trailing period)

        Returns:
            Query result as parsed JSON or string
        """
        # Ensure query ends with period
        if not query.strip().endswith("."):
            query = query.strip() + "."

        # Build swipl command
        # Use -g to run query and halt
        cmd = [
            "swipl",
            "-s", str(self.main_file),
            "-g", f"({query}), halt",
            "-t", "halt(1)",  # Exit with 1 if goal fails
        ]

        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=str(self.kb_path),
                ),
            )

            if result.returncode == 0:
                output = result.stdout.strip()
                # Try to parse as JSON if it looks like JSON
                if output.startswith("{") or output.startswith("["):
                    try:
                        return json.loads(output)
                    except json.JSONDecodeError:
                        pass
                return {"success": True, "output": output}
            else:
                return {
                    "success": False,
                    "error": result.stderr.strip() or "Query failed",
                }

        except subprocess.TimeoutExpired:
            raise PrologExecutionError(query, "Query timeout")
        except FileNotFoundError:
            raise PrologExecutionError(query, "swipl not found - is SWI-Prolog installed?")
        except Exception as e:
            raise PrologExecutionError(query, str(e))

    async def assert_fact(self, fact: str) -> bool:
        """Assert a fact via subprocess."""
        query = f"assertz({fact})"
        result = await self.query(query)
        return result.get("success", False)

    async def retract_fact(self, fact: str) -> bool:
        """Retract a fact via subprocess."""
        query = f"retract({fact})"
        result = await self.query(query)
        return result.get("success", False)

    async def is_available(self) -> bool:
        """Check if swipl is available."""
        try:
            result = subprocess.run(
                ["swipl", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False


class ServicePrologClient(BasePrologClient):
    """Prolog client using HTTP service.

    This client communicates with a Prolog microservice via HTTP.
    Suitable for production deployments.
    """

    def __init__(self, service_url: Optional[str] = None):
        """Initialize service client.

        Args:
            service_url: Prolog service base URL
        """
        settings = get_agent_settings()
        self.service_url = service_url or settings.prolog_service_url

    async def query(self, query: str) -> Any:
        """Execute a Prolog query via HTTP service.

        Args:
            query: Prolog query string

        Returns:
            Query result from service
        """
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.service_url}/query",
                    json={"query": query},
                )
                response.raise_for_status()
                return response.json()
        except httpx.ConnectError:
            raise PrologExecutionError(query, "Prolog service unavailable")
        except httpx.HTTPStatusError as e:
            raise PrologExecutionError(query, f"Service error: {e.response.status_code}")
        except Exception as e:
            raise PrologExecutionError(query, str(e))

    async def assert_fact(self, fact: str) -> bool:
        """Assert a fact via HTTP service."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.service_url}/assert",
                    json={"fact": fact},
                )
                response.raise_for_status()
                return response.json().get("success", False)
        except Exception:
            return False

    async def retract_fact(self, fact: str) -> bool:
        """Retract a fact via HTTP service."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.service_url}/retract",
                    json={"fact": fact},
                )
                response.raise_for_status()
                return response.json().get("success", False)
        except Exception:
            return False

    async def is_available(self) -> bool:
        """Check if Prolog service is available."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.service_url}/health")
                return response.status_code == 200
        except Exception:
            return False


class MockPrologClient(BasePrologClient):
    """Mock Prolog client for testing."""

    def __init__(self):
        self.facts: List[str] = []

    async def query(self, query: str) -> Any:
        """Return mock query result."""
        # Simple mock responses based on query content
        if "check_overlap" in query:
            return {"success": True, "has_overlap": False, "conflicts": []}
        elif "find_free_slots" in query:
            return {
                "success": True,
                "slots": [
                    {"start": "09:00", "end": "10:00"},
                    {"start": "14:00", "end": "15:00"},
                ],
            }
        return {"success": True, "result": "mock"}

    async def assert_fact(self, fact: str) -> bool:
        """Add fact to mock knowledge base."""
        self.facts.append(fact)
        return True

    async def retract_fact(self, fact: str) -> bool:
        """Remove fact from mock knowledge base."""
        if fact in self.facts:
            self.facts.remove(fact)
            return True
        return False

    async def is_available(self) -> bool:
        """Mock client is always available."""
        return True


# Client instance cache
_prolog_client: Optional[BasePrologClient] = None


def get_prolog_client() -> BasePrologClient:
    """Factory function to get the appropriate Prolog client.

    Returns:
        Configured Prolog client based on settings
    """
    global _prolog_client

    if _prolog_client is not None:
        return _prolog_client

    settings = get_agent_settings()

    if settings.prolog_mode == "service":
        _prolog_client = ServicePrologClient()
    else:
        _prolog_client = SubprocessPrologClient()

    return _prolog_client


def reset_prolog_client() -> None:
    """Reset the cached Prolog client (useful for testing)."""
    global _prolog_client
    _prolog_client = None
