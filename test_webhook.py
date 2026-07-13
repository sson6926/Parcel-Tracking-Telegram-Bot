#!/usr/bin/env python3
"""Test webhook configuration"""

import os
import sys
from app.config.settings import (
    get_bot_mode,
    get_webhook_url,
    get_webhook_path,
    get_webhook_port,
    get_webhook_secret
)

def test_webhook_config():
    """Test webhook configuration"""
    print("Testing Webhook Configuration")
    print("=" * 50)
    
    # Set test environment
    os.environ['BOT_MODE'] = 'webhook'
    os.environ['WEBHOOK_URL'] = 'https://example.com'
    os.environ['WEBHOOK_SECRET'] = 'test_secret_123'
    
    # Test functions
    print(f"Bot Mode: {get_bot_mode()}")
    print(f"Webhook URL: {get_webhook_url()}")
    print(f"Webhook Path: {get_webhook_path()}")
    print(f"Webhook Port: {get_webhook_port()}")
    print(f"Webhook Secret: {'***' + get_webhook_secret()[-4:] if get_webhook_secret() else 'Not set'}")
    
    # Test URL construction
    if get_webhook_url():
        full_url = f"{get_webhook_url().rstrip('/')}{get_webhook_path()}"
        print(f"Full Webhook URL: {full_url}")
    
    print("\n" + "=" * 50)
    
    # Test polling mode
    os.environ['BOT_MODE'] = 'polling'
    os.environ.pop('WEBHOOK_URL', None)
    print(f"\nTesting Polling Mode:")
    print(f"Bot Mode: {get_bot_mode()}")
    print(f"Should use polling: {get_bot_mode().lower() != 'webhook' or not get_webhook_url()}")
    
    return True

if __name__ == "__main__":
    try:
        test_webhook_config()
        print("\n✅ Webhook configuration test passed!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)