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
        self.setFixedSize(800, 600)
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
        main_layout.setContentsMargins(50, 40, 50, 40)
        main_layout.setSpacing(25)
        
        # Header
        header_layout = QVBoxLayout()
        header_layout.setSpacing(10)
        
        title = QLabel("NEURAL NETWORK CONFIGURATION")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        subtitle = QLabel("Configure your Gemini API key to enable T.I.Y.A.'s cognitive capabilities")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        
        # API Key section
        api_section = QFrame()
        api_section.setObjectName("section")
        api_layout = QVBoxLayout(api_section)
        api_layout.setSpacing(15)
        
        api_label = QLabel("GEMINI API KEY:")
        api_label.setObjectName("fieldLabel")
        
        self.api_input = QLineEdit()
        self.api_input.setPlaceholderText("Enter your Gemini API key here...")
        self.api_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        # Show/Hide API key checkbox
        self.show_key_checkbox = QCheckBox("Show API Key")
        self.show_key_checkbox.setObjectName("checkbox")
        self.show_key_checkbox.toggled.connect(self.toggle_api_visibility)
        
        # Instructions
        instructions = QTextEdit()
        instructions.setObjectName("instructions")
        instructions.setMaximumHeight(120)
        instructions.setHtml("""
        <div style='color: #00f7ff; font-family: "Courier New"; font-size: 11px;'>
        <b>How to get your Gemini API Key:</b><br>
        1. Visit <span style='color: #ffffff;'>https://makersuite.google.com/app/apikey</span><br>
        2. Sign in with your Google account<br>
        3. Click "Create API Key" and copy the generated key<br>
        4. Paste it above and click "VALIDATE & SAVE"
        </div>
        """)
        instructions.setReadOnly(True)
        
        api_layout.addWidget(api_label)
        api_layout.addWidget(self.api_input)
        api_layout.addWidget(self.show_key_checkbox)
        api_layout.addWidget(instructions)
        
        # Status
        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(20)
        
        self.validate_btn = GlowingButton("VALIDATE & SAVE")
        self.validate_btn.clicked.connect(self.validate_and_save_api)
        
        self.skip_btn = GlowingButton("SKIP FOR NOW", "#ff6b6b")
        self.skip_btn.clicked.connect(self.skip_setup)
        
        self.continue_btn = GlowingButton("CONTINUE TO TIYA", "#00ff88")
        self.continue_btn.clicked.connect(self.continue_to_main)
        self.continue_btn.setVisible(False)
        
        button_layout.addWidget(self.validate_btn)
        button_layout.addWidget(self.skip_btn)
        button_layout.addWidget(self.continue_btn)
        
        # Footer
        footer = QLabel("T.I.Y.A. TRANSCENDENCE PROTOCOL v3.14")
        footer.setObjectName("footer")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Add to main layout
        main_layout.addLayout(header_layout)
        main_layout.addSpacing(20)
        main_layout.addWidget(api_section)
        main_layout.addWidget(self.status_label)
        main_layout.addSpacing(20)
        main_layout.addLayout(button_layout)
        main_layout.addStretch()
        main_layout.addWidget(footer)
        
        self.setStyleSheet(self.get_stylesheet())
    
    def get_stylesheet(self):
        return """
            QFrame#mainFrame {
                background: rgba(10, 15, 25, 200);
                border: 1px solid rgba(0, 247, 255, 50);
                border-radius: 15px;
            }
            
            QFrame#section {
                background: rgba(0, 0, 0, 100);
                border: 1px solid rgba(0, 247, 255, 80);
                border-radius: 10px;
                padding: 20px;
            }
            
            QLabel#title {
                font-family: 'Orbitron', sans-serif;
                font-size: 28px;
                font-weight: bold;
                color: #ffffff;
                text-shadow: 0 0 20px #00f7ff;
                letter-spacing: 3px;
            }
            
            QLabel#subtitle {
                font-family: 'Courier New', monospace;
                font-size: 12px;
                color: rgba(0, 247, 255, 180);
                font-style: italic;
            }
            
            QLabel#fieldLabel {
                font-family: 'Courier New', monospace;
                font-size: 12px;
                font-weight: bold;
                color: rgba(0, 247, 255, 180);
            }
            
            QLabel#statusLabel {
                font-family: 'Courier New', monospace;
                font-size: 12px;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            
            QLabel#footer {
                font-family: 'Courier New', monospace;
                font-size: 9px;
                color: rgba(0, 247, 255, 100);
            }
            
            QLineEdit {
                background: rgba(0, 0, 0, 150);
                border: 1px solid rgba(0, 247, 255, 80);
                border-radius: 8px;
                padding: 12px 15px;
                color: #e0ffff;
                font-size: 14px;
                font-family: 'Courier New', monospace;
            }
            
            QLineEdit:focus {
                border: 1px solid #00f7ff;
                background: rgba(0, 20, 30, 150);
            }
            
            QLineEdit::placeholder {
                color: rgba(0, 247, 255, 100);
            }
            
            QTextEdit#instructions {
                background: rgba(0, 0, 0, 100);
                border: 1px solid rgba(0, 247, 255, 50);
                border-radius: 5px;
                padding: 10px;
            }
            
            QCheckBox#checkbox {
                color: rgba(0, 247, 255, 180);
                font-family: 'Courier New', monospace;
                font-size: 11px;
            }
            
            QCheckBox#checkbox::indicator {
                width: 15px;
                height: 15px;
                border: 1px solid rgba(0, 247, 255, 80);
                border-radius: 3px;
                background: rgba(0, 0, 0, 100);
            }
            
            QCheckBox#checkbox::indicator:checked {
                background: #00f7ff;
            }
            
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00f7ff, stop:1 #008c9e);
                color: #05080f;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                font-family: 'Orbitron', sans-serif;
                padding: 12px 25px;
                letter-spacing: 1px;
            }
            
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ffffff, stop:1 #00f7ff);
                color: #000000;
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
        
        self.status_label.setText("● VALIDATING API KEY...")
        self.status_label.setStyleSheet("color: #ffff00; text-shadow: 0 0 8px #ffff00;")
        
        # Disable button during validation
        self.validate_btn.setEnabled(False)
        self.validate_btn.setText("VALIDATING...")
        
        # Start validation thread
        self.validation_thread = APIValidationThread(api_key)
        self.validation_thread.validation_complete.connect(self.handle_validation_result)
        self.validation_thread.start()
    
    def handle_validation_result(self, is_valid, message):
        """Handle the result of API validation"""
        self.validate_btn.setEnabled(True)
        self.validate_btn.setText("VALIDATE & SAVE")
        
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
                self.skip_btn.setVisible(False)
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
    
    def skip_setup(self):
        reply = QMessageBox.question(
            self, 
            "Skip API Setup",
            "T.I.Y.A. will have limited capabilities without an API key.\n\nAre you sure you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.continue_to_main()
    
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
                        self.validate_btn.setText("UPDATE & SAVE")
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
        self.oldPos = event.globalPos()
    
    def mouseMoveEvent(self, event):
        if hasattr(self, 'oldPos'):
            delta = event.globalPos() - self.oldPos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.oldPos = event.globalPos()

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