import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, date
import uuid

# --- CONFIGURATION: Replace with your actual service account key file ---
SERVICE_ACCOUNT_KEY_PATH = 'aqua-7ced9-firebase-adminsdk-fbsvc-d94e9eb953.json'
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

# =========================================================================
# CONFIGURATION: Define Users and Their Accounts
# =========================================================================

# Define multiple users with unique accounts
USERS_CONFIG = [
    {
        "user_id": f"USER_{uuid.uuid4().hex[:8].upper()}",
        "account_id": f"ACC_{uuid.uuid4().hex[:8].upper()}",
        "first_name": "Marlo",
        "last_name": "Gallego",
        "email": "marlo@example.com",
        "password_hash": "securepasswordhash1",  # NEVER store plain passwords in production!
        "device_name": "AquaSolar Unit 1",
        "admin_number": "+639850326985"
    },
    {
        "user_id": f"USER_{uuid.uuid4().hex[:8].upper()}",
        "account_id": f"ACC_{uuid.uuid4().hex[:8].upper()}",
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "password_hash": "securepasswordhash2",
        "device_name": "AquaSolar Unit 2",
        "admin_number": "+639850326986"
    },
    {
        "user_id": f"USER_{uuid.uuid4().hex[:8].upper()}",
        "account_id": f"ACC_{uuid.uuid4().hex[:8].upper()}",
        "first_name": "Jane",
        "last_name": "Smith",
        "email": "jane@example.com",
        "password_hash": "securepasswordhash3",
        "device_name": "AquaSolar Unit 3",
        "admin_number": "+639850326987"
    }
]

# =========================================================================
# Helper Functions
# =========================================================================

def create_user_and_account(user_config):
    """Create a user and their associated account with all subcollections"""
    user_id = user_config["user_id"]
    account_id = user_config["account_id"]
    
    print(f"\n{'='*60}")
    print(f"Creating user: {user_config['first_name']} {user_config['last_name']}")
    print(f"User ID: {user_id}")
    print(f"Account ID: {account_id}")
    print(f"{'='*60}")
    
    # 1. Create User Document
    user_data = {
        "user_id": user_id,
        "first_name": user_config["first_name"],
        "last_name": user_config["last_name"],
        "email": user_config["email"],
        "password_hash": user_config["password_hash"],
        "account_id_fk": account_id
    }
    db.collection('users').document(user_id).set(user_data)
    print(f"✅ User created: {user_config['email']}")
    
    # 2. Create Account Document
    account_data = {
        "account_id": account_id,
        "user_id_fk": user_id,
        "active": True,
        "device_name": user_config["device_name"],
        "admin_number": user_config["admin_number"]
    }
    db.collection('accounts').document(account_id).set(account_data)
    print(f"✅ Account created: {user_config['device_name']}")
    
    # 3. Create Sensors for this account (matching original schema)
    sensors_data = [
        {
            "sensor_id": f"SENS_FLOW_IN_{account_id}",
            "account_id_fk": account_id,
            "sensor_type": "Flow In",
            "unit": "Liters/Minute"
        },
        {
            "sensor_id": f"SENS_BATTERY_{account_id}",
            "account_id_fk": account_id,
            "sensor_type": "Battery Voltage",
            "unit": "Volts"
        }
    ]
    
    for sensor in sensors_data:
        db.collection('sensors').document(sensor["sensor_id"]).set(sensor)
    print(f"✅ {len(sensors_data)} sensors created")
    
    # 4. Initialize Account Subcollections
    account_ref = db.collection('accounts').document(account_id)
    
    # 4a. Real-Time Status (CRITICAL for ESP32/Flask communication)
    # Matches original schema exactly
    realtime_status_data = {
        "flow_in_L_min": 5.5,
        "flow_out_L_min": 5.4,
        "volume_in_L": 0.0,
        "volume_out_L": 0.0,
        "battery_percent": 95,
        "battery_voltage_V": 12.6,
        "current_A": 0.0,
        "pump_state": "OFF",
        "leakage_detected": False,
        "last_update": firestore.SERVER_TIMESTAMP
    }
    account_ref.collection('realtime_status').document('current').set(realtime_status_data)
    print(f"✅ Real-time status initialized")
    
    # 4b. Commands Document (CRITICAL for pump control - matching original format)
    command_data = {
        "action": "NONE",
        "timestamp": datetime.utcnow(),
        "status": "executed"
    }
    account_ref.collection('commands').document('control').set(command_data)
    print(f"✅ Commands document initialized")
    
    # 4c. Sample Sensor Logs (matching original format)
    sensor_log_data = [
        {
            "log_id": f"LOG_{uuid.uuid4().hex[:8].upper()}",
            "sensor_id_fk": f"SENS_FLOW_IN_{account_id}",
            "timestamp": datetime.utcnow(),
            "reading_value": 5.5,
            "unit": "L/min"
        },
        {
            "log_id": f"LOG_{uuid.uuid4().hex[:8].upper()}",
            "sensor_id_fk": f"SENS_FLOW_IN_{account_id}",
            "timestamp": datetime.utcnow(),
            "reading_value": 5.6,
            "unit": "L/min"
        }
    ]
    
    for log in sensor_log_data:
        account_ref.collection('sensor_logs').add(log)
    print(f"✅ {len(sensor_log_data)} sample sensor logs added")
    
    # 4d. Sample Control Logs (matching original format)
    control_log_data = [
        {
            "control_id": f"CTRL_{uuid.uuid4().hex[:8].upper()}",
            "control_time": datetime.utcnow(),
            "action": "TURN_ON",
            "method": "SMS",
            "details": "Command received while offline"
        }
    ]
    
    for log in control_log_data:
        account_ref.collection('control_logs').add(log)
    print(f"✅ {len(control_log_data)} sample control logs added")
    
    # 4e. Sample Power Logs (matching original format)
    power_status_data = [
        {
            "power_id": f"PWR_{uuid.uuid4().hex[:8].upper()}",
            "power_level_V": 12.3,
            "current_A": 0.5,
            "battery_percent": 95,
            "recorded_at": datetime.utcnow()
        }
    ]
    
    for log in power_status_data:
        account_ref.collection('power_logs').add(log)
    print(f"✅ {len(power_status_data)} sample power logs added")
    
    # 4f. Sample Alerts (matching original format)
    alerts_data = [
        {
            "alert_id": f"ALERT_{uuid.uuid4().hex[:8].upper()}",
            "alert_type": "Leakage",
            "alert_date": datetime.utcnow(),
            "status": "Active",
            "details": "Flow In and Flow Out differential exceeded threshold."
        }
    ]
    
    for alert in alerts_data:
        account_ref.collection('alerts').add(alert)
    print(f"✅ {len(alerts_data)} sample alerts added")
    
    # 4g. Sample Consumption Data (matching original format)
    consumption_data = [
        {
            "cons_id": f"CONS_{uuid.uuid4().hex[:8].upper()}",
            "consumption_date": date.today().isoformat(),
            "consumption_total": 1200.5,
            "pump_cycles": 15,
            "last_updated": firestore.SERVER_TIMESTAMP
        }
    ]
    
    for cons in consumption_data:
        account_ref.collection('consumption').document(cons["consumption_date"]).set(cons)
    print(f"✅ {len(consumption_data)} consumption records initialized")
    
    print(f"✅ ALL subcollections initialized for {account_id}")
    print(f"\n🎉 User {user_config['email']} setup complete!\n")

def cleanup_existing_data():
    """Optional: Clean up existing data before populating"""
    print("\n⚠️  CLEANUP WARNING ⚠️")
    print("This will delete ALL existing users and accounts!")
    response = input("Do you want to proceed with cleanup? (yes/no): ")
    
    if response.lower() != 'yes':
        print("Cleanup cancelled.")
        return False
    
    print("\n🗑️  Deleting existing users...")
    users = db.collection('users').stream()
    user_count = 0
    for user in users:
        user.reference.delete()
        user_count += 1
    print(f"✅ Deleted {user_count} users")
    
    print("🗑️  Deleting existing accounts...")
    accounts = db.collection('accounts').stream()
    account_count = 0
    for account in accounts:
        # Delete all subcollections
        account_id = account.id
        
        # Delete subcollections
        subcollections = ['realtime_status', 'commands', 'sensor_logs', 
                         'control_logs', 'power_logs', 'alerts', 'consumption']
        
        for subcol in subcollections:
            docs = db.collection('accounts').document(account_id).collection(subcol).stream()
            for doc in docs:
                doc.reference.delete()
        
        # Delete account document
        account.reference.delete()
        account_count += 1
    print(f"✅ Deleted {account_count} accounts")
    
    print("🗑️  Deleting existing sensors...")
    sensors = db.collection('sensors').stream()
    sensor_count = 0
    for sensor in sensors:
        sensor.reference.delete()
        sensor_count += 1
    print(f"✅ Deleted {sensor_count} sensors")
    
    return True

# =========================================================================
# SCRIPT EXECUTION
# =========================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🌊 AquaSolar Multi-User Firebase Setup")
    print("=" * 70)
    
    # Ask if user wants to cleanup first
    cleanup = input("\nDo you want to clean up existing data first? (yes/no): ")
    if cleanup.lower() == 'yes':
        if cleanup_existing_data():
            print("\n✅ Cleanup completed!\n")
    
    # Create all users and their accounts
    print(f"\n📝 Creating {len(USERS_CONFIG)} users with unique accounts...\n")
    
    for user_config in USERS_CONFIG:
        try:
            create_user_and_account(user_config)
        except Exception as e:
            print(f"❌ Error creating user {user_config['email']}: {e}")
    
    print("\n" + "=" * 70)
    print("✅ Firebase Firestore Multi-User Setup Complete!")
    print("=" * 70)
    
    print("\n📋 SUMMARY:")
    print(f"   • {len(USERS_CONFIG)} users created")
    print(f"   • {len(USERS_CONFIG)} unique accounts created")
    print(f"   • Each account has its own:")
    print(f"      - Real-time status")
    print(f"      - Command controls")
    print(f"      - Sensor logs")
    print(f"      - Power logs")
    print(f"      - Alerts")
    print(f"      - Consumption tracking")
    
    print("\n🔑 LOGIN CREDENTIALS:")
    for user in USERS_CONFIG:
        print(f"\n   Email: {user['email']}")
        print(f"   Password: {user['password_hash']}")
        print(f"   Account ID: {user['account_id']}")
        print(f"   Device: {user['device_name']}")
    
    print("\n⚠️  IMPORTANT NOTES:")
    print("   1. Each ESP32 device must be configured with its unique Account ID")
    print("   2. Update your ESP32 code to include the account_id in API calls")
    print("   3. Users can only see data from their own account")
    print("   4. Use proper password hashing (bcrypt) in production!")
    
    print("\n📱 ESP32 Configuration Example:")
    print("   ACCOUNT_ID = 'ACC_XXXXXXXX'  # Get from Firebase Console")
    print("   # Include in status updates:")
    print("   data = {'account_id': ACCOUNT_ID, 'flow_in_L_min': 5.5, ...}")
    
    print("\n" + "=" * 70 + "\n")