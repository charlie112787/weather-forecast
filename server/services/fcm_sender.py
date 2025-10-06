import firebase_admin
from firebase_admin import credentials, messaging
from .. import config

# Initialize Firebase Admin SDK
try:
    cred = credentials.Certificate(config.FIREBASE_SERVICE_ACCOUNT_KEY_PATH)
    firebase_admin.initialize_app(cred)
    print("Firebase Admin SDK initialized successfully.")
except Exception as e:
    print(f"Error initializing Firebase Admin SDK: {e}")
    print("Please ensure the service account key path in config.py is correct.")

def send_notification(title: str, body: str, token: str):
    """
    Sends a single notification to a specific device.
    """
    if not firebase_admin._apps:
        print("Firebase Admin SDK not initialized. Cannot send notification.")
        return

    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        token=token,
    )

    try:
        response = messaging.send(message)
        print('Successfully sent message:', response)
    except Exception as e:
        print('Error sending message:', e)
