"""User settings endpoints."""

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import UserSettings
from app.schemas import UserSettingsCreate, UserSettingsUpdate, UserSettingsResponse
from app.services import get_notification_storage, get_email_service

router = APIRouter(prefix="/settings", tags=["settings"])


def _settings_to_response(settings: UserSettings) -> UserSettingsResponse:
    """Convert UserSettings model to response, handling notification_times_json."""
    return UserSettingsResponse.from_orm_with_times(settings)


@router.get("/{user_id}", response_model=UserSettingsResponse)
async def get_settings(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get user settings."""
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    settings = result.scalar_one_or_none()
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")
    return _settings_to_response(settings)


@router.post("", response_model=UserSettingsResponse, status_code=201)
async def create_settings(
    data: UserSettingsCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create user settings."""
    # Convert notification_times to JSON string
    settings_data = data.model_dump(exclude={'notification_times'})
    
    if data.notification_times:
        settings_data['notification_times_json'] = json.dumps([
            t.model_dump() for t in data.notification_times
        ])
    else:
        settings_data['notification_times_json'] = "[]"
    
    settings = UserSettings(**settings_data)
    db.add(settings)
    await db.flush()
    await db.refresh(settings)
    
    # Save to file storage as well
    storage = get_notification_storage()
    storage.save_user_preferences(
        user_id=str(data.user_id),
        email=data.notification_email,
        notifications_enabled=data.notifications_enabled,
        window_notifications_enabled=data.window_notifications_enabled,
        notification_times=[t.model_dump() for t in data.notification_times] if data.notification_times else []
    )
    
    return _settings_to_response(settings)


@router.patch("/{user_id}", response_model=UserSettingsResponse)
async def update_settings(
    user_id: UUID,
    data: UserSettingsUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update user settings."""
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    settings = result.scalar_one_or_none()
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")

    update_data = data.model_dump(exclude_unset=True, exclude={'notification_times'})
    
    # Handle notification_times separately
    if data.notification_times is not None:
        update_data['notification_times_json'] = json.dumps([
            t.model_dump() for t in data.notification_times
        ])
    
    for field, value in update_data.items():
        setattr(settings, field, value)

    await db.flush()
    await db.refresh(settings)

    # Update file storage as well
    storage = get_notification_storage()

    # Parse current notification times for file storage
    notification_times = []
    if settings.notification_times_json:
        try:
            notification_times = json.loads(settings.notification_times_json)
        except json.JSONDecodeError:
            pass

    storage.save_user_preferences(
        user_id=str(user_id),
        email=settings.notification_email,
        notifications_enabled=settings.notifications_enabled,
        window_notifications_enabled=settings.window_notifications_enabled,
        notification_times=notification_times
    )

    return _settings_to_response(settings)


@router.post("/{user_id}/test-email")
async def send_test_email(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Send a test email to the user's notification email."""
    # Get user settings
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    settings = result.scalar_one_or_none()
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")

    if not settings.notification_email:
        raise HTTPException(status_code=400, detail="User email not configured")

    # Send test email
    email_service = get_email_service()
    if not email_service.is_configured():
        error_msg = email_service.get_config_error_message()
        raise HTTPException(status_code=503, detail=error_msg)

    # Send test email
    success, message = email_service.send_email(
        to_email=settings.notification_email,
        subject="📧 Schedule Assistant - Test Email",
        body_html="""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px 10px 0 0; }
                .content { background: #f9f9f9; padding: 20px; border-radius: 0 0 10px 10px; }
                .success { background: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 15px; border-radius: 8px; margin: 20px 0; }
                .footer { text-align: center; margin-top: 20px; color: #666; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✅ Test Email Success!</h1>
                </div>
                <div class="content">
                    <div class="success">
                        <strong>Great news!</strong> Your email is properly configured and working.
                    </div>
                    <p>This is a test email from <strong>Schedule Assistant</strong> to verify that your email notifications are set up correctly.</p>
                    <p>You should now receive event reminders and notifications at this email address when they are triggered.</p>
                    <p style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd;">
                        <strong>Next steps:</strong><br>
                        1. Enable notification preferences in the app<br>
                        2. Set your preferred notification times<br>
                        3. Sit back and receive timely reminders!
                    </p>
                </div>
                <div class="footer">
                    <p>This is an automated test message from Schedule Assistant.</p>
                </div>
            </div>
        </body>
        </html>
        """,
        body_text="""
✅ Test Email Success!

Great news! Your email is properly configured and working.

This is a test email from Schedule Assistant to verify that your email notifications are set up correctly.

You should now receive event reminders and notifications at this email address when they are triggered.

Next steps:
1. Enable notification preferences in the app
2. Set your preferred notification times
3. Sit back and receive timely reminders!

---
This is an automated test message from Schedule Assistant.
        """
    )

    if not success:
        raise HTTPException(status_code=500, detail=message)

    return {"message": "Test email sent successfully", "email": settings.notification_email}
