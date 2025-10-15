import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, date
import uuid

# --- CONFIGURATION: Replace with your actual service account key file ---
SERVICE_ACCOUNT_KEY_PATH = 'aquasolar-10c88-firebase-adminsdk-fbsvc-650df625a1.json'
# --- END CONFIGURATION ---

try:
    # Initialize Firebase Admin
    cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Firebase initialized.")
except Exception as e:
    print(f"❌ Error initializing Firebase: {e}")
    print("Please ensure your service account key file path is correct.")
    exit()

# Define UUIDs for linking relationships
USER_ID = str(uuid.uuid4())
ACCOUNT_ID = "ACC001" # Fixed ID is better for initial device setup
SENSOR_ID_FLOW_IN = "SENS_FLOW_IN"
SENSOR_ID_BATTERY = "SENS_BATTERY"


# =========================================================================
# 1. Top-Level Collections (Users, Accounts, Static Sensors)
#    These collections are indexed by their primary IDs (PKs).
# =========================================================================

# --- User (PK: UserID, Owns Account) ---
users_data = {
    USER_ID: {
        "user_id": USER_ID,
        "first_name": "Marlo",
        "last_name": "Gallego",
        "email": "marlo@example.com",
        "password_hash": "securepasswordhash", # NEVER store plain passwords
        "account_id_fk": ACCOUNT_ID # Foreign Key link to Account
    }
}

# --- Account (PK: AccountID, Central Hub for the Device) ---
accounts_data = {
    ACCOUNT_ID: {
        "account_id": ACCOUNT_ID,
        "user_id_fk": USER_ID,
        "active": True,
        "device_name": "AquaSolar Unit 1",
        "admin_number": "+639850326985"
    }
}

# --- Sensor (PK: SensorID, Metadata for all sensors) ---
sensors_data = {
    SENSOR_ID_FLOW_IN: {
        "sensor_id": SENSOR_ID_FLOW_IN,
        "account_id_fk": ACCOUNT_ID,
        "sensor_type": "Flow In",
        "unit": "Liters/Minute"
    },
    SENSOR_ID_BATTERY: {
        "sensor_id": SENSOR_ID_BATTERY, # FIXED: Changed from SENS_BATTERY to SENSOR_ID_BATTERY
        "account_id_fk": ACCOUNT_ID,
        "sensor_type": "Battery Voltage",
        "unit": "Volts"
    }
}


# =========================================================================
# 2. Sub-Collections (Time-Series & Logs)
#    These are nested under /accounts/{AccountID}
# =========================================================================

# --- Sensor_Log (Generates - high frequency readings) ---
sensor_log_data = [
    {
        "log_id": str(uuid.uuid4()),
        "sensor_id_fk": SENSOR_ID_FLOW_IN,
        "timestamp": datetime.utcnow(),
        "reading_value": 5.5,
        "unit": "L/min"
    },
    {
        "log_id": str(uuid.uuid4()),
        "sensor_id_fk": SENSOR_ID_FLOW_IN,
        "timestamp": datetime.utcnow(),
        "reading_value": 5.6,
        "unit": "L/min"
    }
]

# --- Pump_Control_Log (Controls - history of commands) ---
control_log_data = [
    {
        "control_id": str(uuid.uuid4()),
        "control_time": datetime.utcnow(),
        "action": "TURN_ON",
        "method": "SMS",
        "details": "Command received while offline"
    }
]

# --- Power_Status (Records - battery/power logs) ---
power_status_data = [
    {
        "power_id": str(uuid.uuid4()),
        "power_level_V": 12.3, # Voltage (Level)
        "current_A": 0.5,      # Current
        "recorded_at": datetime.utcnow()
    }
]

# --- Alert (Receives - leakage, low power) ---
alerts_data = [
    {
        "alert_id": str(uuid.uuid4()),
        "alert_type": "Leakage",
        "alert_date": datetime.utcnow(),
        "status": "Active",
        "details": "Flow In and Flow Out differential exceeded threshold."
    }
]

# --- Consumption (Consumes - summarized daily usage) ---
consumption_data = [
    {
        "cons_id": str(uuid.uuid4()),
        "consumption_date": date.today().isoformat(),
        "consumption_total": 1200.5, # Total liters today
        "pump_cycles": 15
    }
]


# =========================================================================
# 3. Real-Time Communication Documents (CRITICAL for ESP32/Flask)
#    These are single documents used for high-speed read/write.
# =========================================================================

# --- Real-Time Status Document (Updated frequently by ESP32) ---
realtime_status_data = {
    "flow_in_L_min": 5.5,
    "flow_out_L_min": 5.4,
    "battery_percent": 95,
    "pump_state": "ON",
    "leakage_detected": False,
    "last_update": firestore.SERVER_TIMESTAMP
}

# --- Command Document (Written by Flask, Polled by ESP32) ---
command_data = {
    "action": "NONE", # Can be 'ON', 'OFF', or 'NONE'
    "timestamp": datetime.utcnow(),
    "status": "executed" # Status can be 'pending', 'executed'
}


# =========================================================================
# Execution Functions
# =========================================================================

def populate_top_level(collection_name, data, doc_id_field):
    """Adds documents to top-level collections, using specified ID field."""
    print(f"--- Populating /{collection_name} ---")
    collection_ref = db.collection(collection_name)
    for doc_id, doc_data in data.items():
        # Ensure the document has a unique ID from the data dictionary
        collection_ref.document(doc_id).set(doc_data)
    print(f"[{len(data)}] documents added to /{collection_name}.")


def populate_sub_collection(account_id, sub_collection_name, data):
    """Adds documents to a sub-collection nested under /accounts/{AccountID}."""
    print(f"--- Populating /accounts/{account_id}/{sub_collection_name} ---")
    sub_collection_ref = db.collection('accounts').document(account_id).collection(sub_collection_name)
    
    # Logs are pushed with an auto-generated ID (add())
    for doc in data:
        sub_collection_ref.add(doc)
    print(f"[{len(data)}] documents added to {sub_collection_name}.")


def populate_single_document(account_id, sub_collection_name, doc_id, data):
    """Sets the data for a single, fixed document (e.g., control/status)."""
    collection_ref = db.collection('accounts').document(account_id).collection(sub_collection_name)
    collection_ref.document(doc_id).set(data)
    print(f"--- Set /accounts/{account_id}/{sub_collection_name}/{doc_id} ---")


# =========================================================================
# SCRIPT EXECUTION
# =========================================================================

# 1. Top-Level Collections
populate_top_level("users", users_data, "user_id")
populate_top_level("accounts", accounts_data, "account_id")
populate_top_level("sensors", sensors_data, "sensor_id")

# 2. Sub-Collections (Linked to ACC001)
populate_sub_collection(ACCOUNT_ID, "sensor_logs", sensor_log_data)
populate_sub_collection(ACCOUNT_ID, "control_logs", control_log_data)
populate_sub_collection(ACCOUNT_ID, "power_logs", power_status_data)
populate_sub_collection(ACCOUNT_ID, "alerts", alerts_data)
populate_sub_collection(ACCOUNT_ID, "consumption", consumption_data)

# 3. Real-Time Communication Documents
# The ESP32 and Flask will constantly read/write to these fixed paths.
populate_single_document(ACCOUNT_ID, "realtime_status", "current", realtime_status_data)
populate_single_document(ACCOUNT_ID, "commands", "control", command_data)

print("\n✅ Firebase Firestore schema and sample data successfully populated!")
