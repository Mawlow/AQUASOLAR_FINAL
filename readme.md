# AquaSolar - IoT Water Monitoring System

## Overview

AquaSolar is a comprehensive IoT-based water monitoring and control system designed for remote monitoring of water flow, pump control, and battery status. The system supports multiple users with complete data isolation and real-time monitoring capabilities.

## Features

### Core Functionality
- Real-time water flow monitoring (inlet and outlet)
- Remote pump control via web dashboard
- Battery voltage and current monitoring
- Leakage detection system
- SMS alert notifications
- Multi-user support with account isolation
- Consumption tracking (daily, weekly, monthly)

### Technical Features
- Optimized Firebase writes with smart throttling
- Real-time data synchronization
- Offline-capable with local storage
- Responsive web dashboard
- RESTful API for ESP32 communication
- Secure user authentication

## System Architecture

### Components

1. **ESP32 Microcontroller**
   - Manages hardware sensors and actuators
   - Sends data to cloud server
   - Receives pump control commands
   - Handles SMS communication via SIM800L

2. **Flask Backend Server**
   - RESTful API endpoints
   - Firebase Firestore integration
   - User authentication and authorization
   - Multi-user account management
   - Data aggregation and logging

3. **Web Dashboard**
   - Real-time status monitoring
   - Interactive pump control
   - Historical data visualization
   - Responsive design for mobile and desktop

4. **Firebase Firestore**
   - User data storage
   - Real-time status updates
   - Historical logs
   - Alert management

## Hardware Requirements

### ESP32 Development Board
- ESP32-WROOM-32 or compatible
- Wi-Fi connectivity

### Sensors
- YF-S201 Water Flow Sensors (x2)
- INA219 Current/Voltage Sensor

### Actuators
- 5V Relay Module for pump control

### Communication
- SIM800L GSM Module for SMS alerts

### Power Supply
- 12V Battery (for pump and system)
- 5V Power supply for ESP32

## Software Requirements

### Backend
- Python 3.8+
- Flask 2.0+
- Firebase Admin SDK
- Flask-CORS

### ESP32 Firmware
- MicroPython 1.19+
- urequests library
- INA219 library

### Frontend
- Modern web browser
- JavaScript enabled
- Chart.js for data visualization

## Installation

### 1. Firebase Setup

Create a Firebase project:
```
1. Go to Firebase Console (https://console.firebase.google.com)
2. Create new project
3. Enable Firestore Database
4. Generate service account key
5. Download JSON credentials file
```

### 2. Backend Setup

Install Python dependencies:
```bash
pip install flask flask-cors firebase-admin
```

Configure Firebase credentials:
```python
# Place your service account JSON file in project root
# Update filename in app.py:
cred = credentials.Certificate('your-firebase-credentials.json')
```

Set environment variables:
```bash
export SECRET_TOKEN="your_owner_code"
export SECRET_KEY="your_flask_secret_key"
export PORT=5000
```

Run Flask server:
```bash
python app.py
```

### 3. ESP32 Setup

Install MicroPython on ESP32:
```bash
esptool.py --port /dev/ttyUSB0 erase_flash
esptool.py --port /dev/ttyUSB0 write_flash -z 0x1000 esp32-micropython.bin
```

Configure Wi-Fi:
```python
# In boot.py or main.py
SSID = "your_wifi_ssid"
PASSWORD = "your_wifi_password"
```

Configure server URL and Account ID:
```python
# In main.py
FLASK_SERVER_URL = "https://your-server-url.com"
ACCOUNT_ID = "ACC_XXXXXXXX"  # Get from Firebase after user registration
```

Upload files to ESP32:
```bash
ampy --port /dev/ttyUSB0 put main.py
ampy --port /dev/ttyUSB0 put ina219.py
```

### 4. Hardware Wiring

```
ESP32 Pin Connections:
- GPIO 22: Relay control (pump)
- GPIO 23: Flow sensor 1 (inlet)
- GPIO 21: Flow sensor 2 (outlet)
- GPIO 19: INA219 SCL
- GPIO 18: INA219 SDA
- GPIO 17: SIM800L TX
- GPIO 16: SIM800L RX

Power Connections:
- ESP32: 5V via USB or 5V pin
- Relay: 5V and GND
- Flow Sensors: 5V and GND
- INA219: 3.3V and GND
- SIM800L: 4V (use voltage regulator)
```

## Configuration

### User Registration

1. Access registration page: `http://your-server:5000/register`
2. Enter user details and owner code
3. System generates unique Account ID
4. Note the Account ID from server logs

### ESP32 Device Configuration

Configure each ESP32 device with a user's Account ID:
```python
# In main.py, line 19
ACCOUNT_ID = "ACC_XXXXXXXX"  # Replace with actual Account ID
```

### Firebase Database Structure

```
/users/{user_id}
  - user_id: string
  - first_name: string
  - last_name: string
  - email: string
  - password_hash: string
  - account_id_fk: string

/accounts/{account_id}
  - account_id: string
  - user_id_fk: string
  - active: boolean
  - device_name: string
  - admin_number: string
  
  /realtime_status/current
    - pump_state: string
    - flow_in_L_min: float
    - flow_out_L_min: float
    - battery_voltage_V: float
    - current_A: float
    - battery_percent: integer
    - leakage_detected: boolean
    - last_update: timestamp
  
  /commands/control
    - action: string (ON/OFF/NONE)
    - timestamp: timestamp
    - status: string (pending/delivered/executed)
  
  /sensor_logs/
    - Historical sensor readings
  
  /power_logs/
    - Battery and power history
  
  /control_logs/
    - Pump control history
  
  /alerts/
    - System alerts
  
  /consumption/
    - Daily consumption totals
```

## API Endpoints

### ESP32 Endpoints

**POST /api/esp32/status**
- Send device status update
- Requires: account_id in request body
- Returns: pending command if available

**GET /api/esp32/command**
- Poll for pending commands
- Requires: account_id query parameter
- Returns: command action (ON/OFF/NONE)

**POST /api/esp32/command/ack**
- Acknowledge command execution
- Requires: account_id and action in request body

### Dashboard Endpoints

**GET /status-data**
- Get current system status
- Requires: user login
- Returns: JSON with all sensor data

**POST /toggle_pump**
- Toggle pump state
- Requires: user login
- Returns: new pump state

### Authentication Endpoints

**POST /login**
- User authentication
- Body: email, password
- Sets session cookies

**POST /register**
- User registration
- Body: firstname, lastname, email, password, owner_code
- Creates new user and account

**GET /logout**
- Clear user session

## Usage

### Dashboard Access

1. Navigate to: `http://your-server:5000`
2. Login with credentials
3. Monitor real-time status
4. Control pump remotely
5. View consumption statistics

### SMS Commands

Send SMS to registered phone number:
- "pump on" - Turn pump ON
- "pump off" - Turn pump OFF
- "status" - Get current system status

### Multi-User Operation

Each user has:
- Unique Account ID
- Isolated data storage
- Individual ESP32 device(s)
- Separate consumption tracking

User A cannot see or control User B's devices.

## Optimization Features

### Smart Throttling
- Sensor logs: Every 5 minutes or significant change
- Power logs: Every 10 minutes or significant change
- Consumption updates: Every 30 minutes
- Reduces Firebase writes by approximately 95%

### Change Detection
- Only logs data when values change significantly
- Prevents duplicate alert notifications
- Optimizes bandwidth usage

### Caching
- Per-account caching for throttling
- Prevents race conditions
- Reduces database queries

## Security

### Authentication
- Session-based authentication
- Password hashing (bcrypt recommended for production)
- Account isolation enforced at API level

### Authorization
- Users can only access their own account data
- ESP32 must provide valid account_id
- Command execution requires account match

### Best Practices
- Change default owner code
- Use strong passwords
- Enable HTTPS in production
- Secure Firebase rules
- Regular security audits

## Troubleshooting

### ESP32 Not Connecting
1. Check Wi-Fi credentials
2. Verify server URL is correct
3. Check network connectivity
4. Monitor serial output for errors

### Battery Not Displaying
1. Verify INA219 wiring
2. Check I2C address (default 0x40)
3. Ensure Flask app includes battery field names
4. Check browser console for errors

### Pump Not Responding
1. Verify Account ID matches
2. Check command in Firebase
3. Test relay manually
4. Monitor ESP32 serial output

### Data Not Updating
1. Check ESP32 is online
2. Verify Firebase connection
3. Check account_id in requests
4. Review server logs

### Multi-User Issues
1. Verify each user has unique Account ID
2. Check ESP32 is configured with correct Account ID
3. Test account isolation
4. Review Flask logs for mismatches

## Development

### Local Development

Run Flask in debug mode:
```bash
python app.py
# Debug mode enabled by default
```

### Testing

Test API endpoints:
```bash
# Status endpoint
curl http://localhost:5000/status-data

# Health check
curl http://localhost:5000/health
```

### Deployment

Deploy to Render.com:
```bash
1. Push code to GitHub
2. Create new Web Service on Render
3. Set environment variables
4. Deploy
```

Environment variables for production:
```
FIREBASE_CREDENTIALS=<json-string>
SECRET_TOKEN=<owner-code>
SECRET_KEY=<flask-secret>
PORT=5000
```

## Monitoring

### Server Health
- Endpoint: `/health`
- Returns: Firebase status, optimization status

### Firebase Usage
- Monitor read/write operations
- Check quota usage
- Review alert triggers

### ESP32 Status
- Check last_update timestamp
- Monitor connection state
- Review serial logs

## Maintenance

### Regular Tasks
- Review and clear old logs
- Monitor Firebase quota
- Update firmware as needed
- Backup user data
- Review security logs

### Database Maintenance
- Archive old sensor_logs
- Clean up expired alerts
- Optimize consumption records
- Vacuum database periodically

## License

This project is provided as-is for educational and commercial use.

## Support

For issues and questions:
- Check troubleshooting section
- Review server logs
- Examine ESP32 serial output
- Verify configuration settings

## Credits

Developed as a capstone project for IoT water monitoring and control systems.

## Version History

### Version 1.2 (Current)
- Multi-user support with account isolation
- Battery field name compatibility fix
- Security improvements for unauthorized access
- Optimized Firebase writes with smart throttling

### Version 1.1
- Added multi-user functionality
- Firebase integration
- Real-time status updates

### Version 1.0
- Initial release
- Single-user system
- Basic monitoring features