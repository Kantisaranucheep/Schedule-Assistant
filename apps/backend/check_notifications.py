"""
Check notification system status.
Run this script to verify notifications are configured correctly.
"""
import sys
import os
from pathlib import Path

# Add app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.notification_storage import get_notification_storage
from app.services.email_service import get_email_service

def main():
    print("=" * 60)
    print("NOTIFICATION SYSTEM STATUS CHECK")
    print("=" * 60)
    print()
    
    # Check email service
    print("📧 EMAIL SERVICE")
    print("-" * 60)
    email_service = get_email_service()
    if email_service.is_configured():
        print("✅ Email service is CONFIGURED")
        config = email_service._get_config_status()
        print(f"   Host: {config['SMTP_HOST']}")
        print(f"   Port: {config['SMTP_PORT']}")
        print(f"   Username: {config['SMTP_USERNAME']}")
        print(f"   From: {config['SMTP_FROM_EMAIL']}")
    else:
        print("❌ Email service is NOT configured")
        print(email_service.get_config_error_message())
    print()
    
    # Check notification storage
    print("📁 NOTIFICATION STORAGE")
    print("-" * 60)
    storage = get_notification_storage()
    print(f"Storage path: {storage.file_path}")
    
    if storage.file_path.exists():
        print("✅ Notification preferences file EXISTS")
        enabled_users = storage.get_all_enabled_users()
        print(f"   Users with notifications enabled: {len(enabled_users)}")
        print()
        
        if enabled_users:
            print("   User details:")
            for user in enabled_users:
                print(f"   - User ID: {user['user_id']}")
                print(f"     Email: {user['email']}")
                print(f"     Enabled: {user['notifications_enabled']}")
                print(f"     Notification times: {user['notification_times']}")
                print()
        else:
            print("   ⚠️  No users have notifications enabled")
    else:
        print("❌ Notification preferences file DOES NOT EXIST")
        print("   This means:")
        print("   1. No notification settings have been saved yet")
        print("   2. OR there was an error creating the file")
        print()
        print("   To fix: Go to the app and save your notification settings")
    
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    all_good = email_service.is_configured() and storage.file_path.exists() and len(storage.get_all_enabled_users()) > 0
    
    if all_good:
        print("✅ All systems are GO! Notifications should work.")
        print()
        print("If you still don't receive notifications:")
        print("1. Make sure you have upcoming events in your calendar")
        print("2. Events must be within your notification window")
        print("3. Check backend logs for any errors")
    else:
        print("❌ Notifications are NOT fully configured.")
        print()
        print("Next steps:")
        if not email_service.is_configured():
            print("1. Configure SMTP settings in .env file")
        if not storage.file_path.exists() or len(storage.get_all_enabled_users()) == 0:
            print("2. Go to the app and save your notification settings")
        print("3. Restart the backend server")
        print("4. Run this script again to verify")

if __name__ == "__main__":
    main()
