
import firebase_admin
from firebase_admin import credentials, storage
import os

def initialize_firebase():
    """Initializes the Firebase Admin SDK if not already initialized."""
    if not firebase_admin._apps:
        try:
            # Assuming serviceAccountKey.json is in the root of the server directory
            cred_path = os.path.join(os.path.dirname(__file__), '..', 'serviceAccountKey.json')
            
            # Get the bucket name from environment variables
            bucket_name = os.getenv('FIREBASE_STORAGE_BUCKET')
            if not bucket_name:
                print("Error: FIREBASE_STORAGE_BUCKET environment variable is not set.")
                return False

            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred, {
                'storageBucket': bucket_name
            })
            print("Firebase Admin SDK initialized successfully.")
            return True
        except Exception as e:
            print(f"Error initializing Firebase Admin SDK: {e}")
            return False
    return True

def upload_file_to_storage(local_file_path: str, destination_blob_name: str) -> str:
    """
    Uploads a file to Firebase Storage and returns its public URL.

    Args:
        local_file_path: The path to the local file to upload.
        destination_blob_name: The desired name of the file in the storage bucket.

    Returns:
        The public URL of the uploaded file, or an empty string if upload fails.
    """
    if not initialize_firebase():
        return ""

    try:
        bucket = storage.bucket()
        blob = bucket.blob(destination_blob_name)

        print(f"Uploading {local_file_path} to Firebase Storage as {destination_blob_name}...")
        blob.upload_from_filename(local_file_path)

        # Make the blob publicly viewable
        blob.make_public()

        public_url = blob.public_url
        print(f"Successfully uploaded file. Public URL: {public_url}")
        return public_url
    except Exception as e:
        print(f"Error uploading file to Firebase Storage: {e}")
        return ""

