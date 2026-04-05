import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(id_str) for id_str in os.getenv("ADMIN_IDS", "").split(",") if id_str.strip()]

GOOGLE_SHEETS_FILE_ID = os.getenv("GOOGLE_SHEETS_FILE_ID")
SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE", "service_account.json")

MAX_HOURS_PER_DAY = 10
MAX_HOURS_PER_WEEK = 40
TRAVEL_TIME_MINUTES = 30

RESPONSE_TIMEOUT_HOURS = 1

CALC_CONFIG = {
    "base_price": 85.0,
    "price_per_bathroom": 25.0,
    "price_per_window": 12.0,
    "room_coefficients": {
        1: 1.0,
        2: 1.4,
        3: 1.8,
        4: 2.2
    },
    "extra_services": {
        "холодильник": 15.0,
        "духовка": 15.0,
        "балкон": 20.0,
        "микроволновка": 10.0,
        "вытяжка": 15.0
    }
}

ROLE_CLIENT = "client"
ROLE_STAFF = "staff"
ROLE_ADMIN = "admin"

ORDER_STATUS_AWAITING = "awaiting_assignment"
ORDER_STATUS_ASSIGNED = "assigned"
ORDER_STATUS_IN_PROGRESS = "in_progress"
ORDER_STATUS_COMPLETED = "completed"
ORDER_STATUS_CANCELLED = "cancelled"