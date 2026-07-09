"""Test setup."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.update({
    "BUSINESS_ID": "test-business",
    "BUSINESS_NAME": "Sohaib Systems",
    "BUSINESS_PHONE": "+15550001111",
    "ALLOWED_ORIGINS": "http://testserver,http://localhost:8005",
    "JWT_SECRET": "test-secret",
    "ADMIN_API_KEY": "test-admin",
    "SUPABASE_URL": "",
    "SUPABASE_KEY": "",
    "SMS_DRY_RUN": "true",
    "MAX_MESSAGES_PER_IP_MINUTE": "1000",
})
