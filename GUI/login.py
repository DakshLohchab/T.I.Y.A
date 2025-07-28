import sys
import math
import random
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QHBoxLayout, QMessageBox, QGraphicsDropShadowEffect, QFrame, QStackedLayout
)
from PyQt5.QtGui import QFont, QPixmap, QPalette, QColor, QPainter, QBrush, QLinearGradient, QPen, QFontDatabase
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty, QRect, QPointF, QSequentialAnimationGroup, QParallelAnimationGroup

# Custom Animated Background Widget
class AnimatedBackground(QWidget):
    """
    A widget that draws an animated background with shimmering stars and grid lines,
    giving a sense of being in a high-tech environment.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.stars = []
        self.init_stars(200)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_stars)
        self.timer.start(50)

    def init_stars(self, number_of_stars):
        screen_size = QApplication.primaryScreen().size()
        for _ in range(number_of_stars):
            self.stars.append({
                "pos": QPointF(random.randint(0, screen_size.width()), random.randint(0, screen_size.height())),
                "opacity": random.uniform(0.1, 0.7),
                "fall_speed": random.uniform(0.1, 0.5)
            })

    def update_stars(self):
        for star in self.stars:
            star["pos"].setY(star["pos"].y() + star["fall_speed"])
            if star["pos"].y() > self.height():
                star["pos"].setY(0)
                star["pos"].setX(random.randint(0, self.width()))
            
            if random.randint(0, 100) > 95:
                star["opacity"] = random.uniform(0.1, 0.7)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor("#05080f"))
        gradient.setColorAt(1, QColor("#101422"))
        painter.fillRect(self.rect(), gradient)
        
        grid_color = QColor(0, 247, 255, 15)
        painter.setPen(grid_color)
        for i in range(0, self.width(), 40):
            painter.drawLine(i, 0, i, self.height())
        for i in range(0, self.height(), 40):
            painter.drawLine(0, i, self.width(), i)

        for star in self.stars:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255, int(star["opacity"] * 255)))
            painter.drawEllipse(star["pos"], 1, 1)

# Custom Glowing Button
class GlowingButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.glow_effect = QGraphicsDropShadowEffect()
        self.glow_effect.setBlurRadius(30)
        self.glow_effect.setColor(QColor("#00f7ff"))
        self.glow_effect.setOffset(0, 0)
        self.setGraphicsEffect(self.glow_effect)

# Custom Pulsing Label
class PulsingLabel(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self._opacity = 1.0
        self.animation = QPropertyAnimation(self, b"opacity")
        self.animation.setDuration(2500)
        self.animation.setStartValue(0.4)
        self.animation.setEndValue(1.0)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.animation.setLoopCount(-1)
        self.animation.start()

    @pyqtProperty(float)
    def opacity(self):
        return self._opacity

    @opacity.setter
    def opacity(self, value):
        self._opacity = value
        self.setStyleSheet(f"color: rgba(0, 247, 255, {int(value * 200)}); background: transparent;")

# Enhanced Interactive Holographic Sphere Widget
class HolographicSphere(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(300, 300)
        self.setMouseTracking(True) # Enable mouse tracking
        self.angle1, self.angle2, self.angle3 = 0, 0, 0
        self.mouse_influence_x, self.mouse_influence_y = 0, 0
        self.core_pulse_size, self.core_pulse_direction = 1.0, 1
        self.scan_line_y, self.scan_line_dir = -1.0, 0.01

        self.particles = []
        for _ in range(20):
            self.particles.append({
                "angle": random.uniform(0, 360), "radius_factor": random.uniform(1.1, 1.3),
                "speed": random.uniform(0.1, 0.4), "size": random.uniform(1, 2.5)
            })

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(16)

    def update_animation(self):
        self.angle1 = (self.angle1 + 0.5 + self.mouse_influence_y * 0.1) % 360
        self.angle2 = (self.angle2 + 0.8 + self.mouse_influence_x * 0.1) % 360
        self.angle3 = (self.angle3 - 0.3) % 360
        
        self.core_pulse_size += 0.01 * self.core_pulse_direction
        if not 0.8 < self.core_pulse_size < 1.2: self.core_pulse_direction *= -1

        self.scan_line_y += self.scan_line_dir
        if not -1.0 < self.scan_line_y < 1.0: self.scan_line_dir *= -1
            
        for p in self.particles: p["angle"] = (p["angle"] + p["speed"]) % 360
        self.update()

    def mouseMoveEvent(self, event):
        # Make the sphere react to mouse position
        center_x, center_y = self.width() / 2, self.height() / 2
        self.mouse_influence_x = (event.x() - center_x) / center_x
        self.mouse_influence_y = (event.y() - center_y) / center_y
        
    def leaveEvent(self, event):
        # Reset influence when mouse leaves
        self.mouse_influence_x, self.mouse_influence_y = 0, 0

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        center, radius = self.rect().center(), min(self.width(), self.height()) / 3.5

        # Outer Glow
        glow_color = QColor(0, 150, 255, 30)
        painter.setPen(Qt.PenStyle.NoPen)
        for i in range(10):
            glow_color.setAlpha(20 - i*2)
            painter.setBrush(glow_color)
            painter.drawEllipse(center, radius + i * 4, radius + i * 4)

        # Rotating Rings with mouse influence
        painter.save()
        painter.translate(center)
        
        # Apply tilt based on mouse position using shear.
        painter.shear(self.mouse_influence_x * -0.3, self.mouse_influence_y * 0.3)

        pen = QPen(QColor(0, 247, 255, 150), 1)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        # Draw each ring with its own valid 2D rotation.
        # Ring 1 (simulating horizontal rotation axis)
        painter.save()
        painter.rotate(self.angle1)
        painter.drawEllipse(QPointF(0,0), radius, radius * 0.5)
        painter.restore()

        # Ring 2 (simulating vertical rotation axis)
        painter.save()
        painter.rotate(self.angle2)
        painter.drawEllipse(QPointF(0,0), radius * 0.5, radius)
        painter.restore()

        # Ring 3 (simulating z-axis rotation)
        painter.save()
        painter.rotate(self.angle3)
        painter.drawEllipse(QPointF(0,0), radius * 0.9, radius * 0.9)
        painter.restore()
        
        painter.restore()

        # Orbiting particles
        painter.setPen(Qt.PenStyle.NoPen)
        for p in self.particles:
            pr = radius * p["radius_factor"]
            px = center.x() + pr * math.cos(math.radians(p["angle"]))
            py = center.y() + pr * math.sin(math.radians(p["angle"]))
            alpha = int(100 + 155 * abs(math.sin(math.radians(p["angle"]*2))))
            painter.setBrush(QColor(200, 255, 255, alpha))
            painter.drawEllipse(QPointF(px, py), p["size"], p["size"])

        # Pulsing Core
        core_gradient = QLinearGradient(center.x(), center.y() - radius/2, center.x(), center.y() + radius/2)
        core_gradient.setColorAt(0, QColor(200, 255, 255, 255))
        core_gradient.setColorAt(1, QColor(0, 247, 255, 200))
        painter.setBrush(core_gradient)
        painter.setPen(QColor(200, 255, 255, 220))
        painter.drawEllipse(center, (radius / 4) * self.core_pulse_size, (radius / 4) * self.core_pulse_size)

        # Scan line
        scan_y_pos = center.y() + self.scan_line_y * radius
        scan_gradient = QLinearGradient(center.x() - radius, scan_y_pos, center.x() + radius, scan_y_pos)
        scan_gradient.setColorAt(0, QColor(0, 255, 255, 0)); scan_gradient.setColorAt(0.5, QColor(0, 255, 255, 150)); scan_gradient.setColorAt(1, QColor(0, 255, 255, 0))
        painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(scan_gradient)
        painter.drawRect(int(center.x() - radius), int(scan_y_pos - 1), int(radius * 2), 3)

# HUD Overlay for decorative elements
class HUDOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(0, 247, 255, 100), 2)
        painter.setPen(pen)
        
        w, h, p = self.width(), self.height(), 20 # width, height, padding
        l = 30 # line length
        
        # Top-left
        painter.drawLine(p, p, p + l, p)
        painter.drawLine(p, p, p, p + l)
        # Top-right
        painter.drawLine(w - p, p, w - p - l, p)
        painter.drawLine(w - p, p, w - p, p + l)
        # Bottom-left
        painter.drawLine(p, h - p, p + l, h - p)
        painter.drawLine(p, h - p, p, h - p - l)
        # Bottom-right
        painter.drawLine(w - p, h - p, w - p - l, h - p)
        painter.drawLine(w - p, h - p, w - p, h - p - l)

# Main Login Window
class TIYALogin(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TIYA - Transcendent Intelligence Yielding Assistant")
        self.setFixedSize(960, 720)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.init_ui()
        self.setup_animations()

    def init_ui(self):
        base_layout = QStackedLayout()
        base_layout.setStackingMode(QStackedLayout.StackingMode.StackAll)
        
        self.background = AnimatedBackground()
        base_layout.addWidget(self.background)

        self.main_frame = QFrame()
        self.main_frame.setObjectName("mainFrame")
        base_layout.addWidget(self.main_frame)
        
        self.hud_overlay = HUDOverlay(self)
        base_layout.addWidget(self.hud_overlay)

        self.setLayout(base_layout)

        main_hbox = QHBoxLayout(self.main_frame)
        main_hbox.setContentsMargins(0, 0, 0, 0)
        main_hbox.setSpacing(0)

        left_panel = QFrame(); left_panel.setObjectName("leftPanel")
        left_vbox = QVBoxLayout(left_panel); left_vbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar = HolographicSphere(); left_vbox.addWidget(self.avatar)
        
        right_panel = QFrame(); right_panel.setObjectName("rightPanel")
        right_vbox = QVBoxLayout(right_panel); right_vbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_vbox.setContentsMargins(60, 50, 60, 50); right_vbox.setSpacing(25)

        self.title = QLabel("T.I.Y.A."); self.title.setObjectName("title"); self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle = PulsingLabel("Transcendent Intelligence Yielding Assistant"); self.subtitle.setObjectName("subtitle"); self.subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.status = QLabel(""); self.status.setObjectName("statusOnline"); self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.id_label = QLabel("NEURAL IDENTIFICATION:"); self.key_label = QLabel("BIOMETRIC KEY:")
        self.username = QLineEdit(); self.username.setPlaceholderText("Quantum Entanglement ID")
        self.password = QLineEdit(); self.password.setPlaceholderText("Cognitive Authentication Key"); self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.login_btn = GlowingButton("INITIATE CONNECTION"); self.login_btn.clicked.connect(self.handle_login)
        footer = QLabel("TRANSCENDENCE PROTOCOL v3.14 © 2242"); footer.setObjectName("footer"); footer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        right_vbox.addWidget(self.title); right_vbox.addWidget(self.subtitle); right_vbox.addSpacing(20)
        right_vbox.addWidget(self.status); right_vbox.addSpacing(20); right_vbox.addWidget(self.id_label)
        right_vbox.addWidget(self.username); right_vbox.addSpacing(15); right_vbox.addWidget(self.key_label)
        right_vbox.addWidget(self.password); right_vbox.addSpacing(30); right_vbox.addWidget(self.login_btn, 0, Qt.AlignmentFlag.AlignCenter)
        right_vbox.addStretch(); right_vbox.addWidget(footer)

        main_hbox.addWidget(left_panel, 4); main_hbox.addWidget(right_panel, 6)
        self.setStyleSheet(self.get_stylesheet())
        
        self.animatable_widgets = [self.title, self.subtitle, self.id_label, self.username, self.key_label, self.password, self.login_btn]
        for widget in self.animatable_widgets: widget.setVisible(False)

    def get_stylesheet(self):
        return """
            QFrame#mainFrame { background: transparent; }
            QFrame#leftPanel { background-color: rgba(10, 15, 25, 150); border-right: 1px solid rgba(0, 247, 255, 50); }
            QFrame#rightPanel { background-color: rgba(10, 15, 25, 200); }
            QLabel { color: rgba(0, 247, 255, 180); background: transparent; font-family: 'Courier New', monospace; font-size: 11px; font-weight: bold; }
            QLabel#title { font-family: 'Orbitron', sans-serif; font-size: 52px; font-weight: bold; color: #ffffff; text-shadow: 0 0 25px #00f7ff; letter-spacing: 10px; margin-bottom: -10px; }
            QLabel#subtitle { font-family: 'Courier New', monospace; font-size: 12px; font-style: italic; margin-bottom: 20px; }
            QLabel#statusOnline, QLabel#statusGranted { color: #00ff88; text-shadow: 0 0 8px #00ff88; }
            QLabel#statusVerifying { color: #ffff00; text-shadow: 0 0 8px #ffff00; }
            QLabel#statusDenied { color: #ff2222; text-shadow: 0 0 10px #ff2222; font-weight: bold; }
            QLabel#footer { color: rgba(0, 247, 255, 100); font-size: 9px; }
            QLineEdit { background: rgba(0, 0, 0, 100); border: 1px solid rgba(0, 247, 255, 80); border-radius: 8px; padding: 12px 15px; color: #e0ffff; font-size: 14px; font-family: 'Courier New', monospace; }
            QLineEdit:focus { border: 1px solid #00f7ff; background: rgba(0, 20, 30, 150); }
            QLineEdit::placeholder { color: rgba(0, 247, 255, 100); }
            QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00f7ff, stop:1 #008c9e); color: #05080f; border: none; border-radius: 8px; font-weight: bold; font-size: 16px; font-family: 'Orbitron', sans-serif; padding: 12px 25px; letter-spacing: 2px; }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ffffff, stop:1 #00f7ff); color: #000000; }
        """

    def setup_animations(self):
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(1500)
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fade_animation.finished.connect(self.run_boot_sequence)
        self.fade_animation.start()

    def run_boot_sequence(self):
        self.boot_texts = ["INITIALIZING NEURAL INTERFACE...", "CALIBRATING QUANTUM LINK...", "SYSTEM STATUS: ONLINE"]
        self.boot_timer = QTimer()
        self.boot_timer.timeout.connect(self.update_boot_text)
        self.boot_timer.start(700)

    def update_boot_text(self):
        if self.boot_texts:
            self.status.setText(f"● {self.boot_texts.pop(0)}")
        else:
            self.boot_timer.stop()
            self.run_slide_animations()

    def run_slide_animations(self):
        self.anim_group = QParallelAnimationGroup()
        for i, widget in enumerate(self.animatable_widgets):
            widget.setVisible(True)
            # Opacity animation
            opacity_anim = QPropertyAnimation(widget, b"windowOpacity")
            opacity_anim.setDuration(500)
            opacity_anim.setStartValue(0.0)
            opacity_anim.setEndValue(1.0)
            # Position animation
            pos_anim = QPropertyAnimation(widget, b"pos")
            pos_anim.setDuration(600)
            start_pos = widget.pos()
            pos_anim.setStartValue(QPointF(start_pos.x() + 50, start_pos.y()))
            pos_anim.setEndValue(start_pos)
            pos_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            # Add to group with a delay
            self.anim_group.addAnimation(opacity_anim)
            self.anim_group.addAnimation(pos_anim)
            QTimer.singleShot(i * 70, lambda anim=self.anim_group: anim.start())

    def handle_login(self):
        self.status.setText("● VERIFYING COGNITIVE SIGNATURE...")
        self.status.setObjectName("statusVerifying")
        self.setStyleSheet(self.get_stylesheet())
        QTimer.singleShot(2000, lambda: self.process_login(self.username.text().lower(), self.password.text()))

    def process_login(self, user, pwd):
        # UPDATED: Added new user credentials as requested.
        valid_users = {"daksh lohchab": "886", "operator": "quantum", "admin": "singularity", "tiya": "protocol"}
        if user in valid_users and pwd == valid_users[user]:
            self.status.setText("● CONNECTION ESTABLISHED. WELCOME.")
            self.status.setObjectName("statusGranted")
            self.show_message_box("Access Granted", f"Welcome, {user.title()}.\nNeural link synchronized.", "success")
        else:
            self.status.setText("● AUTHENTICATION FAILURE. ANOMALY DETECTED.")
            self.status.setObjectName("statusDenied")
            self.glitch_effect()
            self.show_message_box("Access Denied", "Cognitive signature mismatch.\nSecurity protocols engaged.", "failure")
            QTimer.singleShot(2500, self.reset_status)
        self.setStyleSheet(self.get_stylesheet())

    def glitch_effect(self):
        self.glitch_anim = QPropertyAnimation(self, b"pos")
        self.glitch_anim.setDuration(200)
        start_pos = self.pos()
        self.glitch_anim.setKeyValueAt(0, start_pos)
        self.glitch_anim.setKeyValueAt(0.1, start_pos + QPointF(5, 0))
        self.glitch_anim.setKeyValueAt(0.2, start_pos + QPointF(-5, 0))
        self.glitch_anim.setKeyValueAt(0.3, start_pos + QPointF(5, 0))
        self.glitch_anim.setKeyValueAt(0.4, start_pos)
        self.glitch_anim.start()

    def reset_status(self):
        self.status.setText("● SYSTEM STATUS: ONLINE")
        self.status.setObjectName("statusOnline")
        self.setStyleSheet(self.get_stylesheet())
        self.username.clear(); self.password.clear()

    def show_message_box(self, title, text, msg_type="success"):
        msg = QMessageBox(self); msg.setWindowTitle(title); msg.setText(text)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        border_color = "#00f7ff" if msg_type == "success" else "#ff2222"
        text_color = "#e0ffff" if msg_type == "success" else "#ffaaaa"
        msg.setStyleSheet(f"""
            QMessageBox {{ background-color: #0a0f19; font-family: 'Courier New', monospace; }}
            QMessageBox QLabel {{ color: {text_color}; font-size: 14px; }}
            QMessageBox QPushButton {{ background-color: {border_color}; color: #05080f; border-radius: 5px; padding: 8px 25px; font-weight: bold; font-family: 'Orbitron'; }}
        """)
        msg.exec()

    def mousePressEvent(self, event): self.oldPos = event.globalPos()
    def mouseMoveEvent(self, event):
        if hasattr(self, 'oldPos'):
            delta = event.globalPos() - self.oldPos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.oldPos = event.globalPos()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TIYALogin()
    screen_geometry = app.primaryScreen().geometry()
    x = (screen_geometry.width() - window.width()) // 2
    y = (screen_geometry.height() - window.height()) // 2
    window.move(x, y)
    window.show()
    sys.exit(app.exec())
