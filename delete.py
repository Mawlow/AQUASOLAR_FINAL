import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

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


def delete_collection(collection_ref, batch_size=100):
    """
    Delete all documents in a collection in batches.
    """
    deleted = 0
    docs = collection_ref.limit(batch_size).stream()
    
    for doc in docs:
        doc.reference.delete()
        deleted += 1
    
    if deleted >= batch_size:
        # There might be more documents, recurse
        return deleted + delete_collection(collection_ref, batch_size)
    
    return deleted


def delete_subcollections(account_id, subcollection_names):
    """
    Delete all documents from subcollections under a specific account.
    """
    account_ref = db.collection('accounts').document(account_id)
    
    for subcol_name in subcollection_names:
        subcol_ref = account_ref.collection(subcol_name)
        count = delete_collection(subcol_ref)
        print(f"   ✓ Deleted {count} documents from /accounts/{account_id}/{subcol_name}")


def get_all_account_ids():
    """
    Retrieve all account IDs from the accounts collection.
    """
    accounts_ref = db.collection('accounts')
    accounts = accounts_ref.stream()
    return [account.id for account in accounts]


# =========================================================================
# MAIN DELETION SCRIPT
# =========================================================================

print("\n⚠️  WARNING: This will delete ALL documents from your Firestore database!")
print("Collections will remain, but all data will be removed.\n")

confirmation = input("Type 'DELETE ALL' to confirm: ")

if confirmation != "DELETE ALL":
    print("❌ Deletion cancelled.")
    exit()

print("\n🗑️  Starting deletion process...\n")

# Step 1: Get all account IDs first (before deleting accounts collection)
print("--- Retrieving all account IDs ---")
account_ids = get_all_account_ids()
print(f"Found {len(account_ids)} accounts: {account_ids}\n")

# Step 2: Delete subcollections for each account
subcollection_names = [
    "sensor_logs",
    "control_logs", 
    "power_logs",
    "alerts",
    "consumption",
    "realtime_status",
    "commands"
]

for account_id in account_ids:
    print(f"--- Deleting subcollections for account: {account_id} ---")
    delete_subcollections(account_id, subcollection_names)

# Step 3: Delete top-level collections
print("\n--- Deleting top-level collections ---")

top_level_collections = ["users", "accounts", "sensors"]

for collection_name in top_level_collections:
    collection_ref = db.collection(collection_name)
    count = delete_collection(collection_ref)
    print(f"   ✓ Deleted {count} documents from /{collection_name}")

print("\n✅ All documents have been successfully deleted from Firestore!")
print("   Collections remain intact and can be repopulated.")