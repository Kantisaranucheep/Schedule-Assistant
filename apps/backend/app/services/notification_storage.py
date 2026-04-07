"""
Notification preferences file storage.

Saves and loads user notification preferences to/from a text file.
This provides a simple file-based backup of notification settings.
"""

import json
import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Default storage directory (relative to backend app)
DEFAULT_STORAGE_DIR = Path(__file__).parent.parent / "data"
NOTIFICATION_PREFS_FILE = "notification_preferences.txt"


class NotificationPreferencesStorage:
    """File-based storage for notification preferences."""
    
    def __init__(self, storage_dir: Optional[Path] = None):
        """
        Initialize the storage.
        
        Args:
            storage_dir: Directory to store the preferences file. 
                        Defaults to app/data/
        """
        self.storage_dir = storage_dir or DEFAULT_STORAGE_DIR
        self.file_path = self.storage_dir / NOTIFICATION_PREFS_FILE
        
        # Ensure storage directory exists
        self._ensure_directory()
    
    def _ensure_directory(self):
        """Create storage directory if it doesn't exist."""
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create storage directory: {e}")
    
    def _load_all_preferences(self) -> Dict[str, Any]:
        """Load all preferences from file."""
        if not self.file_path.exists():
            return {"users": {}, "last_updated": None}
        
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if not content.strip():
                    return {"users": {}, "last_updated": None}
                return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse preferences file: {e}")
            return {"users": {}, "last_updated": None}
        except Exception as e:
            logger.error(f"Failed to load preferences file: {e}")
            return {"users": {}, "last_updated": None}
    
    def _save_all_preferences(self, data: Dict[str, Any]):
        """Save all preferences to file."""
        try:
            data["last_updated"] = datetime.now().isoformat()
            
            with open(self.file_path, 'w', encoding='utf-8') as f:
                # Write as pure JSON (remove comments that break JSON parsing)
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved notification preferences to {self.file_path}")
        except Exception as e:
            logger.error(f"Failed to save preferences file: {e}")
    
    def save_user_preferences(
        self,
        user_id: str,
        email: Optional[str],
        notifications_enabled: bool,
        window_notifications_enabled: bool,
        notification_times: List[Dict[str, Any]]
    ):
        """
        Save a user's notification preferences.
        
        Args:
            user_id: User ID (as string)
            email: User's notification email
            notifications_enabled: Whether email notifications are enabled
            window_notifications_enabled: Whether window notifications are enabled
            notification_times: List of notification time preferences
                               Each item: {"minutes_before": int, "label": str}
        """
        data = self._load_all_preferences()
        
        data["users"][user_id] = {
            "email": email,
            "notifications_enabled": notifications_enabled,
            "window_notifications_enabled": window_notifications_enabled,
            "notification_times": notification_times,
            "updated_at": datetime.now().isoformat()
        }
        
        self._save_all_preferences(data)
    
    def get_user_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a user's notification preferences.
        
        Args:
            user_id: User ID (as string)
            
        Returns:
            User preferences dict or None if not found
        """
        data = self._load_all_preferences()
        return data["users"].get(user_id)
    
    def get_all_enabled_users(self) -> List[Dict[str, Any]]:
        """
        Get all users with notifications enabled.
        
        Returns:
            List of user preferences with user_id included
        """
        data = self._load_all_preferences()
        enabled = []
        
        for user_id, prefs in data["users"].items():
            if prefs.get("notifications_enabled") and prefs.get("email"):
                enabled.append({
                    "user_id": user_id,
                    **prefs
                })
        
        return enabled
    
    def delete_user_preferences(self, user_id: str):
        """
        Delete a user's notification preferences.
        
        Args:
            user_id: User ID (as string)
        """
        data = self._load_all_preferences()
        
        if user_id in data["users"]:
            del data["users"][user_id]
            self._save_all_preferences(data)


# Singleton instance
_storage: Optional[NotificationPreferencesStorage] = None


def get_notification_storage() -> NotificationPreferencesStorage:
    """Get the notification storage singleton."""
    global _storage
    if _storage is None:
        _storage = NotificationPreferencesStorage()
    return _storage
