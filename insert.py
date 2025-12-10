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

# =========================================================================
# HELPER FUNCTIONS
# =========================================================================

def get_user_by_email(email):
    """Get user document by email to find their account_id"""
    try:
        users = db.collection('users').where('email', '==', email).limit(1).stream()
        for user in users:
            user_data = user.to_dict()
            user_data['user_id'] = user.id
            return user_data
        return None
    except Exception as e:
        print(f"❌ Error getting user: {e}")
        return None

def get_account_id_by_email(email):
    """Get account ID from user email"""
    user = get_user_by_email(email)
    if user:
        return user.get('account_id_fk')
    return None

def insert_sensor_logs_interactive(account_id):
    """Insert sensor logs with user input"""
    print(f"\n📊 Adding Sensor Logs")
    print(f"{'='*50}")
    
    more = True
    count = 0
    
    while more:
        try:
            print(f"\n--- Sensor Log #{count + 1} ---")
            
            sensor_id = input(f"Sensor ID (default: SENS_FLOW_IN_{account_id}): ").strip()
            if not sensor_id:
                sensor_id = f"SENS_FLOW_IN_{account_id}"
            
            reading_value = float(input("Reading Value (e.g., 5.5): "))
            unit = input("Unit (default: L/min): ").strip() or "L/min"
            
            # Create log entry
            log_data = {
                "log_id": f"LOG_{uuid.uuid4().hex[:8].upper()}",
                "sensor_id_fk": sensor_id,
                "timestamp": datetime.utcnow(),
                "reading_value": reading_value,
                "unit": unit
            }
            
            # Insert into Firebase
            db.collection('accounts').document(account_id).collection('sensor_logs').add(log_data)
            print(f"✅ Sensor log added!")
            count += 1
            
            # Ask if user wants to add more
            add_more = input("\nAdd another sensor log? (yes/no): ").strip().lower()
            more = add_more == 'yes'
        
        except ValueError:
            print("❌ Invalid input! Please enter valid numbers.")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print(f"\n✅ Inserted {count} sensor logs")

def insert_control_logs_interactive(account_id):
    """Insert control logs with user input"""
    print(f"\n⚙️  Adding Control Logs")
    print(f"{'='*50}")
    
    more = True
    count = 0
    
    while more:
        try:
            print(f"\n--- Control Log #{count + 1} ---")
            
            print("Action options: TURN_ON, TURN_OFF")
            action = input("Action: ").strip().upper()
            if action not in ["TURN_ON", "TURN_OFF"]:
                print("⚠️  Using default: TURN_ON")
                action = "TURN_ON"
            
            print("Method options: Manual, Remote, SMS, Scheduled")
            method = input("Method: ").strip()
            if not method:
                method = "Manual"
            
            details = input("Details (e.g., Command received while offline): ").strip()
            if not details:
                details = f"Pump {action} via {method}"
            
            # Create log entry
            log_data = {
                "control_id": f"CTRL_{uuid.uuid4().hex[:8].upper()}",
                "control_time": datetime.utcnow(),
                "action": action,
                "method": method,
                "details": details
            }
            
            # Insert into Firebase
            db.collection('accounts').document(account_id).collection('control_logs').add(log_data)
            print(f"✅ Control log added!")
            count += 1
            
            # Ask if user wants to add more
            add_more = input("\nAdd another control log? (yes/no): ").strip().lower()
            more = add_more == 'yes'
        
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print(f"\n✅ Inserted {count} control logs")

def insert_power_logs_interactive(account_id):
    """Insert power logs with user input"""
    print(f"\n🔋 Adding Power Logs")
    print(f"{'='*50}")
    
    more = True
    count = 0
    
    while more:
        try:
            print(f"\n--- Power Log #{count + 1} ---")
            
            voltage = float(input("Voltage (V) (e.g., 12.3): "))
            current = float(input("Current (A) (e.g., 0.5): "))
            battery_percent = int(input("Battery Percentage (0-100) (e.g., 95): "))
            
            # Validate battery percentage
            if not (0 <= battery_percent <= 100):
                print("⚠️  Battery percentage must be between 0-100. Using 95.")
                battery_percent = 95
            
            # Create log entry
            log_data = {
                "power_id": f"PWR_{uuid.uuid4().hex[:8].upper()}",
                "power_level_V": voltage,
                "current_A": current,
                "battery_percent": battery_percent,
                "recorded_at": datetime.utcnow()
            }
            
            # Insert into Firebase
            db.collection('accounts').document(account_id).collection('power_logs').add(log_data)
            print(f"✅ Power log added!")
            count += 1
            
            # Ask if user wants to add more
            add_more = input("\nAdd another power log? (yes/no): ").strip().lower()
            more = add_more == 'yes'
        
        except ValueError:
            print("❌ Invalid input! Please enter valid numbers.")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print(f"\n✅ Inserted {count} power logs")

def insert_alerts_interactive(account_id):
    """Insert alerts with user input"""
    print(f"\n🚨 Adding Alerts")
    print(f"{'='*50}")
    
    more = True
    count = 0
    
    alert_types = ["Leakage", "Low Battery", "High Temperature", "Pump Malfunction", "Custom"]
    
    while more:
        try:
            print(f"\n--- Alert #{count + 1} ---")
            
            print("Alert Type options:")
            for i, alert_type in enumerate(alert_types, 1):
                print(f"  {i}. {alert_type}")
            
            choice = input("Select alert type (1-5): ").strip()
            if choice.isdigit() and 1 <= int(choice) <= 5:
                if int(choice) == 5:
                    alert_type = input("Enter custom alert type: ").strip()
                else:
                    alert_type = alert_types[int(choice) - 1]
            else:
                print("⚠️  Using default: Leakage")
                alert_type = "Leakage"
            
            print("Status options: Active, Resolved")
            status = input("Status (Active/Resolved): ").strip()
            if status not in ["Active", "Resolved"]:
                status = "Active"
            
            details = input("Details (e.g., Flow differential exceeded threshold): ").strip()
            if not details:
                details = f"{alert_type} alert triggered"
            
            # Create alert entry
            alert_data = {
                "alert_id": f"ALERT_{uuid.uuid4().hex[:8].upper()}",
                "alert_type": alert_type,
                "alert_date": datetime.utcnow(),
                "status": status,
                "details": details
            }
            
            # Insert into Firebase
            db.collection('accounts').document(account_id).collection('alerts').add(alert_data)
            print(f"✅ Alert added!")
            count += 1
            
            # Ask if user wants to add more
            add_more = input("\nAdd another alert? (yes/no): ").strip().lower()
            more = add_more == 'yes'
        
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print(f"\n✅ Inserted {count} alerts")

def insert_consumption_data_interactive(account_id):
    """Insert consumption data with user input"""
    print(f"\n💧 Adding Consumption Data")
    print(f"{'='*50}")
    
    more = True
    count = 0
    
    while more:
        try:
            print(f"\n--- Consumption Record #{count + 1} ---")
            
            consumption_date = input("Consumption Date (YYYY-MM-DD) (default: today): ").strip()
            if not consumption_date:
                consumption_date = date.today().isoformat()
            else:
                # Validate date format
                date.fromisoformat(consumption_date)
            
            consumption_total = float(input("Total Consumption (L) (e.g., 1200.5): "))
            pump_cycles = int(input("Pump Cycles (e.g., 15): "))
            
            # Create consumption entry
            consumption_data = {
                "cons_id": f"CONS_{uuid.uuid4().hex[:8].upper()}",
                "consumption_date": consumption_date,
                "consumption_total": consumption_total,
                "pump_cycles": pump_cycles,
                "last_updated": firestore.SERVER_TIMESTAMP
            }
            
            # Insert into Firebase using date as document ID
            db.collection('accounts').document(account_id).collection('consumption').document(consumption_date).set(consumption_data)
            print(f"✅ Consumption record added for {consumption_date}!")
            count += 1
            
            # Ask if user wants to add more
            add_more = input("\nAdd another consumption record? (yes/no): ").strip().lower()
            more = add_more == 'yes'
        
        except ValueError as e:
            print(f"❌ Invalid input! {e}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print(f"\n✅ Inserted {count} consumption records")

# =========================================================================
# SCRIPT EXECUTION
# =========================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🌊 AquaSolar Interactive Data Insertion Tool")
    print("=" * 70)
    
    # Get account ID
    choice = input("\nFind account by:\n1. Email\n2. Account ID\nEnter choice (1 or 2): ").strip()
    
    account_id = None
    
    if choice == "1":
        email = input("Enter user email: ").strip()
        account_id = get_account_id_by_email(email)
        if not account_id:
            print(f"❌ User with email '{email}' not found!")
            exit()
        print(f"✅ Found account: {account_id}")
    
    elif choice == "2":
        account_id = input("Enter account ID: ").strip()
        # Verify account exists
        account_doc = db.collection('accounts').document(account_id).get()
        if not account_doc.exists:
            print(f"❌ Account '{account_id}' not found!")
            exit()
        print(f"✅ Account found!")
    
    else:
        print("❌ Invalid choice!")
        exit()
    
    # Menu for what to insert
    while True:
        print("\n" + "=" * 70)
        print("What data would you like to insert?")
        print("=" * 70)
        print("1. Sensor Logs")
        print("2. Control Logs")
        print("3. Power Logs")
        print("4. Alerts")
        print("5. Consumption Data")
        print("6. Exit")
        
        choice = input("\nEnter choice (1-6): ").strip()
        
        if choice == "1":
            insert_sensor_logs_interactive(account_id)
        elif choice == "2":
            insert_control_logs_interactive(account_id)
        elif choice == "3":
            insert_power_logs_interactive(account_id)
        elif choice == "4":
            insert_alerts_interactive(account_id)
        elif choice == "5":
            insert_consumption_data_interactive(account_id)
        elif choice == "6":
            print("\n✅ Exiting. Goodbye!")
            break
        else:
            print("❌ Invalid choice! Please try again.")
    
    print("\n" + "=" * 70 + "\n")