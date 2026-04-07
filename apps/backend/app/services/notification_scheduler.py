"""
Notification Scheduler Service.

Uses APScheduler to periodically check for upcoming events and send notifications.
"""

import uuid
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.config import get_settings
from app.core.timezone import now as tz_now, get_system_timezone
from app.models import Event, UserSettings, User, Calendar
from app.services.email_service import get_email_service
from app.services.notification_storage import get_notification_storage

logger = logging.getLogger(__name__)


@dataclass
class ScheduledNotification:
    """Represents a scheduled notification to be sent."""
    event_id: str
    user_id: str
    email: str
    event_title: str
    event_start: datetime
    event_location: Optional[str]
    minutes_before: int
    notification_time: datetime  # When to send the notification


class NotificationScheduler:
    """
    Scheduler for sending event notifications.
    
    Checks for upcoming events and sends email notifications based on user preferences.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.scheduler = AsyncIOScheduler()
        self.email_service = get_email_service()
        self.storage = get_notification_storage()
        
        # Track sent notifications to avoid duplicates
        # Key: "{event_id}_{minutes_before}" 
        self._sent_notifications: Set[str] = set()
        
        # Database session factory
        self._engine = None
        self._session_factory = None
    
    def _get_notification_key(self, event_id: str, minutes_before: int) -> str:
        """Generate a unique key for tracking sent notifications."""
        return f"{event_id}_{minutes_before}"
    
    async def _get_session(self) -> AsyncSession:
        """Get a database session."""
        if self._engine is None:
            self._engine = create_async_engine(self.settings.database_url)
            self._session_factory = async_sessionmaker(
                self._engine, 
                class_=AsyncSession, 
                expire_on_commit=False
            )
        return self._session_factory()
    
    async def check_and_send_notifications(self):
        """
        Main job: Check for upcoming events and send notifications.
        
        This method is called periodically by the scheduler.
        """
        try:
            logger.debug("Checking for upcoming event notifications...")
            
            # Get all users with notifications enabled from file storage
            enabled_users = self.storage.get_all_enabled_users()
            
            if not enabled_users:
                logger.debug("No users with notifications enabled")
                return
            
            current_time = tz_now()
            
            async with await self._get_session() as session:
                for user_prefs in enabled_users:
                    try:
                        await self._process_user_notifications(
                            session, user_prefs, current_time
                        )
                    except Exception as e:
                        logger.error(f"Error processing notifications for user {user_prefs.get('user_id')}: {e}")
        
        except Exception as e:
            logger.error(f"Error in notification check job: {e}")
    
    async def _process_user_notifications(
        self,
        session: AsyncSession,
        user_prefs: Dict[str, Any],
        current_time: datetime
    ):
        """Process notifications for a single user."""
        user_id = user_prefs.get("user_id")
        email = user_prefs.get("email")
        notification_times = user_prefs.get("notification_times", [])
        
        if not email or not notification_times:
            return
        
        # Get user's calendar(s)
        try:
            user_uuid = uuid.UUID(user_id)
        except (ValueError, TypeError):
            logger.warning(f"Invalid user_id format: {user_id}")
            return
        
        # Query for upcoming events within the next 24 hours + buffer
        max_minutes = max(t.get("minutes_before", 0) for t in notification_times) if notification_times else 1440
        
        # Look ahead window
        window_start = current_time
        window_end = current_time + timedelta(minutes=max_minutes + 5)  # +5 min buffer
        
        # Query events
        query = (
            select(Event)
            .join(Calendar)
            .where(
                and_(
                    Calendar.user_id == user_uuid,
                    Event.start_time >= window_start,
                    Event.start_time <= window_end,
                    Event.status == "confirmed"
                )
            )
        )
        
        result = await session.execute(query)
        events = result.scalars().all()
        
        for event in events:
            for time_pref in notification_times:
                minutes_before = time_pref.get("minutes_before", 0)
                
                # Calculate when notification should be sent
                notification_time = event.start_time - timedelta(minutes=minutes_before)
                
                # Check if it's time to send (within 1 minute window)
                time_diff = (notification_time - current_time).total_seconds() / 60
                
                if -1 <= time_diff <= 1:  # Within 1 minute of notification time
                    notification_key = self._get_notification_key(str(event.id), minutes_before)
                    
                    if notification_key not in self._sent_notifications:
                        # Send notification
                        success = self.email_service.send_event_notification(
                            to_email=email,
                            event_title=event.title,
                            event_start=event.start_time,
                            event_location=event.location,
                            minutes_before=minutes_before
                        )
                        
                        if success:
                            self._sent_notifications.add(notification_key)
                            logger.info(
                                f"Sent notification for event '{event.title}' "
                                f"({minutes_before} min before) to {email}"
                            )
                        else:
                            logger.warning(
                                f"Failed to send notification for event '{event.title}' to {email}"
                            )
    
    def start(self):
        """Start the notification scheduler."""
        if self.scheduler.running:
            logger.warning("Scheduler already running")
            return
        
        # Add the periodic job
        self.scheduler.add_job(
            self.check_and_send_notifications,
            trigger=IntervalTrigger(seconds=self.settings.notification_check_interval_seconds),
            id="notification_check",
            name="Check and send event notifications",
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info(
            f"Notification scheduler started "
            f"(checking every {self.settings.notification_check_interval_seconds} seconds)"
        )
    
    def stop(self):
        """Stop the notification scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Notification scheduler stopped")
    
    def clear_sent_cache(self):
        """Clear the sent notifications cache. Useful for testing."""
        self._sent_notifications.clear()


# Singleton instance
_scheduler: Optional[NotificationScheduler] = None


def get_notification_scheduler() -> NotificationScheduler:
    """Get the notification scheduler singleton."""
    global _scheduler
    if _scheduler is None:
        _scheduler = NotificationScheduler()
    return _scheduler


def start_notification_scheduler():
    """Start the notification scheduler."""
    scheduler = get_notification_scheduler()
    scheduler.start()


def stop_notification_scheduler():
    """Stop the notification scheduler."""
    scheduler = get_notification_scheduler()
    scheduler.stop()
