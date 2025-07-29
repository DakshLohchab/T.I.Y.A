import sys
import json
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QHBoxLayout, QMessageBox, QGraphicsDropShadowEffect, QFrame, QStackedLayout,
    QTextEdit, QCheckBox
)
from PyQt5.QtGui import QFont, QPixmap, QPalette, QColor, QPainter, QBrush, QLinearGradient, QPen
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty, QPointF, pyqtSignal, QThread
import requests

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("Warning: google-generativeai not installed. API validation will be simulated.")

class APIValidationThread(QThread):
    validation_complete = pyqtSignal(bool, str)
    
    def __init__(self, api_key):
        super().__init__()
        self.api_key = api_key
    
    def run(self):
        """Validate the API key with actual Gemini API"""
        try:
            if GEMINI_AVAILABLE and self.api_key:
                # Configure the API
                genai.configure(api_key=self.api_key)
                
                # Try to create a model and generate a simple response
                model = genai.GenerativeModel('gemini-pro')
                response = model.generate_content("Hello")
                
                if response and response.text:
                    self.validation_complete.emit(True, "API key validated successfully")
                else:
                    self.validation_complete.emit(False, "Invalid response from API")
                    
            else:
                # Simulate validation if Gemini is not available
                import time
                time.sleep(2)
                if len(self.api_key) > 20:
                    self.validation_complete.emit(True, "API key format appears valid (simulation mode)")
                else:
                    self.validation_complete.emit(False, "API key format appears invalid")
                    
        except Exception as e:
            error_msg = str(e).lower()
            if "api_key" in error_msg or "invalid" in error_msg:
                self.validation_complete.emit(False, "Invalid API key")
            elif "quota" in error_msg or "limit" in error_msg:
                self.validation_complete.emit(False, "API quota exceeded")
            elif "permission" in error_msg:
                self.validation_complete.emit(False, "API permission denied")
            else:
                self.validation_complete.emit(False, f"Validation error: {str(e)}")

class AnimatedBackground(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.particles = []
        self.init_particles(100)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_particles)
        self.timer.start(50)
    
    def init_particles(self, count):
        import random
        for _ in range(count):
            self.particles.append({
                "x": random.randint(0, 800),
                "y": random.randint(0, 600),
                "vx": random.uniform(-0.5, 0.5),
                "vy": random.uniform(-0.5, 0.5),
                "opacity": random.uniform(0.1, 0.8)
            })
    
    def update_particles(self):
        import random
        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            
            if p["x"] < 0 or p["x"] > self.width():
                p["vx"] *= -1
            if p["y"] < 0 or p["y"] > self.height():
                p["vy"] *= -1
                
            if random.randint(0, 200) == 0:
                p["opacity"] = random.uniform(0.1, 0.8)
        
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background gradient
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor("#0a0f19"))
        gradient.setColorAt(1, QColor("#1a1f2e"))
        painter.fillRect(self.rect(), gradient)
        
        # Draw particles
        painter.setPen(Qt.PenStyle.NoPen)
        for p in self.particles:
            alpha = int(p["opacity"] * 255)
            painter.setBrush(QColor(0, 247, 255, alpha))
            painter.drawEllipse(int(p["x"]), int(p["y"]), 2, 2)

class GlowingButton(QPushButton):
    def __init__(self, text, color="#00f7ff", parent=None):
        super().__init__(text, parent)
        self.glow_effect = QGraphicsDropShadowEffect()
        self.glow_effect.setBlurRadius(20)
        self.glow_effect.setColor(QColor(color))
        self.glow_effect.setOffset(0, 0)
        self.setGraphicsEffect(self.glow_effect)

class APISetupWindow(QWidget):
    api_configured = pyqtSignal(str)  # Signal to emit when API is configured
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TIYA - API Configuration")
        self.setMinimumSize(800, 550)
        self.resize(800, 550)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.config_file = "tiya_config.json"
        self.init_ui()
        self.load_existing_config()
    
    def init_ui(self):
        # Base layout with stacked widgets for layering
        base_layout = QStackedLayout()
        base_layout.setStackingMode(QStackedLayout.StackingMode.StackAll)
        
        # Background
        self.background = AnimatedBackground()
        base_layout.addWidget(self.background)
        
        # Main content frame
        main_frame = QFrame()
        main_frame.setObjectName("mainFrame")
        base_layout.addWidget(main_frame)
        
        self.setLayout(base_layout)
        
        # Main layout
        main_layout = QVBoxLayout(main_frame)
        main_layout.setContentsMargins(40, 30, 40, 30)
        main_layout.setSpacing(20)
        
        # Header
        header_layout = QVBoxLayout()
        header_layout.setSpacing(8)
        
        title = QLabel("🚀 T.I.Y.A Setup")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        subtitle = QLabel("Connect your Gemini API to unlock T.I.Y.A.'s full potential")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        
        # API Key section
        api_section = QFrame()
        api_section.setObjectName("section")
        api_layout = QVBoxLayout(api_section)
        api_layout.setSpacing(15)
        
        # API Key header with icon
        header_layout = QHBoxLayout()
        api_icon = QLabel("🔑")
        api_icon.setObjectName("apiIcon")
        api_label = QLabel("Gemini API Key")
        api_label.setObjectName("fieldLabel")
        
        header_layout.addWidget(api_icon)
        header_layout.addWidget(api_label)
        header_layout.addStretch()
        
        # Input container for better styling
        input_container = QFrame()
        input_container.setObjectName("inputContainer")
        input_layout = QVBoxLayout(input_container)
        input_layout.setContentsMargins(15, 15, 15, 15)
        input_layout.setSpacing(10)
        
        self.api_input = QLineEdit()
        self.api_input.setPlaceholderText("Paste your Gemini API key here...")
        self.api_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_input.setObjectName("apiInput")
        self.api_input.setMinimumHeight(45)
        
        # Show/Hide API key checkbox with better styling
        checkbox_layout = QHBoxLayout()
        self.show_key_checkbox = QCheckBox("👁️ Show API Key")
        self.show_key_checkbox.setObjectName("checkbox")
        self.show_key_checkbox.toggled.connect(self.toggle_api_visibility)
        
        # Help text
        help_text = QLabel("💡 Need an API key? Visit Google AI Studio to get yours for free")
        help_text.setObjectName("helpText")
        help_text.setWordWrap(True)
        
        checkbox_layout.addWidget(self.show_key_checkbox)
        checkbox_layout.addStretch()
        
        input_layout.addWidget(self.api_input)
        input_layout.addLayout(checkbox_layout)
        input_layout.addWidget(help_text)
        
        api_layout.addLayout(header_layout)
        api_layout.addWidget(input_container)
        
        # Status
        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(20)
        
        self.validate_btn = GlowingButton("🔒 Validate & Save API Key")
        self.validate_btn.clicked.connect(self.validate_and_save_api)
        
        self.continue_btn = GlowingButton("✨ Launch T.I.Y.A", "#00ff88")
        self.continue_btn.clicked.connect(self.continue_to_main)
        self.continue_btn.setVisible(False)
        
        # Center the buttons
        button_layout.addStretch()
        button_layout.addWidget(self.validate_btn)
        button_layout.addWidget(self.continue_btn)
        button_layout.addStretch()
        
        # Footer
        footer = QLabel("T.I.Y.A. TRANSCENDENCE PROTOCOL v3.14")
        footer.setObjectName("footer")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Add to main layout
        main_layout.addLayout(header_layout)
        main_layout.addSpacing(15)
        main_layout.addWidget(api_section)
        main_layout.addWidget(self.status_label)
        main_layout.addSpacing(15)
        main_layout.addLayout(button_layout)
        main_layout.addStretch()
        main_layout.addWidget(footer)
        
        self.setStyleSheet(self.get_stylesheet())
    
    def get_stylesheet(self):
        return """
            QFrame#mainFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 rgba(15, 20, 35, 220), 
                    stop:1 rgba(25, 30, 45, 220));
                border: 2px solid rgba(0, 247, 255, 100);
                border-radius: 20px;
            }
            
            QFrame#section {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 rgba(5, 15, 25, 150), 
                    stop:1 rgba(15, 25, 35, 150));
                border: 1px solid rgba(0, 247, 255, 120);
                border-radius: 15px;
                padding: 20px;
            }
            
            QFrame#inputContainer {
                background: rgba(0, 0, 0, 80);
                border: 1px solid rgba(0, 247, 255, 60);
                border-radius: 12px;
                padding: 5px;
            }
            
            QLabel#title {
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 28px;
                font-weight: bold;
                color: #ffffff;
                text-shadow: 0 0 25px #00f7ff;
                letter-spacing: 2px;
                padding: 8px;
            }
            
            QLabel#subtitle {
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 14px;
                color: rgba(0, 247, 255, 200);
                font-style: italic;
                padding: 5px;
            }
            
            QLabel#apiIcon {
                font-size: 24px;
                padding: 5px;
            }
            
            QLabel#fieldLabel {
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 16px;
                font-weight: bold;
                color: #ffffff;
                padding: 5px;
            }
            
            QLabel#helpText {
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 11px;
                color: rgba(0, 247, 255, 150);
                font-style: italic;
                padding: 5px;
            }
            
            QLabel#statusLabel {
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 13px;
                font-weight: bold;
                padding: 15px;
                border-radius: 8px;
                margin: 10px;
            }
            
            QLabel#footer {
                font-family: 'Courier New', monospace;
                font-size: 9px;
                color: rgba(0, 247, 255, 80);
            }
            
            QLineEdit#apiInput {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 rgba(0, 10, 20, 180), 
                    stop:1 rgba(0, 20, 30, 180));
                border: 2px solid rgba(0, 247, 255, 100);
                border-radius: 8px;
                padding: 12px 15px;
                color: #ffffff;
                font-size: 14px;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-weight: 500;
                min-height: 20px;
            }
            
            QLineEdit#apiInput:focus {
                border: 2px solid #00f7ff;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 rgba(0, 20, 35, 200), 
                    stop:1 rgba(0, 35, 50, 200));
                box-shadow: 0 0 15px rgba(0, 247, 255, 50);
            }
            
            QLineEdit#apiInput::placeholder {
                color: rgba(0, 247, 255, 120);
                font-style: italic;
            }
            
            QCheckBox#checkbox {
                color: rgba(0, 247, 255, 180);
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 12px;
                font-weight: 500;
                padding: 5px;
            }
            
            QCheckBox#checkbox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid rgba(0, 247, 255, 100);
                border-radius: 4px;
                background: rgba(0, 0, 0, 120);
            }
            
            QCheckBox#checkbox::indicator:checked {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #00f7ff, stop:1 #008c9e);
                border: 2px solid #00f7ff;
            }
            
            QCheckBox#checkbox::indicator:hover {
                border: 2px solid #00f7ff;
                background: rgba(0, 247, 255, 20);
            }
            
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #00f7ff, stop:1 #008c9e);
                color: #05080f;
                border: none;
                border-radius: 10px;
                font-weight: bold;
                font-size: 13px;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                padding: 12px 25px;
                letter-spacing: 1px;
                min-height: 20px;
            }
            
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #ffffff, stop:1 #00f7ff);
                color: #000000;
                transform: translateY(-2px);
            }
            
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #008c9e, stop:1 #00f7ff);
                transform: translateY(1px);
            }
            
            QPushButton:disabled {
                background: rgba(100, 100, 100, 100);
                color: rgba(255, 255, 255, 100);
            }
        """
    
    def toggle_api_visibility(self, checked):
        if checked:
            self.api_input.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.api_input.setEchoMode(QLineEdit.EchoMode.Password)
    
    def validate_and_save_api(self):
        api_key = self.api_input.text().strip()
        
        if not api_key:
            self.show_status("ERROR: API key cannot be empty", "error")
            return
        
        self.status_label.setText("⏳ Validating API key...")
        self.status_label.setStyleSheet("color: #ffff00; text-shadow: 0 0 8px #ffff00;")
        
        # Disable button during validation
        self.validate_btn.setEnabled(False)
        self.validate_btn.setText("🔄 Validating...")
        
        # Start validation thread
        self.validation_thread = APIValidationThread(api_key)
        self.validation_thread.validation_complete.connect(self.handle_validation_result)
        self.validation_thread.start()
    
    def handle_validation_result(self, is_valid, message):
        """Handle the result of API validation"""
        self.validate_btn.setEnabled(True)
        self.validate_btn.setText("🔒 Validate & Save API Key")
        
        if is_valid:
            api_key = self.api_input.text().strip()
            config = {
                "gemini_api_key": api_key,
                "configured": True,
                "setup_date": str(QTimer().currentTime()),
                "validation_message": message
            }
            
            try:
                with open(self.config_file, 'w') as f:
                    json.dump(config, f, indent=2)
                
                self.show_status(f"✓ {message.upper()}", "success")
                self.validate_btn.setVisible(False)
                self.continue_btn.setVisible(True)
                
            except Exception as e:
                self.show_status(f"ERROR: Failed to save config - {str(e)}", "error")
        else:
            self.show_status(f"ERROR: {message}", "error")
    
    def show_status(self, message, status_type):
        self.status_label.setText(message)
        if status_type == "success":
            self.status_label.setStyleSheet("color: #00ff88; text-shadow: 0 0 8px #00ff88; background: rgba(0, 255, 136, 20); border: 1px solid rgba(0, 255, 136, 50);")
        elif status_type == "error":
            self.status_label.setStyleSheet("color: #ff2222; text-shadow: 0 0 8px #ff2222; background: rgba(255, 34, 34, 20); border: 1px solid rgba(255, 34, 34, 50);")
        else:
            self.status_label.setStyleSheet("color: #ffff00; text-shadow: 0 0 8px #ffff00;")
    
    def continue_to_main(self):
        api_key = self.load_api_key()
        self.api_configured.emit(api_key or "")
        self.close()
    
    def load_existing_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    if config.get('configured') and config.get('gemini_api_key'):
                        self.api_input.setText(config['gemini_api_key'])
                        self.show_status("✓ EXISTING CONFIGURATION FOUND", "success")
                        self.validate_btn.setText("🔄 Update & Save API Key")
                        self.continue_btn.setVisible(True)
        except Exception as e:
            print(f"Error loading config: {e}")
    
    def load_api_key(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    return config.get('gemini_api_key', '')
        except:
            pass
        return ''
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.oldPos = event.globalPosition().toPoint()
    
    def mouseMoveEvent(self, event):
        if hasattr(self, 'oldPos') and event.buttons() == Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self.oldPos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.oldPos = event.globalPosition().toPoint()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = APISetupWindow()
    
    # Center the window
    screen_geometry = app.primaryScreen().geometry()
    x = (screen_geometry.width() - window.width()) // 2
    y = (screen_geometry.height() - window.height()) // 2
    window.move(x, y)
    
    window.show()
    sys.exit(app.exec())