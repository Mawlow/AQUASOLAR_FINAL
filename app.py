from flask import Flask, render_template, redirect, request, session, url_for, jsonify
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta
import os
import uuid

app = Flask(__name__)
CORS(app)  # Enable CORS for ESP32 communication

# Secret configuration
SECRET_TOKEN = os.environ.get("SECRET_TOKEN", "12345678")
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey")

# Fixed Account ID for the AquaSolar device
ACCOUNT_ID = "ACC001"
ADMIN_NUMBER = "+639850326985"

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
        cred = credentials.Certificate('aquasolar-10c88-firebase-adminsdk-fbsvc-650df625a1.json')
    
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Firebase initialized successfully")
except Exception as e:
    print(f"❌ Firebase initialization error: {e}")
    db = None

# -------------------------------
# 🔹 Firebase Helper Functions
# -------------------------------

def get_account_ref():
    """Get reference to the main account document"""
    return db.collection('accounts').document(ACCOUNT_ID)

def get_subcollection(subcollection_name):
    """Get reference to a subcollection under the account"""
    return get_account_ref().collection(subcollection_name)

def add_sensor_log(sensor_id, reading_value, unit="L/min"):
    """Add a sensor reading to the sensor_logs subcollection"""
    try:
        log_data = {
            "log_id": f"LOG_{uuid.uuid4().hex[:8].upper()}",
            "sensor_id_fk": sensor_id,
            "timestamp": firestore.SERVER_TIMESTAMP,
            "reading_value": reading_value,
            "unit": unit
        }
        get_subcollection('sensor_logs').add(log_data)
    except Exception as e:
        print(f"Error adding sensor log: {e}")

def add_control_log(action, method="Manual"):
    """Add a pump control event to control_logs"""
    try:
        log_data = {
            "control_id": f"CTRL_{uuid.uuid4().hex[:8].upper()}",
            "control_time": firestore.SERVER_TIMESTAMP,
            "action": action,
            "method": method,
            "details": f"Pump {action} via {method}"
        }
        get_subcollection('control_logs').add(log_data)
    except Exception as e:
        print(f"Error adding control log: {e}")

def add_power_log(voltage, current, battery_percent):
    """Add battery/power reading to power_logs"""
    try:
        log_data = {
            "power_id": f"PWR_{uuid.uuid4().hex[:8].upper()}",
            "power_level_V": voltage,
            "current_A": current,
            "battery_percent": battery_percent,
            "recorded_at": firestore.SERVER_TIMESTAMP
        }
        get_subcollection('power_logs').add(log_data)
    except Exception as e:
        print(f"Error adding power log: {e}")

def add_alert(alert_type, details, status="Active"):
    """Add an alert to the alerts subcollection"""
    try:
        alert_data = {
            "alert_id": f"ALERT_{uuid.uuid4().hex[:8].upper()}",
            "alert_type": alert_type,
            "alert_date": firestore.SERVER_TIMESTAMP,
            "status": status,
            "details": details
        }
        get_subcollection('alerts').add(alert_data)
    except Exception as e:
        print(f"Error adding alert: {e}")

def update_consumption(volume_in, pump_cycles=1):
    """Update or create today's consumption record"""
    try:
        today = datetime.now().date().isoformat()
        consumption_ref = get_subcollection('consumption')
        
        # Query for today's record
        query = consumption_ref.where('consumption_date', '==', today).limit(1).get()
        
        if query:
            # Update existing record
            doc = query[0]
            current_data = doc.to_dict()
            doc.reference.update({
                'consumption_total': current_data.get('consumption_total', 0) + volume_in,
                'pump_cycles': current_data.get('pump_cycles', 0) + pump_cycles
            })
        else:
            # Create new record for today
            consumption_data = {
                "cons_id": f"CONS_{uuid.uuid4().hex[:8].upper()}",
                "consumption_date": today,
                "consumption_total": volume_in,
                "pump_cycles": pump_cycles
            }
            consumption_ref.add(consumption_data)
    except Exception as e:
        print(f"Error updating consumption: {e}")

def get_consumption_summary():
    """Calculate consumption for today, week, and month"""
    try:
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        consumption_ref = get_subcollection('consumption')
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

def get_realtime_status():
    """Get current real-time status from Firebase"""
    try:
        status_doc = get_subcollection('realtime_status').document('current').get()
        if status_doc.exists:
            return status_doc.to_dict()
        return None
    except Exception as e:
        print(f"Error getting realtime status: {e}")
        return None

def update_realtime_status(data):
    """Update the real-time status document"""
    try:
        data['last_update'] = firestore.SERVER_TIMESTAMP
        get_subcollection('realtime_status').document('current').set(data, merge=True)
    except Exception as e:
        print(f"Error updating realtime status: {e}")

def get_command():
    """Get the current command for ESP32"""
    try:
        cmd_doc = get_subcollection('commands').document('control').get()
        if cmd_doc.exists:
            return cmd_doc.to_dict()
        return None
    except Exception as e:
        print(f"Error getting command: {e}")
        return None

def set_command(action):
    """Set a command for ESP32 to execute"""
    try:
        cmd_data = {
            "action": action,
            "timestamp": firestore.SERVER_TIMESTAMP,
            "status": "pending"
        }
        get_subcollection('commands').document('control').set(cmd_data)
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
            return query[0].to_dict()
        return None
    except Exception as e:
        print(f"Error getting user: {e}")
        return None

def create_user(first_name, last_name, email, password):
    """Create a new user in Firebase"""
    try:
        user_id = f"USER_{uuid.uuid4().hex[:8].upper()}"
        user_data = {
            "user_id": user_id,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "password_hash": password,  # In production, use proper hashing!
            "account_id_fk": ACCOUNT_ID
        }
        db.collection('users').document(user_id).set(user_data)
        return user_data
    except Exception as e:
        print(f"Error creating user: {e}")
        return None

# -------------------------------
# 🔹 Routes
# -------------------------------

@app.route('/')
def index():
    if "user" not in session:
        return redirect(url_for('login'))
    
    # Get consumption summary
    consumption = get_consumption_summary()
    
    # Get last known status
    status = get_realtime_status()
    if not status:
        status = {
            "pump_state": "N/A",
            "flow_in_L_min": 0,
            "flow_out_L_min": 0,
            "battery_percent": 0,
            "leakage_detected": False
        }
    
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
        **consumption
    }
    
    return render_template("dashboard.html", status=display_status, user_name=session.get("user_name"))

# -------------------------------
# 🔹 ESP32 Communication Endpoints
# -------------------------------

@app.route("/api/esp32/status", methods=["POST"])
def esp32_status_update():
    """Endpoint for ESP32 to push status updates"""
    try:
        data = request.get_json()
        
        # Update real-time status in Firebase
        update_realtime_status(data)
        
        # Log sensor readings
        if 'flow_in_L_min' in data:
            add_sensor_log("SENS_FLOW_IN", data['flow_in_L_min'])
        
        # Log power status
        if all(k in data for k in ['battery_voltage_V', 'current_A', 'battery_percent']):
            add_power_log(
                data['battery_voltage_V'],
                data['current_A'],
                data['battery_percent']
            )
        
        # Check for alerts
        if data.get('leakage_detected', False):
            add_alert("Leakage", "Flow differential exceeded threshold")
        
        if data.get('battery_percent', 100) <= 10:
            add_alert("Low Battery", f"Battery at {data.get('battery_percent')}%")
        
        # Update daily consumption
        if 'volume_in_L' in data:
            update_consumption(data['volume_in_L'])
        
        # Check if there's a pending command
        cmd = get_command()
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
        cmd = get_command()
        if cmd and cmd.get('status') == 'pending':
            # Mark as delivered
            get_subcollection('commands').document('control').update({
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
        
        # Mark command as executed
        get_subcollection('commands').document('control').update({
            'status': 'executed'
        })
        
        # Log the control action
        add_control_log(action, method="Remote")
        
        return jsonify({"status": "acknowledged"})
    except Exception as e:
        print(f"Error acknowledging command: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/status-data")
def status_data():
    """Get current status for dashboard (legacy endpoint)"""
    if "user" not in session:
        return jsonify({"error": "Not logged in"}), 403
    
    try:
        status = get_realtime_status()
        if not status:
            status = {
                "pump_state": "N/A",
                "flow_in_L_min": 0,
                "flow_out_L_min": 0,
                "battery_percent": 0,
                "leakage_detected": False
            }
        
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
            "current_consumed": status.get("current_A", 0)
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
    if "user" not in session:
        return jsonify({"error": "Not logged in"}), 403
    
    try:
        # Get current status
        status = get_realtime_status()
        current_state = status.get("pump_state", "OFF") if status else "OFF"
        
        # Toggle state
        new_state = "OFF" if current_state == "ON" else "ON"
        
        # Set command for ESP32
        set_command(new_state)
        
        # Log the action
        add_control_log(f"TURN_{new_state}", method="Manual")
        
        return jsonify({"pump": new_state, "status": "command_sent"})
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
        if user and user.get("password_hash") == password:  # Use proper comparison in production
            session["user"] = email
            session["user_name"] = f"{user['first_name']} {user['last_name']}"
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
        
        # Create new user
        user = create_user(first_name, last_name, email, password)
        if user:
            return redirect(url_for('login'))
        else:
            return render_template("register.html", error="Registration failed")
    
    return render_template("register.html", error=None)

@app.route("/logout")
def logout():
    session.pop("user", None)
    session.pop("user_name", None)
    return redirect(url_for("login"))

# -------------------------------
# 🔹 Health Check (for Render)
# -------------------------------

@app.route("/health")
def health():
    """Health check endpoint for Render"""
    return jsonify({"status": "healthy", "firebase": "connected" if db else "disconnected"})

# -------------------------------
# 🔹 Startup
# -------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)