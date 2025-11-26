from flask import Flask, render_template, redirect, request, session, url_for, jsonify
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta
import os
import uuid
import time

app = Flask(__name__)
CORS(app)  # Enable CORS for ESP32 communication

# Secret configuration
SECRET_TOKEN = os.environ.get("SECRET_TOKEN", "12345678")
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey")

# ------------------------------- 
# 🔥 Firebase Initialization
# ------------------------------- 
try:
    # For Render deployment, use environment variable for credentials
    if os.environ.get("FIREBASE_CREDENTIALS"):
        import json
        cred_dict = json.loads(os.environ.get("FIREBASE_CREDENTIALS"))
        cred = credentials.Certificate(cred_dict)
    else:
        # For local development, use service account file
        cred = credentials.Certificate('aqua-7ced9-firebase-adminsdk-fbsvc-d94e9eb953.json')
    
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Firebase initialized successfully")
except Exception as e:
    print(f"❌ Firebase initialization error: {e}")
    db = None

# ------------------------------- 
# 📊 Cache and Throttling Configuration
# ------------------------------- 
# Cache to prevent duplicate/excessive writes (per account)
account_cache = {}

def get_account_cache(account_id):
    """Get or create cache for a specific account"""
    if account_id not in account_cache:
        account_cache[account_id] = {
            'last_sensor_log_time': 0,
            'last_power_log_time': 0,
            'last_consumption_update_time': 0,
            'last_logged_values': {}
        }
    return account_cache[account_id]

# Thresholds for significant changes (only log when exceeded)
FLOW_CHANGE_THRESHOLD = 0.5      # L/min
BATTERY_CHANGE_THRESHOLD = 5     # percent
VOLTAGE_CHANGE_THRESHOLD = 0.3   # volts

# Logging intervals (in seconds)
SENSOR_LOG_INTERVAL = 300        # Log sensor data every 5 minutes
POWER_LOG_INTERVAL = 600         # Log power data every 10 minutes
CONSUMPTION_UPDATE_INTERVAL = 1800  # Update consumption every 30 minutes

# ------------------------------- 
# 🔹 Session Helper Functions
# ------------------------------- 
def get_current_account_id():
    """Get the account ID of the currently logged-in user"""
    return session.get('account_id', None)

def get_current_admin_number():
    """Get the admin number of the currently logged-in user"""
    return session.get('admin_number', "+639850326985")

def require_login():
    """Check if user is logged in"""
    if "user" not in session or not get_current_account_id():
        return False
    return True

# ------------------------------- 
# 🔹 Firebase Helper Functions
# ------------------------------- 
def get_account_ref(account_id=None):
    """Get reference to the main account document"""
    if account_id is None:
        account_id = get_current_account_id()
    
    if not account_id:
        raise ValueError("No account ID provided or in session")
    
    return db.collection('accounts').document(account_id)

def get_subcollection(subcollection_name, account_id=None):
    """Get reference to a subcollection under the account"""
    return get_account_ref(account_id).collection(subcollection_name)

def is_significant_change(new_value, old_value, threshold):
    """Check if value changed significantly"""
    if old_value is None:
        return True
    return abs(new_value - old_value) >= threshold

def add_sensor_log(sensor_id, reading_value, unit="L/min", account_id=None):
    """Add a sensor reading to the sensor_logs subcollection"""
    try:
        log_data = {
            "log_id": f"LOG_{uuid.uuid4().hex[:8].upper()}",
            "sensor_id_fk": sensor_id,
            "timestamp": firestore.SERVER_TIMESTAMP,
            "reading_value": reading_value,
            "unit": unit
        }
        get_subcollection('sensor_logs', account_id).add(log_data)
        print(f"✅ Sensor log added for {account_id or 'current account'}: {reading_value} {unit}")
    except Exception as e:
        print(f"Error adding sensor log: {e}")

def add_control_log(action, method="Manual", account_id=None):
    """Add a pump control event to control_logs"""
    try:
        log_data = {
            "control_id": f"CTRL_{uuid.uuid4().hex[:8].upper()}",
            "control_time": firestore.SERVER_TIMESTAMP,
            "action": action,
            "method": method,
            "details": f"Pump {action} via {method}"
        }
        get_subcollection('control_logs', account_id).add(log_data)
        print(f"✅ Control log added for {account_id or 'current account'}: {action}")
    except Exception as e:
        print(f"Error adding control log: {e}")

def add_power_log(voltage, current, battery_percent, account_id=None):
    """Add battery/power reading to power_logs"""
    try:
        log_data = {
            "power_id": f"PWR_{uuid.uuid4().hex[:8].upper()}",
            "power_level_V": voltage,
            "current_A": current,
            "battery_percent": battery_percent,
            "recorded_at": firestore.SERVER_TIMESTAMP
        }
        get_subcollection('power_logs', account_id).add(log_data)
        print(f"✅ Power log added for {account_id or 'current account'}: {battery_percent}%")
    except Exception as e:
        print(f"Error adding power log: {e}")

def add_alert(alert_type, details, status="Active", account_id=None):
    """Add an alert to the alerts subcollection"""
    try:
        alert_data = {
            "alert_id": f"ALERT_{uuid.uuid4().hex[:8].upper()}",
            "alert_type": alert_type,
            "alert_date": firestore.SERVER_TIMESTAMP,
            "status": status,
            "details": details
        }
        get_subcollection('alerts', account_id).add(alert_data)
        print(f"🚨 Alert added for {account_id or 'current account'}: {alert_type}")
    except Exception as e:
        print(f"Error adding alert: {e}")

def update_consumption_batch(volume_in, pump_cycles=1, account_id=None):
    """Update consumption using Firebase increments for efficiency"""
    try:
        today = datetime.now().date().isoformat()
        doc_ref = get_subcollection('consumption', account_id).document(today)
        doc = doc_ref.get()
        
        if doc.exists:
            # Use Firebase Increment for atomic updates
            doc_ref.update({
                'consumption_total': firestore.Increment(volume_in),
                'pump_cycles': firestore.Increment(pump_cycles),
                'last_updated': firestore.SERVER_TIMESTAMP
            })
            print(f"✅ Consumption updated for {account_id or 'current account'}: +{volume_in}L")
        else:
            # Create new document for today
            doc_ref.set({
                "cons_id": f"CONS_{uuid.uuid4().hex[:8].upper()}",
                "consumption_date": today,
                "consumption_total": volume_in,
                "pump_cycles": pump_cycles,
                'last_updated': firestore.SERVER_TIMESTAMP
            })
            print(f"✅ Consumption created for {account_id or 'current account'} on {today}: {volume_in}L")
    except Exception as e:
        print(f"Error updating consumption: {e}")

def is_esp32_online(account_id=None):
    """Check if ESP32 is online based on last update time"""
    try:
        status = get_realtime_status(account_id)
        if not status:
            return False
        
        last_update = status.get('last_update')
        if not last_update:
            return False
        
        # ESP32 is considered online if it updated within the last 60 seconds
        time_diff = datetime.now() - last_update
        return time_diff.total_seconds() < 60
    except Exception as e:
        print(f"Error checking ESP32 status: {e}")
        return False

def get_consumption_summary(account_id=None):
    """Calculate consumption for today, week, and month"""
    try:
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        consumption_ref = get_subcollection('consumption', account_id)
        all_records = consumption_ref.get()
        
        today_total = 0
        week_total = 0
        month_total = 0
        
        for doc in all_records:
            data = doc.to_dict()
            try:
                date_str = data.get('consumption_date')
                record_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                consumption = data.get('consumption_total', 0)
                
                if record_date == today:
                    today_total += consumption
                if week_ago <= record_date <= today:
                    week_total += consumption
                if month_ago <= record_date <= today:
                    month_total += consumption
            except Exception:
                continue
        
        return {
            "consumption_day": round(today_total, 2),
            "consumption_week": round(week_total, 2),
            "consumption_month": round(month_total, 2)
        }
    except Exception as e:
        print(f"Error calculating consumption: {e}")
        return {
            "consumption_day": 0,
            "consumption_week": 0,
            "consumption_month": 0
        }

def get_realtime_status(account_id=None):
    """Get current real-time status from Firebase"""
    try:
        status_doc = get_subcollection('realtime_status', account_id).document('current').get()
        if status_doc.exists:
            return status_doc.to_dict()
        return None
    except Exception as e:
        print(f"Error getting realtime status: {e}")
        return None

def update_realtime_status(data, account_id=None):
    """Update the real-time status document"""
    try:
        data['last_update'] = firestore.SERVER_TIMESTAMP
        data['esp32_online'] = True  # Mark ESP32 as online when it sends data
        get_subcollection('realtime_status', account_id).document('current').set(data, merge=True)
    except Exception as e:
        print(f"Error updating realtime status: {e}")

def get_command(account_id=None):
    """Get the current command for ESP32"""
    try:
        cmd_doc = get_subcollection('commands', account_id).document('control').get()
        if cmd_doc.exists:
            return cmd_doc.to_dict()
        return None
    except Exception as e:
        print(f"Error getting command: {e}")
        return None

def set_command(action, account_id=None):
    """Set a command for ESP32 to execute"""
    try:
        cmd_data = {
            "action": action,
            "timestamp": firestore.SERVER_TIMESTAMP,
            "status": "pending"
        }
        get_subcollection('commands', account_id).document('control').set(cmd_data)
    except Exception as e:
        print(f"Error setting command: {e}")

# ------------------------------- 
# 🔹 User Authentication
# ------------------------------- 
def get_user_by_email(email):
    """Get user from Firebase by email"""
    try:
        users_ref = db.collection('users')
        query = users_ref.where('email', '==', email).limit(1).get()
        if query:
            user_doc = query[0]
            user_data = user_doc.to_dict()
            user_data['doc_id'] = user_doc.id  # Include document ID
            return user_data
        return None
    except Exception as e:
        print(f"Error getting user: {e}")
        return None

# ------------------------------- 
# 🔹 Routes
# ------------------------------- 
@app.route('/')
def index():
    if not require_login():
        return redirect(url_for('login'))
    
    try:
        # Get consumption summary for current user's account
        consumption = get_consumption_summary()
        
        # Get last known status
        status = get_realtime_status()
        if not status:
            status = {
                "pump_state": "N/A",
                "flow_in_L_min": 0,
                "flow_out_L_min": 0,
                "battery_percent": 0,
                "leakage_detected": False,
                "esp32_online": False
            }
        
        # Check if ESP32 is online
        esp32_online = is_esp32_online()
        
        display_status = {
            "pump": status.get("pump_state", "N/A"),
            "flow_in": status.get("flow_in_L_min", 0),
            "flow_out": status.get("flow_out_L_min", 0),
            "volume_in": status.get("volume_in_L", 0),
            "volume_out": status.get("volume_out_L", 0),
            "leakage": status.get("leakage_detected", False),
            "battery_percent": status.get("battery_percent", 0),
            "battery_voltage": status.get("battery_voltage_V", 0),
            "current_consumed": status.get("current_A", 0),
            "esp32_online": esp32_online,  # Add online status
            **consumption
        }
        
        return render_template("dashboard.html", 
                             status=display_status, 
                             user_name=session.get("user_name"),
                             device_name=session.get("device_name", "AquaSolar"),
                             account_id=session.get("account_id"))
    except Exception as e:
        print(f"Error loading dashboard: {e}")
        return render_template("dashboard.html", 
                             status={},
                             user_name=session.get("user_name"),
                             error="Failed to load dashboard data")

# ------------------------------- 
# 🔹 ESP32 Communication Endpoints (OPTIMIZED)
# ------------------------------- 
@app.route("/api/esp32/status", methods=["POST"])
def esp32_status_update():
    """
    Optimized endpoint for ESP32 to push status updates
    Uses smart throttling and change detection to reduce Firebase writes by ~95%
    
    ESP32 should send account_id in the request body or as a query parameter
    """
    try:
        data = request.get_json()
        
        # Get account_id from request (ESP32 must provide this)
        account_id = data.get('account_id') or request.args.get('account_id')
        
        if not account_id:
            return jsonify({"error": "account_id is required"}), 400
        
        # Get cache for this specific account
        cache = get_account_cache(account_id)
        current_time = time.time()
        
        # ✅ ALWAYS update real-time status (this is what dashboard reads)
        update_realtime_status(data, account_id)
        
        # 📊 Log sensor readings ONLY every 5 minutes OR on significant change
        if 'flow_in_L_min' in data:
            should_log_sensor = False
            
            # Check if enough time has passed
            if current_time - cache['last_sensor_log_time'] >= SENSOR_LOG_INTERVAL:
                should_log_sensor = True
                reason = f"Time interval ({SENSOR_LOG_INTERVAL}s)"
            
            # OR check if flow changed significantly
            elif is_significant_change(
                data['flow_in_L_min'], 
                cache['last_logged_values'].get('flow_in_L_min'),
                FLOW_CHANGE_THRESHOLD
            ):
                should_log_sensor = True
                reason = "Significant flow change"
            
            if should_log_sensor:
                add_sensor_log("SENS_FLOW_IN", data['flow_in_L_min'], account_id=account_id)
                cache['last_sensor_log_time'] = current_time
                cache['last_logged_values']['flow_in_L_min'] = data['flow_in_L_min']
                print(f"📊 Sensor logged for {account_id}: {reason}")
        
        # 🔋 Log power status ONLY every 10 minutes OR on significant change
        if all(k in data for k in ['battery_voltage_V', 'current_A', 'battery_percent']):
            should_log_power = False
            
            # Check if enough time has passed
            if current_time - cache['last_power_log_time'] >= POWER_LOG_INTERVAL:
                should_log_power = True
                reason = f"Time interval ({POWER_LOG_INTERVAL}s)"
            
            # OR check if battery dropped significantly
            elif is_significant_change(
                data['battery_percent'],
                cache['last_logged_values'].get('battery_percent'),
                BATTERY_CHANGE_THRESHOLD
            ):
                should_log_power = True
                reason = "Significant battery change"
            
            if should_log_power:
                add_power_log(
                    data['battery_voltage_V'],
                    data['current_A'],
                    data['battery_percent'],
                    account_id=account_id
                )
                cache['last_power_log_time'] = current_time
                cache['last_logged_values']['battery_percent'] = data['battery_percent']
                print(f"🔋 Power logged for {account_id}: {reason}")
        
        # 🚨 Check for alerts (ONLY create if state changed)
        # Leakage alert
        if data.get('leakage_detected', False):
            # Only alert if this is a NEW leakage
            if not cache['last_logged_values'].get('leakage_detected', False):
                add_alert("Leakage", "Flow differential exceeded threshold", account_id=account_id)
        
        cache['last_logged_values']['leakage_detected'] = data.get('leakage_detected', False)
        
        # Low battery alert
        if data.get('battery_percent', 100) <= 10:
            # Only alert once when crossing the 10% threshold
            if cache['last_logged_values'].get('battery_percent', 100) > 10:
                add_alert("Low Battery", f"Battery at {data.get('battery_percent')}%", account_id=account_id)
        
        # 💧 Update daily consumption ONLY every 30 minutes
        if 'volume_in_L' in data:
            if current_time - cache['last_consumption_update_time'] >= CONSUMPTION_UPDATE_INTERVAL:
                update_consumption_batch(data['volume_in_L'], account_id=account_id)
                cache['last_consumption_update_time'] = current_time
                print(f"💧 Consumption updated for {account_id} (30min interval)")
        
        # Check if there's a pending command
        cmd = get_command(account_id)
        response = {"status": "ok"}
        
        if cmd and cmd.get('status') == 'pending':
            response['command'] = cmd.get('action')
        
        return jsonify(response)
        
    except Exception as e:
        print(f"Error in ESP32 status update: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/esp32/command", methods=["GET"])
def esp32_get_command():
    """Endpoint for ESP32 to poll for commands"""
    try:
        # Get account_id from query parameter
        account_id = request.args.get('account_id')
        
        if not account_id:
            return jsonify({"error": "account_id is required"}), 400
        
        cmd = get_command(account_id)
        
        if cmd and cmd.get('status') == 'pending':
            # Mark as delivered
            get_subcollection('commands', account_id).document('control').update({
                'status': 'delivered'
            })
            return jsonify({"command": cmd.get('action')})
        
        return jsonify({"command": "NONE"})
        
    except Exception as e:
        print(f"Error getting command: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/esp32/command/ack", methods=["POST"])
def esp32_command_ack():
    """Endpoint for ESP32 to acknowledge command execution"""
    try:
        data = request.get_json()
        action = data.get('action', 'Unknown')
        account_id = data.get('account_id') or request.args.get('account_id')
        
        if not account_id:
            return jsonify({"error": "account_id is required"}), 400
        
        # Mark command as executed
        get_subcollection('commands', account_id).document('control').update({
            'status': 'executed'
        })
        
        # Log the control action
        add_control_log(action, method="Remote", account_id=account_id)
        
        return jsonify({"status": "acknowledged"})
        
    except Exception as e:
        print(f"Error acknowledging command: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/status-data")
def status_data():
    """Get current status for dashboard"""
    if not require_login():
        return jsonify({"error": "Not logged in"}), 403
    
    try:
        status = get_realtime_status()
        if not status:
            status = {
                "pump_state": "N/A",
                "flow_in_L_min": 0,
                "flow_out_L_min": 0,
                "battery_percent": 0,
                "leakage_detected": False,
                "esp32_online": False
            }
        
        # Check if ESP32 is online
        esp32_online = is_esp32_online()
        
        # Convert to legacy format
        data = {
            "pump": status.get("pump_state", "N/A"),
            "flow_in": status.get("flow_in_L_min", 0),
            "flow_out": status.get("flow_out_L_min", 0),
            "volume_in": status.get("volume_in_L", 0),
            "volume_out": status.get("volume_out_L", 0),
            "leakage": status.get("leakage_detected", False),
            "battery_percent": status.get("battery_percent", 0),
            "battery_voltage": status.get("battery_voltage_V", 0),
            "current_consumed": status.get("current_A", 0),
            "esp32_online": esp32_online  # Add online status
        }
        
        # Merge consumption summary
        data.update(get_consumption_summary())
        
        return jsonify(data)
        
    except Exception as e:
        print(f"Error getting status: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/toggle_pump", methods=["POST"])
def toggle_pump():
    """Toggle pump state via web interface"""
    if not require_login():
        return jsonify({"error": "Not logged in"}), 403
    
    try:
        # Get current user's account ID
        account_id = get_current_account_id()
        
        # Get current status
        status = get_realtime_status(account_id)
        current_state = status.get("pump_state", "OFF") if status else "OFF"
        
        # Toggle state
        new_state = "OFF" if current_state == "ON" else "ON"
        
        # Set command for ESP32 - WITH ACCOUNT ID!
        set_command(new_state, account_id)
        
        # Log the action - WITH ACCOUNT ID!
        add_control_log(f"TURN_{new_state}", method="Manual", account_id=account_id)
        
        print(f"✅ Command set for account {account_id}: {new_state}")
        
        return jsonify({"pump": new_state, "status": "command_sent", "account_id": account_id})
        
    except Exception as e:
        print(f"Error toggling pump: {e}")
        return jsonify({"error": str(e)}), 500

# ------------------------------- 
# 🔹 Authentication Routes
# ------------------------------- 
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        
        user = get_user_by_email(email)
        
        if user and user.get("password_hash") == password:
            # ✅ Store account_id in session
            session["user"] = email
            session["user_name"] = f"{user['first_name']} {user['last_name']}"
            session["account_id"] = user.get("account_id_fk")  # CRITICAL!
            session["user_id"] = user.get("user_id")
            
            # Get account details
            try:
                account_ref = db.collection('accounts').document(user.get("account_id_fk"))
                account_doc = account_ref.get()
                if account_doc.exists:
                    account_data = account_doc.to_dict()
                    session["admin_number"] = account_data.get("admin_number", "+639850326985")
                    session["device_name"] = account_data.get("device_name", "AquaSolar")
                    print(f"✅ User {email} logged in with account {user.get('account_id_fk')}")
            except Exception as e:
                print(f"Error loading account details: {e}")
            
            return redirect(url_for("index"))
        
        return render_template("login.html", error="Invalid email or password")
    
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == 'POST':
        first_name = request.form['firstname']
        last_name = request.form['lastname']
        email = request.form['email']
        password = request.form['password']
        owner_code = request.form['owner_code']
        
        if owner_code != SECRET_TOKEN:
            return render_template("register.html", error="Invalid owner code!")
        
        # Check if user exists
        if get_user_by_email(email):
            return render_template("register.html", error="Email already exists")
        
        # ✅ Create unique account for this user
        try:
            # Generate unique IDs
            user_id = f"USER_{uuid.uuid4().hex[:8].upper()}"
            account_id = f"ACC_{uuid.uuid4().hex[:8].upper()}"  # UNIQUE for each user!
            
            print(f"🆕 Creating new user: {email} with account {account_id}")
            
            # Create account first
            account_data = {
                "account_id": account_id,
                "user_id_fk": user_id,
                "active": True,
                "device_name": f"AquaSolar - {first_name}",
                "admin_number": "+639850326985"  # Default, user can change later
            }
            db.collection('accounts').document(account_id).set(account_data)
            print(f"✅ Account {account_id} created")
            
            # Initialize realtime_status for new account
            db.collection('accounts').document(account_id).collection('realtime_status').document('current').set({
                "flow_in_L_min": 0.0,
                "flow_out_L_min": 0.0,
                "volume_in_L": 0.0,
                "volume_out_L": 0.0,
                "battery_percent": 100,
                "battery_voltage_V": 12.6,
                "current_A": 0.0,
                "pump_state": "OFF",
                "leakage_detected": False,
                "last_update": firestore.SERVER_TIMESTAMP
            })
            print(f"✅ Realtime status initialized for {account_id}")
            
            # Initialize commands document
            db.collection('accounts').document(account_id).collection('commands').document('control').set({
                "action": "NONE",
                "timestamp": firestore.SERVER_TIMESTAMP,
                "status": "executed"
            })
            print(f"✅ Commands initialized for {account_id}")
            
            # Create user with link to new account
            user_data = {
                "user_id": user_id,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "password_hash": password,  # ⚠️ Use bcrypt in production!
                "account_id_fk": account_id  # Link to unique account
            }
            db.collection('users').document(user_id).set(user_data)
            print(f"✅ User {user_id} created and linked to account {account_id}")
            
            return redirect(url_for('login'))
            
        except Exception as e:
            print(f"❌ Error creating user: {e}")
            return render_template("register.html", error="Registration failed. Please try again.")
    
    return render_template("register.html", error=None)

@app.route("/logout")
def logout():
    session.clear()  # Clear all session data
    return redirect(url_for("login"))

# ------------------------------- 
# 🔹 Health Check (for Render)
# ------------------------------- 
@app.route("/health")
def health():
    """Health check endpoint for Render"""
    return jsonify({
        "status": "healthy", 
        "firebase": "connected" if db else "disconnected",
        "optimization": "enabled",
        "multi_user": "enabled"
    })

# ------------------------------- 
# 🔹 Startup
# ------------------------------- 
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("\n" + "=" * 50)
    print("🌊 AquaSolar Flask Server (MULTI-USER)")
    print(f"📊 Sensor logging: Every {SENSOR_LOG_INTERVAL}s")
    print(f"🔋 Power logging: Every {POWER_LOG_INTERVAL}s")
    print(f"💧 Consumption updates: Every {CONSUMPTION_UPDATE_INTERVAL}s")
    print("👥 Multi-user support: ENABLED")
    print("=" * 50 + "\n")
    app.run(host="0.0.0.0", port=port, debug=False)