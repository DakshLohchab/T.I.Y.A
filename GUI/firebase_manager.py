import firebase_admin
from firebase_admin import credentials, firestore
import json
import os
from datetime import datetime
import hashlib

class FirebaseManager:
    def __init__(self):
        self.db = None
        self.initialized = False
        self.init_firebase()
    
    def init_firebase(self):
        """Initialize Firebase connection"""
        try:
            # Check if Firebase is already initialized
            if not firebase_admin._apps:
                # Path to your Firebase service account key
                creds_path = "firebase_credentials.json"
                
                if os.path.exists(creds_path):
                    cred = credentials.Certificate(creds_path)
                    firebase_admin.initialize_app(cred)
                    self.db = firestore.client()
                    self.initialized = True
                    print("Firebase initialized successfully")
                else:
                    print("Firebase credentials file not found")
                    # Create a template credentials file
                    self.create_credentials_template()
            else:
                self.db = firestore.client()
                self.initialized = True
                
        except Exception as e:
            print(f"Firebase initialization error: {e}")
            self.initialized = False
    
    def create_credentials_template(self):
        """Create a template for Firebase credentials"""
        template = {
            "type": "service_account",
            "project_id": "your-project-id",
            "private_key_id": "your-private-key-id",
            "private_key": "-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY\n-----END PRIVATE KEY-----\n",
            "client_email": "your-service-account-email@your-project-id.iam.gserviceaccount.com",
            "client_id": "your-client-id",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs/your-service-account-email%40your-project-id.iam.gserviceaccount.com"
        }
        
        with open("firebase_credentials.json", "w") as f:
            json.dump(template, f, indent=2)
        
        print("Created firebase_credentials.json template. Please fill it with your actual Firebase credentials.")
    
    def hash_username(self, username):
        """Create a secure hash of username for storage"""
        return hashlib.sha256(username.lower().encode()).hexdigest()
    
    def store_user_api_key(self, username, api_key):
        """Store user's API key in Firebase"""
        if not self.initialized:
            return False, "Firebase not initialized"
        
        try:
            user_hash = self.hash_username(username)
            user_data = {
                'api_key': api_key,
                'last_updated': datetime.now(),
                'username_hash': user_hash,
                'created_at': datetime.now()
            }
            
            # Store in 'users' collection with hashed username as document ID
            self.db.collection('users').document(user_hash).set(user_data, merge=True)
            return True, "API key stored successfully"
            
        except Exception as e:
            return False, f"Error storing API key: {str(e)}"
    
    def get_user_api_key(self, username):
        """Retrieve user's API key from Firebase"""
        if not self.initialized:
            return None, "Firebase not initialized"
        
        try:
            user_hash = self.hash_username(username)
            doc_ref = self.db.collection('users').document(user_hash)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                return data.get('api_key'), "API key retrieved successfully"
            else:
                return None, "User not found"
                
        except Exception as e:
            return None, f"Error retrieving API key: {str(e)}"
    
    def update_user_last_login(self, username):
        """Update user's last login timestamp"""
        if not self.initialized:
            return False
        
        try:
            user_hash = self.hash_username(username)
            self.db.collection('users').document(user_hash).update({
                'last_login': datetime.now()
            })
            return True
        except Exception as e:
            print(f"Error updating last login: {e}")
            return False
    
    def store_user_preferences(self, username, preferences):
        """Store user preferences"""
        if not self.initialized:
            return False
        
        try:
            user_hash = self.hash_username(username)
            self.db.collection('users').document(user_hash).update({
                'preferences': preferences,
                'preferences_updated': datetime.now()
            })
            return True
        except Exception as e:
            print(f"Error storing preferences: {e}")
            return False
    
    def get_user_preferences(self, username):
        """Retrieve user preferences"""
        if not self.initialized:
            return {}
        
        try:
            user_hash = self.hash_username(username)
            doc_ref = self.db.collection('users').document(user_hash)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                return data.get('preferences', {})
            else:
                return {}
                
        except Exception as e:
            print(f"Error retrieving preferences: {e}")
            return {}
    
    def store_chat_history(self, username, chat_data):
        """Store chat history for a user"""
        if not self.initialized:
            return False
        
        try:
            user_hash = self.hash_username(username)
            chat_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            self.db.collection('users').document(user_hash).collection('chats').document(chat_id).set({
                'messages': chat_data,
                'timestamp': datetime.now()
            })
            return True
        except Exception as e:
            print(f"Error storing chat history: {e}")
            return False
    
    def get_chat_history(self, username, limit=10):
        """Retrieve recent chat history for a user"""
        if not self.initialized:
            return []
        
        try:
            user_hash = self.hash_username(username)
            chats_ref = self.db.collection('users').document(user_hash).collection('chats')
            docs = chats_ref.order_by('timestamp', direction=firestore.Query.DESCENDING).limit(limit).stream()
            
            chat_history = []
            for doc in docs:
                data = doc.to_dict()
                chat_history.append({
                    'id': doc.id,
                    'messages': data.get('messages', []),
                    'timestamp': data.get('timestamp')
                })
            
            return chat_history
        except Exception as e:
            print(f"Error retrieving chat history: {e}")
            return []
    
    def delete_user_data(self, username):
        """Delete all user data (for privacy compliance)"""
        if not self.initialized:
            return False
        
        try:
            user_hash = self.hash_username(username)
            
            # Delete chat history
            chats_ref = self.db.collection('users').document(user_hash).collection('chats')
            docs = chats_ref.stream()
            for doc in docs:
                doc.reference.delete()
            
            # Delete user document
            self.db.collection('users').document(user_hash).delete()
            return True
        except Exception as e:
            print(f"Error deleting user data: {e}")
            return False

# Singleton instance
firebase_manager = FirebaseManager()