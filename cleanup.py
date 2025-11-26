import firebase_admin
from firebase_admin import credentials, firestore
import time

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

def delete_collection(collection_name, batch_size=100):
    """Delete all documents in a collection"""
    collection_ref = db.collection(collection_name)
    docs = collection_ref.limit(batch_size).stream()
    deleted = 0
    
    for doc in docs:
        print(f"   Deleting {collection_name}/{doc.id}")
        doc.reference.delete()
        deleted += 1
    
    if deleted >= batch_size:
        return delete_collection(collection_name, batch_size)
    
    return deleted

def delete_subcollection(account_id, subcollection_name, batch_size=100):
    """Delete all documents in a subcollection"""
    subcol_ref = db.collection('accounts').document(account_id).collection(subcollection_name)
    docs = subcol_ref.limit(batch_size).stream()
    deleted = 0
    
    for doc in docs:
        print(f"      Deleting {subcollection_name}/{doc.id}")
        doc.reference.delete()
        deleted += 1
    
    if deleted >= batch_size:
        return delete_subcollection(account_id, subcollection_name, batch_size)
    
    return deleted

def cleanup_all_data():
    """Delete ALL data from Firebase Firestore"""
    
    print("\n" + "=" * 70)
    print("⚠️  FIREBASE CLEANUP - THIS WILL DELETE EVERYTHING! ⚠️")
    print("=" * 70)
    print("\nThis will permanently delete:")
    print("   • All users")
    print("   • All accounts")
    print("   • All sensors")
    print("   • All sensor logs")
    print("   • All control logs")
    print("   • All power logs")
    print("   • All alerts")
    print("   • All consumption records")
    print("   • All real-time status")
    print("   • All commands")
    
    print("\n⚠️  THIS CANNOT BE UNDONE! ⚠️\n")
    
    confirm1 = input("Are you absolutely sure? Type 'DELETE' to confirm: ")
    
    if confirm1 != "DELETE":
        print("\n❌ Cleanup cancelled. No data was deleted.")
        return False
    
    confirm2 = input("Type 'YES' one more time to proceed: ")
    
    if confirm2 != "YES":
        print("\n❌ Cleanup cancelled. No data was deleted.")
        return False
    
    print("\n🗑️  Starting cleanup process...\n")
    time.sleep(1)
    
    # Step 1: Delete all account subcollections first
    print("=" * 70)
    print("STEP 1: Deleting Account Subcollections")
    print("=" * 70)
    
    accounts = db.collection('accounts').stream()
    account_ids = [account.id for account in accounts]
    
    print(f"\nFound {len(account_ids)} accounts to process\n")
    
    subcollections = [
        'realtime_status',
        'commands', 
        'sensor_logs',
        'control_logs',
        'power_logs',
        'alerts',
        'consumption'
    ]
    
    for account_id in account_ids:
        print(f"\n📁 Processing account: {account_id}")
        for subcol in subcollections:
            count = delete_subcollection(account_id, subcol)
            if count > 0:
                print(f"   ✅ Deleted {count} documents from {subcol}")
    
    # Step 2: Delete top-level collections
    print("\n" + "=" * 70)
    print("STEP 2: Deleting Top-Level Collections")
    print("=" * 70)
    
    collections_to_delete = ['users', 'accounts', 'sensors']
    
    for collection_name in collections_to_delete:
        print(f"\n🗑️  Deleting collection: {collection_name}")
        count = delete_collection(collection_name)
        print(f"✅ Deleted {count} documents from {collection_name}")
    
    print("\n" + "=" * 70)
    print("✅ CLEANUP COMPLETE!")
    print("=" * 70)
    print("\n🎉 All data has been successfully deleted from Firebase.")
    print("\n📝 Next steps:")
    print("   1. Run: python firebase_populate.py")
    print("   2. This will create fresh multi-user data")
    print("\n" + "=" * 70 + "\n")
    
    return True

# =========================================================================
# SCRIPT EXECUTION
# =========================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🌊 AquaSolar Firebase Cleanup Tool")
    print("=" * 70)
    
    success = cleanup_all_data()
    
    if success:
        print("\n✅ Ready for fresh setup!")
        run_populate = input("\nDo you want to run firebase_populate.py now? (yes/no): ")
        
        if run_populate.lower() == 'yes':
            print("\n🚀 Running firebase_populate.py...\n")
            import os
            os.system('python firebase_populate.py')
    else:
        print("\n👋 Exiting without changes.")