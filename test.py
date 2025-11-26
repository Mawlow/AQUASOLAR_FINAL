import firebase_admin
from firebase_admin import credentials, firestore
import time

# --- CONFIGURATION ---
SERVICE_ACCOUNT_KEY_PATH = 'aqua-7ced9-firebase-adminsdk-fbsvc-d94e9eb953.json'

cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
firebase_admin.initialize_app(cred)
db = firestore.client()

print("=" * 70)
print("🔍 COMMAND ISOLATION TEST")
print("=" * 70)

# Check commands for all accounts
accounts = [
    {"id": "ACC_DE290622", "name": "Marlo"},
    {"id": "ACC_B28A6FA0", "name": "John"},
    {"id": "ACC_7BA5E5E9", "name": "Jane"}
]

print("\n📋 Current Commands in Firebase:")
print("-" * 70)

for account in accounts:
    try:
        cmd_doc = db.collection('accounts').document(account['id']).collection('commands').document('control').get()
        
        if cmd_doc.exists:
            cmd_data = cmd_doc.to_dict()
            print(f"\n👤 {account['name']} ({account['id']}):")
            print(f"   Action: {cmd_data.get('action')}")
            print(f"   Status: {cmd_data.get('status')}")
            print(f"   Timestamp: {cmd_data.get('timestamp')}")
        else:
            print(f"\n👤 {account['name']} ({account['id']}):")
            print(f"   ⚠️  No command document found!")
    except Exception as e:
        print(f"\n❌ Error reading {account['name']}: {e}")

print("\n" + "=" * 70)
print("🧪 MANUAL TEST INSTRUCTIONS:")
print("=" * 70)
print("\n1. Keep this window open")
print("2. Login to website as John (john@example.com)")
print("3. Click 'Toggle Pump' button")
print("4. Come back here and press ENTER to check results")
input("\n⏸️  Press ENTER after clicking John's Toggle Pump button...")

print("\n🔄 Checking commands after John's action...")
print("-" * 70)

for account in accounts:
    try:
        cmd_doc = db.collection('accounts').document(account['id']).collection('commands').document('control').get()
        
        if cmd_doc.exists:
            cmd_data = cmd_doc.to_dict()
            action = cmd_data.get('action')
            
            if action != 'NONE':
                print(f"\n👤 {account['name']} ({account['id']}):")
                print(f"   ✅ Action: {action} ← COMMAND PRESENT!")
            else:
                print(f"\n👤 {account['name']} ({account['id']}):")
                print(f"   ⚪ Action: {action} (No command)")
    except Exception as e:
        print(f"\n❌ Error: {e}")

print("\n" + "=" * 70)
print("🎯 EXPECTED RESULT:")
print("=" * 70)
print("  • John's account (ACC_B28A6FA0): Should have a command")
print("  • Marlo's account (ACC_DE290622): Should have NO command")
print("  • Jane's account (ACC_7BA5E5E9): Should have NO command")

print("\n" + "=" * 70)
print("🔌 ESP32 BEHAVIOR:")
print("=" * 70)
print(f"  Your ESP32 is configured with: ACC_DE290622 (Marlo)")
print(f"  Therefore:")
print(f"    • ESP32 reads from: /accounts/ACC_DE290622/commands/control")
print(f"    • John's command goes to: /accounts/ACC_B28A6FA0/commands/control")
print(f"    • Result: ESP32 should NOT see John's command ✅")

print("\n" + "=" * 70)
input("\n⏸️  Press ENTER to test with Marlo's account...")

print("\n5. Now login as Marlo (marlo@example.com)")
print("6. Click 'Toggle Pump' button")
input("\n⏸️  Press ENTER after clicking Marlo's Toggle Pump button...")

print("\n🔄 Checking commands after Marlo's action...")
print("-" * 70)

for account in accounts:
    try:
        cmd_doc = db.collection('accounts').document(account['id']).collection('commands').document('control').get()
        
        if cmd_doc.exists:
            cmd_data = cmd_doc.to_dict()
            action = cmd_data.get('action')
            
            if account['id'] == 'ACC_DE290622':
                if action != 'NONE':
                    print(f"\n✅ {account['name']} ({account['id']}):")
                    print(f"   Action: {action} ← ESP32 WILL SEE THIS!")
                else:
                    print(f"\n⚠️  {account['name']} ({account['id']}):")
                    print(f"   Action: {action} ← No command set?")
            else:
                print(f"\n👤 {account['name']} ({account['id']}):")
                print(f"   Action: {action}")
    except Exception as e:
        print(f"\n❌ Error: {e}")

print("\n" + "=" * 70)
print("✅ TEST COMPLETE")
print("=" * 70 + "\n")