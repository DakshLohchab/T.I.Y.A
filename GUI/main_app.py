import sys
import os
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer

# Import your custom modules
from login import TIYALogin
from main_assistant import EnhancedTIYAAssistant
from firebase_manager import firebase_manager

class TIYAApplication:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.current_user = None
        self.api_key = None
        
        # Windows
        self.login_window = None
        self.api_setup_window = None
        self.assistant_window = None
        
        self.start_application()
    
    def start_application(self):
        """Start the application with login window"""
        self.show_login()
    
    def show_login(self):
        """Show the login window"""
        self.login_window = TIYALogin()
        
        # Override the login process to integrate with our flow
        original_process_login = self.login_window.process_login
        self.login_window.process_login = self.handle_login
        
        # Center and show
        self.center_window(self.login_window)
        self.login_window.show()
    
    def handle_login(self, username, password):
        """Handle login process with Firebase integration"""
        # Valid users (you can expand this or move to Firebase)
        valid_users = {
            "daksh lohchab": "886", 
            "operator": "quantum", 
            "admin": "singularity", 
            "tiya": "protocol"
        }
        
        if username in valid_users and password == valid_users[username]:
            self.current_user = username
            
            # Update login status
            self.login_window.status.setText("● CONNECTION ESTABLISHED. CHECKING NEURAL KEYS...")
            self.login_window.status.setObjectName("statusGranted")
            self.login_window.setStyleSheet(self.login_window.get_stylesheet())
            
            # Update last login in Firebase
            firebase_manager.update_user_last_login(username)
            
            # Check if user has API key stored
            QTimer.singleShot(1500, self.check_user_api_key)
            
        else:
            # Handle failed login (keep original behavior)
            self.login_window.status.setText("● AUTHENTICATION FAILURE. ANOMALY DETECTED.")
            self.login_window.status.setObjectName("statusDenied")
            self.login_window.glitch_effect()
            self.login_window.show_message_box(
                "Access Denied", 
                "Cognitive signature mismatch.\nSecurity protocols engaged.", 
                "failure"
            )
            QTimer.singleShot(2500, self.login_window.reset_status)
            self.login_window.setStyleSheet(self.login_window.get_stylesheet())
    
    def check_user_api_key(self):
        """Check if user has API key stored in Firebase"""
        try:
            api_key, message = firebase_manager.get_user_api_key(self.current_user)
            
            if api_key:
                # User has API key, go directly to main assistant
                self.api_key = api_key
                self.login_window.show_message_box(
                    "Welcome Back", 
                    f"Neural link synchronized, {self.current_user.title()}.\nAccessing T.I.Y.A. interface...", 
                    "success"
                )
                QTimer.singleShot(2000, self.show_main_assistant)
            else:
                # User doesn't have API key, show API setup
                self.login_window.show_message_box(
                    "Neural Key Required", 
                    f"Welcome, {self.current_user.title()}.\nAPI configuration required for full capabilities.", 
                    "success"
                )
                QTimer.singleShot(2000, self.show_api_setup)
                
        except Exception as e:
            print(f"Error checking API key: {e}")
            # If Firebase fails, show API setup
            self.login_window.show_message_box(
                "System Notice", 
                f"Welcome, {self.current_user.title()}.\nLocal API configuration required.", 
                "success"
            )
            QTimer.singleShot(2000, self.show_api_setup)
    
    def show_api_setup(self):
        """Show API setup window"""
        self.login_window.close()
        
        self.api_setup_window = APISetupWindow()
        self.api_setup_window.api_configured.connect(self.handle_api_configured)
        
        self.center_window(self.api_setup_window)
        self.api_setup_window.show()
    
    def handle_api_configured(self, api_key):
        """Handle API key configuration"""
        self.api_key = api_key
        
        if api_key:
            # Store API key in Firebase
            success, message = firebase_manager.store_user_api_key(self.current_user, api_key)
            if success:
                print(f"API key stored in Firebase: {message}")
            else:
                print(f"Failed to store API key: {message}")
        
        # Show main assistant
        self.show_main_assistant()
    
    def show_main_assistant(self):
        """Show the main T.I.Y.A. assistant"""
        if self.api_setup_window:
            self.api_setup_window.close()
        if self.login_window:
            self.login_window.close()
        
        self.assistant_window = EnhancedTIYAAssistant(
            api_key=self.api_key,
            username=self.current_user.title()
        )
        
        self.center_window(self.assistant_window)
        self.assistant_window.show()
    
    def center_window(self, window):
        """Center a window on the screen"""
        screen_geometry = self.app.primaryScreen().geometry()
        x = (screen_geometry.width() - window.width()) // 2
        y = (screen_geometry.height() - window.height()) // 2
        window.move(x, y)
    
    def run(self):
        """Run the application"""
        return self.app.exec_()

if __name__ == "__main__":
    tiya_app = TIYAApplication()
    sys.exit(tiya_app.run())