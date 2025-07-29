import sys
import json
import os
import threading
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QHBoxLayout, QScrollArea, QFrame
)
from PyQt5.QtGui import (
    QFont, QPixmap, QPalette, QColor, QPainter, QBrush, QLinearGradient, QPen,
    QTextCursor, QImage, QFontDatabase, QRadialGradient
)
from PyQt5.QtCore import (
    Qt, QTimer, QPointF, QThread, pyqtSignal, QSize, QRect
)
import math
import random
import cv2
import numpy as np

# Audio imports with fallbacks
try:
    import speech_recognition as sr
    import pyttsx3
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("Warning: speech_recognition and/or pyttsx3 not installed. Audio features disabled.")

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("Warning: google-generativeai not installed. Using mock responses.")

# --- WAKE WORD LISTENER THREAD ---
class WakeWordListener(QThread):
    """
    A QThread that continuously listens for a wake word in the background.
    """
    wakeWordDetected = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.recognizer = sr.Recognizer() if AUDIO_AVAILABLE else None
        self.microphone = sr.Microphone() if AUDIO_AVAILABLE else None
        self.running = False

    def run(self):
        if not AUDIO_AVAILABLE:
            print("Wake word listener disabled: Audio libraries not available.")
            return

        self.running = True
        print("Wake word listener started. Say 'Tiya' to activate.")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1.0)
            self.recognizer.dynamic_energy_threshold = True

            while self.running:
                try:
                    audio = self.recognizer.listen(source, phrase_time_limit=2.5)
                    text = self.recognizer.recognize_google(audio).lower()

                    if "tiya" in text:
                        print("Wake word 'Tiya' detected!")
                        self.wakeWordDetected.emit()
                except sr.UnknownValueError:
                    pass # Ignore if it can't understand
                except sr.RequestError as e:
                    print(f"Could not request results from Google Speech Recognition service; {e}")
                except Exception as e:
                    print(f"An error occurred in wake word listener: {e}")

    def stop(self):
        self.running = False
        print("Wake word listener stopped.")
        self.quit()
        self.wait(2000) # Wait up to 2 seconds for thread to finish

# --- GUI WIDGETS (CircularHUD, EnhancedWebcamFeed, etc.) ---

class CircularHUD(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(280, 280)
        self.pulse = 0
        self.rotation = 0
        self.audio_levels = [0] * 32
        self.status = "STANDBY" # Can be STANDBY, LISTENING, SPEAKING, PROCESSING

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(16)  # ~60 FPS

    def set_status(self, status):
        """Sets the current status of the HUD"""
        self.status = status.upper()
        self.update()

    def set_audio_levels(self, levels):
        self.audio_levels = levels[:32] if len(levels) >= 32 else levels + [0] * (32 - len(levels))

    def animate(self):
        self.rotation = (self.rotation + 0.5) % 360
        self.pulse = (self.pulse + 2) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        center = QPointF(140, 140)

        # Draw outer ring segments (like in reference image)
        painter.setPen(QPen(QColor(60, 60, 80), 2))
        for i in range(0, 360, 10):
            start_angle = i + self.rotation
            color = QColor(0, 247, 255, 200) if i % 30 == 0 else QColor(80, 80, 100, 150)
            painter.setPen(QPen(color, 2))
            painter.drawArc(QRect(10, 10, 260, 260), int(start_angle * 16), 8 * 16)

        # Draw audio visualization ring
        if self.status in ["LISTENING", "SPEAKING"]:
            for i, level in enumerate(self.audio_levels):
                angle = (i * 360 / len(self.audio_levels)) + self.rotation
                level_height = max(3, level * 20)
                color = QColor(0, 255, 100) if self.status == "LISTENING" else QColor(255, 100, 0)
                color.setAlpha(int(150 + level * 105))
                painter.setPen(QPen(color, 2))
                inner_r, outer_r = 105, 105 + level_height
                x1, y1 = center.x() + inner_r * math.cos(math.radians(angle)), center.y() + inner_r * math.sin(math.radians(angle))
                x2, y2 = center.x() + outer_r * math.cos(math.radians(angle)), center.y() + outer_r * math.sin(math.radians(angle))
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        # Central core and status text
        gradient = QRadialGradient(center, 70)
        gradient.setColorAt(0, QColor(0, 247, 255, 200))
        gradient.setColorAt(0.7, QColor(0, 150, 200, 100))
        gradient.setColorAt(1, QColor(0, 50, 80, 50))
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor(0, 247, 255, 150), 2))
        painter.drawEllipse(center.toPoint(), 70, 70)

        status_color = {
            "LISTENING": QColor(0, 255, 100),
            "SPEAKING": QColor(255, 100, 0),
            "PROCESSING": QColor(255, 200, 0),
        }.get(self.status, QColor(0, 247, 255))
        
        painter.setPen(status_color)
        font = QFont("Orbitron", 10, QFont.Bold)
        painter.setFont(font)
        text_rect = painter.fontMetrics().boundingRect(self.status)
        painter.drawText(QRect(center.toPoint() - QPointF(text_rect.width()/2, -text_rect.height()/2).toPoint(), text_rect.size()), Qt.AlignCenter, self.status)

class AudioProcessor:
    def __init__(self, hud_widget):
        self.hud = hud_widget
        self.tts_engine = pyttsx3.init() if AUDIO_AVAILABLE else None
        if AUDIO_AVAILABLE:
            self.tts_engine.setProperty('rate', 180)
            voices = self.tts_engine.getProperty('voices')
            if voices:
                for voice in voices:
                    if 'english' in voice.name.lower():
                        self.tts_engine.setProperty('voice', voice.id)
                        break

    def speak(self, text, callback=None):
        if not AUDIO_AVAILABLE:
            print(f"TTS (disabled): {text}")
            if callback: callback()
            return

        def speak_thread():
            self.hud.set_status("SPEAKING")
            
            # Simulate audio levels while speaking
            duration = len(text.split()) * 0.3 # Approximate duration
            num_steps = int(duration / 0.1)
            for i in range(num_steps):
                levels = [0.3 + random.random() * 0.4 for _ in range(32)]
                self.hud.set_audio_levels(levels)
                threading.Event().wait(0.1)

            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
            
            self.hud.set_audio_levels([0] * 32)
            self.hud.set_status("STANDBY")
            if callback:
                QTimer.singleShot(0, callback) # Safely call back to main thread

        threading.Thread(target=speak_thread).start()


class EnhancedWebcamFeed(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.cap = cv2.VideoCapture(0)
        self.setFixedSize(140, 140)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)
        
        self.face_cascade = None
        if os.path.exists(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'):
            self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        self.create_default_avatar()

    def create_default_avatar(self):
        self.default_pixmap = QPixmap(140, 140)
        self.default_pixmap.fill(Qt.transparent)
        painter = QPainter(self.default_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        center = QPointF(70, 70)
        
        gradient = QRadialGradient(center, 65)
        gradient.setColorAt(0, QColor(0, 247, 255, 100))
        gradient.setColorAt(1, QColor(0, 100, 150, 0))
        painter.setBrush(gradient)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(5, 5, 130, 130)
        
        painter.setBrush(QColor(20, 20, 40, 200))
        painter.setPen(QPen(QColor(0, 247, 255, 200), 2))
        painter.drawEllipse(15, 15, 110, 110)
        
        painter.setPen(QPen(QColor(0, 247, 255, 100), 1))
        for i in range(-5, 6):
            painter.drawLine(QPointF(70 + i*10, 20), QPointF(70+i*10, 120))
            painter.drawLine(QPointF(20, 70 + i*10), QPointF(120, 70+i*10))
            
        painter.end()
        self.setPixmap(self.default_pixmap)

    def update_frame(self):
        try:
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.flip(frame, 1)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                if self.face_cascade:
                    gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
                    faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
                    for (x, y, w, h) in faces:
                        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 247, 255), 2)
                
                h, w, ch = frame.shape
                qt_img = QImage(frame.data, w, h, ch * w, QImage.Format_RGB888)
                pix = QPixmap.fromImage(qt_img).scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                
                mask = QPixmap(self.size())
                mask.fill(Qt.transparent)
                painter = QPainter(mask)
                painter.setBrush(Qt.white)
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(0, 0, self.width(), self.height())
                painter.end()
                pix.setMask(mask.createMaskFromColor(Qt.transparent))
                self.setPixmap(pix)
            else:
                 self.setPixmap(self.default_pixmap)
        except Exception:
            self.setPixmap(self.default_pixmap)

    def closeEvent(self, event):
        if self.cap.isOpened():
            self.cap.release()
        super().closeEvent(event)

# --- MAIN APPLICATION WINDOW ---

class EnhancedTIYAAssistant(QWidget):
    def __init__(self, api_key="", username="Operator"):
        super().__init__()
        self.api_key = api_key
        self.username = username
        self.chat_history = []
        
        self.setWindowTitle("T.I.Y.A. - Advanced Quantum Interface")
        self.setGeometry(100, 50, 1200, 700)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.background_image = QPixmap("./background.jpg")

        self.init_ui()
        self.setup_audio_and_wake_word()
        self.oldPos = self.pos()

    def paintEvent(self, event):
        painter = QPainter(self)
        if not self.background_image.isNull():
             # Draw the background image to cover the widget's area
            painter.drawPixmap(self.rect(), self.background_image)
        else:
             # Fallback if image not found
            painter.fillRect(self.rect(), QColor(10, 15, 25, 255))

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        left_panel = self.create_left_panel()
        right_panel = self.create_right_panel()

        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 2)

        self.setStyleSheet(self.get_enhanced_stylesheet())

    def create_left_panel(self):
        panel = QFrame()
        panel.setObjectName("leftPanel")
        panel.setFixedWidth(350)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        title = QLabel("T.I.Y.A. v9.4.2")
        title.setObjectName("mainTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self.hud = CircularHUD()
        layout.addWidget(self.hud, 0, Qt.AlignCenter)

        self.webcam = EnhancedWebcamFeed()
        layout.addWidget(self.webcam, 0, Qt.AlignCenter)

        button_layout = QHBoxLayout()
        self.mic_button = QPushButton("MIC OFF")
        self.mic_button.setObjectName("controlButton")
        self.mic_button.setCheckable(True)
        self.mic_button.setChecked(False)
        self.mic_button.clicked.connect(self.toggle_wake_word_listener)
        
        self.mute_button = QPushButton("AUDIO ON")
        self.mute_button.setObjectName("controlButton")
        self.mute_button.setCheckable(True)
        self.mute_button.setChecked(True)
        self.mute_button.clicked.connect(self.toggle_audio_output)

        button_layout.addWidget(self.mic_button)
        button_layout.addWidget(self.mute_button)
        layout.addLayout(button_layout)
        
        self.status_label = QLabel("QUANTUM CORE: ONLINE")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        return panel

    def create_right_panel(self):
        panel = QFrame()
        panel.setObjectName("rightPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        header = QLabel("QUANTUM COMMUNICATION CHANNEL")
        header.setObjectName("chatHeader")
        layout.addWidget(header)

        self.chat_scroll = QScrollArea()
        self.chat_scroll.setObjectName("chatScroll")
        self.chat_scroll.setWidgetResizable(True)
        self.chat_widget = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_widget)
        self.chat_layout.setAlignment(Qt.AlignTop)
        self.chat_layout.setSpacing(15)
        self.chat_scroll.setWidget(self.chat_widget)
        layout.addWidget(self.chat_scroll)

        input_layout = QHBoxLayout()
        self.message_input = QLineEdit()
        self.message_input.setObjectName("messageInput")
        self.message_input.setPlaceholderText("Enter quantum communication...")
        self.message_input.returnPressed.connect(self.send_message)
        self.send_button = QPushButton("TRANSMIT")
        self.send_button.setObjectName("sendButton")
        self.send_button.clicked.connect(self.send_message)
        input_layout.addWidget(self.message_input)
        input_layout.addWidget(self.send_button)
        layout.addLayout(input_layout)

        self.add_tiya_message("Quantum communication channel established\nAll systems online and ready\nVoice recognition: " + ("ACTIVE" if AUDIO_AVAILABLE else "UNAVAILABLE"), speak=False)
        return panel

    def setup_audio_and_wake_word(self):
        self.audio_processor = AudioProcessor(self.hud) if AUDIO_AVAILABLE else None
        self.wake_word_thread = WakeWordListener(self)
        self.wake_word_thread.wakeWordDetected.connect(self.handle_wake_word)

    def toggle_wake_word_listener(self):
        if self.mic_button.isChecked():
            self.mic_button.setText("MIC ON")
            self.status_label.setText("MONITORING FOR WAKE WORD 'Tiya'")
            self.wake_word_thread.start()
        else:
            self.mic_button.setText("MIC OFF")
            self.status_label.setText("QUANTUM CORE: ONLINE")
            self.wake_word_thread.stop()
            self.hud.set_status("STANDBY")

    def toggle_audio_output(self):
        if self.mute_button.isChecked():
            self.mute_button.setText("AUDIO ON")
            self.add_tiya_message("Audio output enabled.", speak=False)
        else:
            self.mute_button.setText("AUDIO OFF")
            self.add_tiya_message("Audio output disabled.", speak=False)

    def handle_wake_word(self):
        """Called when the wake word is detected."""
        if not self.mic_button.isChecked(): return # Don't respond if mic is toggled off
        
        self.status_label.setText("WAKE WORD DETECTED. LISTENING...")
        self.listen_for_command()

    def listen_for_command(self):
        if not AUDIO_AVAILABLE: return

        def listen_thread_fn():
            recognizer = sr.Recognizer()
            microphone = sr.Microphone()
            
            # Simulate listening audio levels
            def simulate_listening():
                for _ in range(50): # 5 seconds max
                    if self.hud.status != "LISTENING": break
                    levels = [random.random() * 0.8 for _ in range(32)]
                    QTimer.singleShot(0, lambda: self.hud.set_audio_levels(levels))
                    threading.Event().wait(0.1)

            QTimer.singleShot(0, lambda: self.hud.set_status("LISTENING"))
            sim_thread = threading.Thread(target=simulate_listening)
            sim_thread.start()

            try:
                with microphone as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
                
                text = recognizer.recognize_google(audio)
                QTimer.singleShot(0, lambda: self.process_voice_input(text))

            except (sr.WaitTimeoutError, sr.UnknownValueError, sr.RequestError) as e:
                error_msg = f"Voice input error: {type(e).__name__}"
                QTimer.singleShot(0, lambda: self.add_tiya_message(error_msg))
                QTimer.singleShot(0, self.reset_to_monitoring)
            finally:
                QTimer.singleShot(0, lambda: self.hud.set_audio_levels([0]*32))


        threading.Thread(target=listen_thread_fn).start()

    def reset_to_monitoring(self):
        self.hud.set_status("STANDBY")
        if self.mic_button.isChecked():
            self.status_label.setText("MONITORING FOR WAKE WORD 'Tiya'")
        else:
            self.status_label.setText("QUANTUM CORE: ONLINE")


    def process_voice_input(self, text):
        self.add_user_message(f"[VOICE]: {text}")
        self.generate_response(text)
    
    def send_message(self):
        message = self.message_input.text().strip()
        if not message: return
        self.add_user_message(message)
        self.message_input.clear()
        self.generate_response(message)

    def generate_response(self, message):
        self.hud.set_status("PROCESSING")
        self.status_label.setText("PROCESSING QUANTUM RESPONSE...")
        
        def response_thread():
            try:
                if GEMINI_AVAILABLE and self.api_key:
                    # ... (Gemini API call logic remains the same)
                    genai.configure(api_key=self.api_key)
                    model = genai.GenerativeModel('gemini-pro')
                    prompt = f"""You are T.I.Y.A. (2300 AD Quantum Intelligence), an advanced AI. Respond as a futuristic assistant:
                    - Use quantum computing metaphors.
                    - Keep responses concise but informative.
                    - Sign messages with "// T-I-Y-A Quantum Core"
                    User: {message}"""
                    response = model.generate_content(prompt)
                    response_text = response.text
                else:
                    responses = [
                        "Quantum analysis complete. Your query aligns with probability matrix 7-Gamma. Optimal solution path calculated.",
                        "Temporal calculations initiated. Calibrating response to your precise timeline. Quantum entanglement stable.",
                        "Neural networks synchronized. Processing complete. All quantum states are aligned for this outcome."
                    ]
                    response_text = f"{random.choice(responses)}\n\n// T-I-Y-A Quantum Core"
                
                QTimer.singleShot(0, lambda: self.add_tiya_message(response_text, speak=True))
            except Exception as e:
                error_text = f"System error: {str(e)}\n\n// T-I-Y-A Quantum Core"
                QTimer.singleShot(0, lambda: self.add_tiya_message(error_text, speak=True))

        threading.Thread(target=response_thread).start()

    def add_user_message(self, message):
        bubble = QFrame()
        bubble.setObjectName("userBubble")
        layout = QVBoxLayout(bubble)
        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet("color: #000; font: 12px 'Courier New';")
        time_label = QLabel(datetime.now().strftime("%H:%M:%S"))
        time_label.setStyleSheet("color: rgba(0,0,0,100); font-size: 9px;")
        layout.addWidget(msg_label)
        layout.addWidget(time_label)
        
        container_widget = QWidget()
        container_layout = QHBoxLayout(container_widget)
        container_layout.addStretch()
        container_layout.addWidget(bubble)
        self.chat_layout.addWidget(container_widget)
        self.scroll_to_bottom()
    
    def add_tiya_message(self, message, speak=True):
        bubble = QFrame()
        bubble.setObjectName("tiyaBubble")
        layout = QVBoxLayout(bubble)
        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet("color: #e0ffff; font: 12px 'Courier New';")
        time_label = QLabel(datetime.now().strftime("%H:%M:%S"))
        time_label.setStyleSheet("color: rgba(255,255,255,100); font-size: 9px;")
        layout.addWidget(msg_label)
        layout.addWidget(time_label)
        
        container_widget = QWidget()
        container_layout = QHBoxLayout(container_widget)
        container_layout.addWidget(bubble)
        container_layout.addStretch()
        self.chat_layout.addWidget(container_widget)
        self.scroll_to_bottom()
        
        tts_text = message.replace("// T-I-Y-A Quantum Core", "").strip()
        if speak and self.mute_button.isChecked() and AUDIO_AVAILABLE and self.audio_processor and tts_text:
            self.audio_processor.speak(tts_text, callback=self.reset_to_monitoring)
        else:
            self.reset_to_monitoring()
            
    def scroll_to_bottom(self):
        QTimer.singleShot(100, lambda: self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()))

    def get_enhanced_stylesheet(self):
        return """
        QWidget {
            background: transparent;
            font-family: 'Orbitron', 'Courier New', monospace;
        }
        QFrame#leftPanel, QFrame#rightPanel {
            background: rgba(10, 15, 25, 210); /* Frosted Glass */
            border: 1px solid rgba(0, 247, 255, 100);
            border-radius: 15px;
        }
        QLabel#mainTitle {
            font: bold 20px 'Orbitron'; color: #00f7ff; letter-spacing: 2px; padding: 8px;
        }
        QLabel#chatHeader {
            font: bold 14px 'Orbitron'; color: #00f7ff; letter-spacing: 1px; padding: 8px 0;
            border-bottom: 1px solid rgba(0, 247, 255, 80);
        }
        QLabel#statusLabel {
            font: bold 10px 'Orbitron'; color: #00ff88; letter-spacing: 1px; padding: 5px;
        }
        QPushButton#controlButton {
            background: rgba(0, 247, 255, 30);
            color: #00f7ff; border: 1px solid #00f7ff; border-radius: 6px;
            font: bold 10px 'Orbitron'; padding: 8px; letter-spacing: 1px;
        }
        QPushButton#controlButton:hover { background: rgba(0, 247, 255, 50); }
        QPushButton#controlButton:checked { background: #00f7ff; color: #000; }
        
        QScrollArea#chatScroll { background: transparent; border: none; }
        QScrollBar:vertical {
            border: none; background: rgba(0,0,0,50); width: 8px; margin: 0;
        }
        QScrollBar::handle:vertical { background: #00f7ff; min-height: 20px; border-radius: 4px; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }

        QFrame#userBubble {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00f7ff, stop:1 #008c9e);
            border-radius: 15px; margin: 5px; max-width: 450px;
        }
        QFrame#tiyaBubble {
            background: rgba(0, 0, 0, 180);
            border: 1px solid rgba(0, 247, 255, 80);
            border-radius: 15px; margin: 5px; max-width: 450px;
        }
        QLineEdit#messageInput {
            background: rgba(0, 0, 0, 150);
            border: 1px solid rgba(0, 247, 255, 80); border-radius: 8px;
            padding: 12px 15px; color: #e0ffff; font: 14px 'Courier New';
        }
        QLineEdit#messageInput:focus {
            border: 2px solid #00f7ff; background: rgba(0, 20, 30, 150);
        }
        QPushButton#sendButton {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00f7ff, stop:1 #008c9e);
            color: #000; border: none; border-radius: 8px;
            font: bold 14px 'Orbitron'; padding: 12px 25px; letter-spacing: 2px;
        }
        QPushButton#sendButton:hover { background: #fff; }
        """
    
    def mousePressEvent(self, event):
        self.oldPos = event.globalPos()
    def mouseMoveEvent(self, event):
        delta = event.globalPos() - self.oldPos
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.oldPos = event.globalPos()
    
    def closeEvent(self, event):
        self.wake_word_thread.stop()
        self.webcam.closeEvent(event)
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    if not os.path.exists("./background.jpg"):
        print("\nWARNING: 'background.jpg' not found. The background will be a solid color.")
        print("For the best experience, place a background image in the same directory as the script.\n")
    
    print("=== T.I.Y.A. Enhanced Assistant Initializing ===")
    if not AUDIO_AVAILABLE:
        print("WARNING: Audio features are disabled. Please install necessary packages:")
        print("pip install SpeechRecognition pyttsx3 pyaudio")
    if not GEMINI_AVAILABLE:
        print("WARNING: Gemini API is not installed. Using mock responses.")
        print("pip install google-generativeai")
    
    window = EnhancedTIYAAssistant(api_key="", username="Quantum User") # Add your Gemini API key here
    
    screen_geometry = app.primaryScreen().geometry()
    x = (screen_geometry.width() - window.width()) // 2
    y = (screen_geometry.height() - window.height()) // 2
    window.move(x, y)
    
    window.show()
    sys.exit(app.exec())