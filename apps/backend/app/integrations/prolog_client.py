"""Prolog client for constraint checking via subprocess."""

import asyncio
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

from app.agent.config import get_agent_settings


class PrologClient:
    """Client for interacting with Prolog knowledge base."""

    def __init__(
        self,
        kb_path: Optional[str] = None,
        mode: str = "subprocess",
        service_url: str = "http://localhost:8081",
    ):
        """Initialize Prolog client.

        Args:
            kb_path: Path to Prolog KB directory
            mode: "subprocess" or "service"
            service_url: URL for Prolog service (if mode="service")
        """
        settings = get_agent_settings()
        self.mode = mode or settings.prolog_mode
        self.service_url = service_url or settings.prolog_service_url

        # Resolve KB path
        if kb_path:
            self.kb_path = Path(kb_path)
        else:
            # Default: relative to backend app
            self.kb_path = Path(__file__).parent.parent.parent.parent / "prolog"

        self.main_file = self.kb_path / "main.pl"

    async def query(self, query_str: str) -> Dict[str, Any]:
        """Execute a Prolog query.

        Args:
            query_str: Prolog query string

        Returns:
            Query result as dictionary
        """
        if self.mode == "service":
            return await self._query_service(query_str)
        return await self._query_subprocess(query_str)

    async def _query_subprocess(self, query_str: str) -> Dict[str, Any]:
        """Execute query via SWI-Prolog subprocess.

        Args:
            query_str: Prolog query

        Returns:
            Query result
        """
        if not self.main_file.exists():
            return {
                "success": False,
                "error": f"Prolog KB not found at {self.main_file}",
            }

        # Build SWI-Prolog command
        # Use JSON output for structured results
        prolog_cmd = f"""
            consult('{self.main_file.as_posix()}'),
            catch(
                (
                    {query_str},
                    writeln('SUCCESS')
                ),
                Error,
                (
                    format('ERROR: ~w~n', [Error])
                )
            ),
            halt.
        """

        try:
            process = await asyncio.create_subprocess_exec(
                "swipl",
                "-q",
                "-g",
                prolog_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.kb_path),
            )

            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10.0)

            output = stdout.decode("utf-8").strip()
            error = stderr.decode("utf-8").strip()

            if "SUCCESS" in output:
                return {"success": True, "output": output}
            elif "ERROR" in output or error:
                return {"success": False, "error": error or output}
            else:
                return {"success": True, "output": output}

        except asyncio.TimeoutError:
            return {"success": False, "error": "Prolog query timed out"}
        except FileNotFoundError:
            return {"success": False, "error": "SWI-Prolog (swipl) not found in PATH"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _query_service(self, query_str: str) -> Dict[str, Any]:
        """Execute query via Prolog HTTP service.

        Args:
            query_str: Prolog query

        Returns:
            Query result
        """
        import httpx

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.service_url}/query",
                    json={"query": query_str},
                    timeout=10.0,
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def check_overlap(
        self,
        calendar_id: str,
        start_time: str,
        end_time: str,
        exclude_event_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Check for scheduling conflicts.

        Args:
            calendar_id: Calendar ID
            start_time: Event start (ISO format)
            end_time: Event end (ISO format)
            exclude_event_id: Event to exclude from check

        Returns:
            Conflict check result
        """
        if exclude_event_id:
            query = f"check_event_conflicts('{calendar_id}', '{start_time}', '{end_time}', '{exclude_event_id}', Result)"
        else:
            query = f"check_overlap('{calendar_id}', '{start_time}', '{end_time}', Result)"

        return await self.query(query)

    async def find_free_slots(
        self,
        calendar_id: str,
        start_date: str,
        end_date: str,
        duration_minutes: int,
    ) -> Dict[str, Any]:
        """Find available time slots.

        Args:
            calendar_id: Calendar ID
            start_date: Start of range (YYYY-MM-DD)
            end_date: End of range (YYYY-MM-DD)
            duration_minutes: Required slot duration

        Returns:
            Free slots result
        """
        query = f"find_free_slots('{calendar_id}', '{start_date}', '{end_date}', {duration_minutes}, Slots)"
        return await self.query(query)

    async def is_available(self) -> bool:
        """Check if Prolog is available.

        Returns:
            True if Prolog can be reached
        """
        try:
            result = await self.query("true")
            return result.get("success", False)
        except Exception:
            return False


@lru_cache
def get_prolog_client() -> PrologClient:
    """Get cached Prolog client instance."""
    return PrologClient()
