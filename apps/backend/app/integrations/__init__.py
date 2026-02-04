# apps/backend/app/integrations/__init__.py
"""External integrations module."""

from app.integrations.prolog_client import PrologClient, get_prolog_client

__all__ = ["PrologClient", "get_prolog_client"]
