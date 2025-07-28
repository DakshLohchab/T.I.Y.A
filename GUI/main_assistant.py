import sys
import json
import os
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QHBoxLayout, QTextEdit, QScrollArea, QFrame, QStackedLayout, QSplitter,
    QListWidget, QListWidgetItem, QProgressBar, QTabWidget, QGridLayout
)
from PyQt5.QtGui import (
    QFont, QPixmap, QPalette, QColor, QPainter, QBrush, QLinearGradient, QPen,
    QTextCursor, QIcon
)
from PyQt5.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty, QPointF, 
    QThread, pyqtSignal, QSize
)
import math
import random

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("Warning: google-generativeai not installed. Using mock responses.")

class NeuralBackgroundWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.nodes = []
        self.connections = []
        self.init_neural_network()
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_network)
        self.timer.start(100)
    
    def init_neural_network(self):
        # Create nodes
        for _ in range(50):
            self.nodes.append({
                "x": random.randint(50, 1200),
                "y": random.randint(50, 800),
                "vx": random.uniform(-0.5, 0.5),
                "vy": random.uniform(-0.5, 0.5),
                "size": random.uniform(2, 5),
                "pulse": random.uniform(0, 360),
                "pulse_speed": random.uniform(2, 8)
            })
    
    def update_network(self):
        # Update nodes
        for node in self.nodes:
            node["x"] += node["vx"]
            node["y"] += node["vy"]
            node["pulse"] = (node["pulse"] + node["pulse_speed"]) % 360
            
            # Bounce off edges
            if node["x"] <= 0 or node["x"] >= self.width():
                node["vx"] *= -1
            if node["y"] <= 0 or node["y"] >= self.height():
                node["vy"] *= -1
        
        # Update connections
        self.connections = []
        for i, node1 in enumerate(self.nodes):
            for j, node2 in enumerate(self.nodes[i+1:], i+1):
                distance = math.sqrt((node1["x"] - node2["x"])**2 + (node1["y"] - node2["y"])**2)
                if distance < 150:
                    opacity = max(0, 1 - distance / 150)
                    self.connections.append({
                        "x1": node1["x"], "y1": node1["y"],
                        "x2": node2["x"], "y2": node2["y"],
                        "opacity": opacity
                    })
        
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background gradient
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor("#0a0f19"))
        gradient.setColorAt(0.5, QColor("#1a1f2e"))
        gradient.setColorAt(1, QColor("#0a0f19"))
        painter.fillRect(self.rect(), gradient)
        
        # Draw connections
        for conn in self.connections:
            alpha = int(conn["opacity"] * 60)
            painter.setPen(QPen(QColor(0, 247, 255, alpha), 1))
            painter.drawLine(int(conn["x1"]), int(conn["y1"]), int(conn["x2"]), int(conn["y2"]))
        
        # Draw nodes
        painter.setPen(Qt.PenStyle.NoPen)
        for node in self.nodes:
            # Pulsing effect
            pulse_factor = (math.sin(math.radians(node["pulse"])) + 1) / 2
            size = node["size"] * (0.7 + 0.3 * pulse_factor)
            alpha = int(150 + 105 * pulse_factor)
            
            painter.setBrush(QColor(0, 247, 255, alpha))
            painter.drawEllipse(int(node["x"] - size/2), int(node["y"] - size/2), int(size), int(size))

class ChatBubble(QFrame):
    def __init__(self, message, is_user=True, timestamp=None, parent=None):
        super().__init__(parent)
        self.is_user = is_user
        self.message = message
        self.timestamp = timestamp or datetime.now().strftime("%H:%M")
        
        self.setFixedWidth(600)
        self.setMinimumHeight(60)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        
        # Message text
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        
        # Timestamp
        time_label = QLabel(self.timestamp)
        time_label.setObjectName("timestamp")
        
        layout.addWidget(message_label)
        layout.addWidget(time_label)
        
        self.setLayout(layout)
        self.setObjectName("userBubble" if is_user else "tiyaBubble")

class StatusIndicator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(100, 30)
        self.status = "offline"  # offline, connecting, online, thinking
        self.pulse_value = 0
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_pulse)
        self.timer.start(50)
    
    def set_status(self, status):
        self.status = status
        self.update()
    
    def update_pulse(self):
        self.pulse_value = (self.pulse_value + 5) % 360
        if self.status in ["connecting", "thinking"]:
            self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        colors = {
            "offline": QColor("#666666"),
            "connecting": QColor("#ffff00"),
            "online": QColor("#00ff88"),
            "thinking": QColor("#00f7ff")
        }
        
        color = colors.get(self.status, QColor("#666666"))
        
        if self.status in ["connecting", "thinking"]:
            pulse_factor = (math.sin(math.radians(self.pulse_value)) + 1) / 2
            alpha = int(100 + 155 * pulse_factor)
            color.setAlpha(alpha)
        
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(5, 10, 10, 10)
        
        painter.setPen(color)
        painter.setFont(QFont("Courier New", 8))
        painter.drawText(20, 20, self.status.upper())

class AIResponseThread(QThread):
    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, message, api_key):
        super().__init__()
        self.message = message
        self.api_key = api_key
    
    def run(self):
        """Generate AI response using Gemini API or mock response"""
        try:
            if GEMINI_AVAILABLE and self.api_key:
                # Configure Gemini API
                genai.configure(api_key=self.api_key)
                
                # Create model
                model = genai.GenerativeModel('gemini-pro')
                
                # Generate response with T.I.Y.A. personality
                prompt = f"""You are T.I.Y.A. (Transcendent Intelligence Yielding Assistant), an advanced AI assistant with a futuristic, sophisticated personality. 
                
Respond to the following message in character as T.I.Y.A.:
- Use a professional yet friendly tone
- Occasionally reference your advanced capabilities
- Be helpful and informative
- Keep responses concise but thorough

User message: {self.message}"""
                
                response = model.generate_content(prompt)
                
                if response and response.text:
                    self.response_ready.emit(response.text)
                else:
                    self.error_occurred.emit("Failed to generate response")
                    
            else:
                # Mock response when Gemini is not available
                import time
                time.sleep(random.uniform(1, 3))  # Simulate processing time
                
                mock_responses = [
                    f"I've processed your query '{self.message}' through my neural networks. While I'm currently operating in simulation mode, I can still assist you with information and guidance.",
                    f"Your message has been analyzed by my cognitive matrix. Regarding '{self.message}', I recommend we explore this topic further when my full API capabilities are enabled.",
                    f"Neural processing complete. I understand you're asking about '{self.message}'. In my current limited mode, I can provide basic assistance.",
                    f"T.I.Y.A. systems acknowledge: '{self.message}'. My quantum processors are ready to help, though full functionality requires API configuration.",
                    f"Cognitive analysis of your input '{self.message}' shows multiple response pathways. I'm here to assist within my current operational parameters."
                ]
                
                response = random.choice(mock_responses)
                self.response_ready.emit(response)
                
        except Exception as e:
            self.error_occurred.emit(f"AI processing error: {str(e)}")

class TIYAMainAssistant(QWidget):
    def __init__(self, api_key="", username="Operator"):
        super().__init__()
        self.api_key = api_key
        self.username = username
        self.chat_history = []
        
        self.setWindowTitle("T.I.Y.A. - Transcendent Intelligence Interface")
        self.setGeometry(100, 100, 1400, 900)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.init_ui()
        self.setup_animations()
    
    def init_ui(self):
        # Base layout with background
        base_layout = QStackedLayout()
        base_layout.setStackingMode(QStackedLayout.StackingMode.StackAll)
        
        # Neural network background
        self.background = NeuralBackgroundWidget()
        base_layout.addWidget(self.background)
        
        # Main content
        main_widget = QWidget()
        main_widget.setObjectName("mainWidget")
        base_layout.addWidget(main_widget)
        
        self.setLayout(base_layout)
        
        # Main layout
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(0)
        
        # Header
        header = self.create_header()
        main_layout.addWidget(header)
        
        # Content area
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Chat
        chat_panel = self.create_chat_panel()
        content_splitter.addWidget(chat_panel)
        
        # Right panel - Controls
        control_panel = self.create_control_panel()
        content_splitter.addWidget(control_panel)
        
        content_splitter.setSizes([1000, 400])
        main_layout.addWidget(content_splitter)
        
        # Input area
        input_area = self.create_input_area()
        main_layout.addWidget(input_area)
        
        self.setStyleSheet(self.get_stylesheet())
    
    def create_header(self):
        header = QFrame()
        header.setObjectName("header")
        header.setFixedHeight(80)
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(30, 15, 30, 15)
        
        # Title section
        title_layout = QVBoxLayout()
        title = QLabel("T.I.Y.A.")
        title.setObjectName("headerTitle")
        subtitle = QLabel("Transcendent Intelligence Yielding Assistant")
        subtitle.setObjectName("headerSubtitle")
        
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        
        # Status section
        status_layout = QHBoxLayout()
        status_layout.addStretch()
        
        self.status_indicator = StatusIndicator()
        self.status_indicator.set_status("online" if self.api_key else "offline")
        
        user_label = QLabel(f"Welcome, {self.username}")
        user_label.setObjectName("userLabel")
        
        status_layout.addWidget(self.status_indicator)
        status_layout.addWidget(user_label)
        
        layout.addLayout(title_layout)
        layout.addLayout(status_layout)
        
        return header
    
    def create_chat_panel(self):
        chat_panel = QFrame()
        chat_panel.setObjectName("chatPanel")
        
        layout = QVBoxLayout(chat_panel)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Chat header
        chat_header = QLabel("NEURAL CONVERSATION INTERFACE")
        chat_header.setObjectName("panelHeader")
        layout.addWidget(chat_header)
        
        # Chat area
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setObjectName("chatScroll")
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.chat_widget = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_widget)
        self.chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.chat_layout.setSpacing(15)
        
        self.chat_scroll.setWidget(self.chat_widget)
        layout.addWidget(self.chat_scroll)
        
        # Add welcome message
        self.add_tiya_message("Neural interface initialized. How may I assist you today?")
        
        return chat_panel
    
    def create_control_panel(self):
        control_panel = QFrame()
        control_panel.setObjectName("controlPanel")
        
        layout = QVBoxLayout(control_panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # System status
        status_header = QLabel("SYSTEM STATUS")
        status_header.setObjectName("panelHeader")
        layout.addWidget(status_header)
        
        status_frame = QFrame()
        status_frame.setObjectName("statusFrame")
        status_layout = QVBoxLayout(status_frame)
        
        # API Status
        api_status = QLabel("API CONNECTION:" + (" ACTIVE" if self.api_key else " INACTIVE"))
        api_status.setObjectName("statusActive" if self.api_key else "statusInactive")
        status_layout.addWidget(api_status)
        
        # Memory usage (mock)
        memory_label = QLabel("NEURAL MEMORY: 73% UTILIZED")
        memory_label.setObjectName("statusInfo")
        self.memory_bar = QProgressBar()
        self.memory_bar.setValue(73)
        self.memory_bar.setObjectName("progressBar")
        status_layout.addWidget(memory_label)
        status_layout.addWidget(self.memory_bar)
        
        # Processing power (mock)
        processing_label = QLabel("QUANTUM PROCESSING: OPTIMAL")
        processing_label.setObjectName("statusActive")
        status_layout.addWidget(processing_label)
        
        layout.addWidget(status_frame)
        
        # Quick actions
        actions_header = QLabel("QUICK ACTIONS")
        actions_header.setObjectName("panelHeader")
        layout.addWidget(actions_header)
        
        actions_frame = QFrame()
        actions_frame.setObjectName("actionsFrame")
        actions_layout = QVBoxLayout(actions_frame)
        
        clear_btn = QPushButton("CLEAR CONVERSATION")
        clear_btn.setObjectName("actionButton")
        clear_btn.clicked.connect(self.clear_chat)
        
        export_btn = QPushButton("EXPORT LOGS")
        export_btn.setObjectName("actionButton")
        export_btn.clicked.connect(self.export_chat)
        
        settings_btn = QPushButton("NEURAL SETTINGS")
        settings_btn.setObjectName("actionButton")
        
        actions_layout.addWidget(clear_btn)
        actions_layout.addWidget(export_btn)
        actions_layout.addWidget(settings_btn)
        
        layout.addWidget(actions_frame)
        layout.addStretch()
        
        return control_panel
    
    def create_input_area(self):
        input_area = QFrame()
        input_area.setObjectName("inputArea")
        input_area.setFixedHeight(80)
        
        layout = QHBoxLayout(input_area)
        layout.setContentsMargins(30, 15, 30, 15)
        layout.setSpacing(15)
        
        self.message_input = QLineEdit()
        self.message_input.setObjectName("messageInput")
        self.message_input.setPlaceholderText("Enter your message to T.I.Y.A...")
        self.message_input.returnPressed.connect(self.send_message)
        
        self.send_button = QPushButton("TRANSMIT")
        self.send_button.setObjectName("sendButton")
        self.send_button.clicked.connect(self.send_message)
        
        layout.addWidget(self.message_input)
        layout.addWidget(self.send_button)
        
        return input_area
    
    def add_user_message(self, message):
        bubble = ChatBubble(message, is_user=True)
        self.chat_layout.addWidget(bubble, 0, Qt.AlignmentFlag.AlignRight)
        self.scroll_to_bottom()
    
    def add_tiya_message(self, message):
        bubble = ChatBubble(message, is_user=False)
        self.chat_layout.addWidget(bubble, 0, Qt.AlignmentFlag.AlignLeft)
        self.scroll_to_bottom()
    
    def scroll_to_bottom(self):
        QTimer.singleShot(100, lambda: self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        ))
    
    def send_message(self):
        message = self.message_input.text().strip()
        if not message:
            return
        
        # Add user message
        self.add_user_message(message)
        self.message_input.clear()
        
        # Show thinking status
        self.status_indicator.set_status("thinking")
        
        # Process with AI (if API key available)
        if self.api_key:
            self.ai_thread = AIResponseThread(message, self.api_key)
            self.ai_thread.response_ready.connect(self.handle_ai_response)
            self.ai_thread.error_occurred.connect(self.handle_ai_error)
            self.ai_thread.start()
        else:
            QTimer.singleShot(1000, lambda: self.handle_ai_response(
                "I'm currently operating in limited mode. Please configure your API key to enable full cognitive capabilities."
            ))
    
    def handle_ai_response(self, response):
        self.status_indicator.set_status("online" if self.api_key else "offline")
        self.add_tiya_message(response)
    
    def handle_ai_error(self, error_message):
        self.status_indicator.set_status("offline")
        self.add_tiya_message(f"⚠️ Neural processing error: {error_message}")
        print(f"AI Error: {error_message}")
    
    def clear_chat(self):
        # Clear all chat bubbles except welcome message
        for i in reversed(range(self.chat_layout.count())):
            child = self.chat_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        # Re-add welcome message
        self.add_tiya_message("Neural interface reinitialized. How may I assist you today?")
    
    def export_chat(self):
        # Mock export functionality
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tiya_conversation_{timestamp}.txt"
        
        # In a real implementation, you would save the chat history
        self.add_tiya_message(f"Conversation log exported to {filename}")
    
    def setup_animations(self):
        # Fade in animation
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(1000)
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fade_animation.start()
    
    def get_stylesheet(self):
        return """
            QWidget#mainWidget {
                background: transparent;
            }
            
            QFrame#header {
                background: rgba(10, 15, 25, 200);
                border: 1px solid rgba(0, 247, 255, 50);
                border-radius: 10px;
                margin-bottom: 10px;
            }
            
            QLabel#headerTitle {
                font-family: 'Orbitron', sans-serif;
                font-size: 24px;
                font-weight: bold;
                color: #ffffff;
                text-shadow: 0 0 15px #00f7ff;
                letter-spacing: 5px;
            }
            
            QLabel#headerSubtitle {
                font-family: 'Courier New', monospace;
                font-size: 10px;
                color: rgba(0, 247, 255, 180);
                font-style: italic;
            }
            
            QLabel#userLabel {
                font-family: 'Courier New', monospace;
                font-size: 12px;
                color: rgba(0, 247, 255, 180);
                font-weight: bold;
            }
            
            QFrame#chatPanel, QFrame#controlPanel {
                background: rgba(10, 15, 25, 150);
                border: 1px solid rgba(0, 247, 255, 50);
                border-radius: 10px;
            }
            
            QLabel#panelHeader {
                font-family: 'Orbitron', sans-serif;
                font-size: 14px;
                font-weight: bold;
                color: #00f7ff;
                text-shadow: 0 0 10px #00f7ff;
                letter-spacing: 2px;
                padding: 10px 0;
            }
            
            QScrollArea#chatScroll {
                background: transparent;
                border: none;
            }
            
            QFrame#userBubble {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00f7ff, stop:1 #008c9e);
                border-radius: 15px;
                color: #05080f;
                font-family: 'Courier New', monospace;
                font-size: 12px;
                margin: 5px;
            }
            
            QFrame#tiyaBubble {
                background: rgba(0, 0, 0, 150);
                border: 1px solid rgba(0, 247, 255, 80);
                border-radius: 15px;
                color: #e0ffff;
                font-family: 'Courier New', monospace;
                font-size: 12px;
                margin: 5px;
            }
            
            QLabel#timestamp {
                font-size: 9px;
                color: rgba(255, 255, 255, 100);
                font-style: italic;
            }
            
            QFrame#statusFrame, QFrame#actionsFrame {
                background: rgba(0, 0, 0, 100);
                border: 1px solid rgba(0, 247, 255, 50);
                border-radius: 8px;
                padding: 15px;
            }
            
            QLabel#statusActive {
                color: #00ff88;
                text-shadow: 0 0 5px #00ff88;
                font-family: 'Courier New', monospace;
                font-size: 11px;
                font-weight: bold;
            }
            
            QLabel#statusInactive {
                color: #ff6b6b;
                text-shadow: 0 0 5px #ff6b6b;
                font-family: 'Courier New', monospace;
                font-size: 11px;
                font-weight: bold;
            }
            
            QLabel#statusInfo {
                color: rgba(0, 247, 255, 180);
                font-family: 'Courier New', monospace;
                font-size: 11px;
            }
            
            QProgressBar#progressBar {
                border: 1px solid rgba(0, 247, 255, 80);
                border-radius: 5px;
                background: rgba(0, 0, 0, 100);
                height: 8px;
            }
            
            QProgressBar#progressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00f7ff, stop:1 #008c9e);
                border-radius: 4px;
            }
            
            QPushButton#actionButton {
                background: rgba(0, 0, 0, 150);
                border: 1px solid rgba(0, 247, 255, 80);
                border-radius: 6px;
                color: #e0ffff;
                font-family: 'Courier New', monospace;
                font-size: 11px;
                font-weight: bold;
                padding: 8px 15px;
                letter-spacing: 1px;
            }
            
            QPushButton#actionButton:hover {
                background: rgba(0, 247, 255, 20);
                border: 1px solid #00f7ff;
            }
            
            QFrame#inputArea {
                background: rgba(10, 15, 25, 200);
                border: 1px solid rgba(0, 247, 255, 50);
                border-radius: 10px;
                margin-top: 10px;
            }
            
            QLineEdit#messageInput {
                background: rgba(0, 0, 0, 150);
                border: 1px solid rgba(0, 247, 255, 80);
                border-radius: 8px;
                padding: 12px 15px;
                color: #e0ffff;
                font-size: 14px;
                font-family: 'Courier New', monospace;
            }
            
            QLineEdit#messageInput:focus {
                border: 1px solid #00f7ff;
                background: rgba(0, 20, 30, 150);
            }
            
            QLineEdit#messageInput::placeholder {
                color: rgba(0, 247, 255, 100);
            }
            
            QPushButton#sendButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00f7ff, stop:1 #008c9e);
                color: #05080f;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                font-family: 'Orbitron', sans-serif;
                padding: 12px 25px;
                letter-spacing: 2px;
                min-width: 120px;
            }
            
            QPushButton#sendButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ffffff, stop:1 #00f7ff);
                color: #000000;
            }
        """
    
    def mousePressEvent(self, event):
        self.oldPos = event.globalPos()
    
    def mouseMoveEvent(self, event):
        if hasattr(self, 'oldPos'):
            delta = event.globalPos() - self.oldPos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.oldPos = event.globalPos()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TIYAMainAssistant(api_key="demo_key", username="Test User")
    
    # Center the window
    screen_geometry = app.primaryScreen().geometry()
    x = (screen_geometry.width() - window.width()) // 2
    y = (screen_geometry.height() - window.height()) // 2
    window.move(x, y)
    
    window.show()
    sys.exit(app.exec())