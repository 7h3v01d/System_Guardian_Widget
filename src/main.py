import sys
import json
import psutil
import GPUtil
import threading
import time
from pathlib import Path
from dataclasses import dataclass, asdict

try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:
    print("Dependencies missing: pip install PySide6 psutil gputil")
    sys.exit(1)

# ──────────────────────────────────────────────────────────────
# 1. MODERN STYLING (Unchanged)
# ──────────────────────────────────────────────────────────────
STYLE_SHEET = """
    QMainWindow { background: #f6f7fb; }
    QTabWidget::pane { border: 1px solid #d9dbe2; border-radius: 10px; background: white; }
    QTabBar::tab { 
        padding: 8px 14px; border: 1px solid #d9dbe2; border-bottom: none; 
        border-top-left-radius: 10px; border-top-right-radius: 10px; 
        background: #eef0f7; margin-right: 4px; color: #111827;
    }
    QTabBar::tab:selected { background: white; font-weight: bold; }
    QPushButton { 
        padding: 8px 15px; border-radius: 10px; background: white; 
        border: 1px solid #d0d3dd; color: #111827; font-weight: 500;
    }
    QPushButton:hover { background: #f2f3f8; }
    QPlainTextEdit { border: 1px solid #d9dbe2; border-radius: 8px; font-family: 'Consolas'; font-size: 12px; }
"""

# ──────────────────────────────────────────────────────────────
# 2. THE ENGINE (Unchanged)
# ──────────────────────────────────────────────────────────────
class GuardianEngine(QtCore.QObject):
    stats_updated = QtCore.Signal(dict)

    def __init__(self, threshold=90.0, recovery=75.0):
        super().__init__()
        self.threshold = threshold
        self.recovery = recovery
        self.throttled = False
        self.suspended = False
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _get_vivaldi_procs(self):
        procs = []
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if 'vivaldi' in proc.info['name'].lower():
                    procs.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied): continue
        return procs

    def toggle_panic(self):
        self.suspended = not self.suspended
        for p in self._get_vivaldi_procs():
            try:
                p.resume() if not self.suspended else p.suspend()
            except: pass
        return self.suspended

    def _run(self):
        while self.running:
            cpu = psutil.cpu_percent(interval=0.8)
            gpus = GPUtil.getGPUs()
            gpu = gpus[0].load * 100 if gpus else 0
            
            if (cpu > self.threshold or gpu > self.threshold) and not self.throttled:
                self._set_priority(psutil.IDLE_PRIORITY_CLASS)
                self.throttled = True
            elif cpu < self.recovery and self.throttled:
                self._set_priority(psutil.NORMAL_PRIORITY_CLASS)
                self.throttled = False

            self.stats_updated.emit({"cpu": cpu, "gpu": gpu, "throttled": self.throttled, "suspended": self.suspended})
            time.sleep(0.2)

    def _set_priority(self, level):
        for p in self._get_vivaldi_procs():
            try: p.nice(level)
            except: pass

# ──────────────────────────────────────────────────────────────
# 3. UI CLASSES (Surgical fix for transparent corners)
# ──────────────────────────────────────────────────────────────
@dataclass
class AppSettings:
    start_in_widget_mode: bool = True
    widget_x: int = 100
    widget_y: int = 100

    @classmethod
    def load(cls):
        return cls()

class ModernTile(QtWidgets.QWidget):
    showFullRequested = QtCore.Signal()
    panicRequested = QtCore.Signal()

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        
        # TRANSITION TO TRANSPARENT:
        self.setWindowFlags(QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground) # The core fix
        
        # We need a small buffer for the shadow to render without clipping
        self.setFixedSize(320, 95) 

        # This container holds your actual UI and the rounded look
        self.container = QtWidgets.QFrame(self)
        self.container.setGeometry(5, 5, 310, 80)
        self.container.setObjectName("VTWidget")
        self.container.setStyleSheet("""
            QFrame#VTWidget { 
                background: white; 
                border-radius: 15px; 
                border: 2px solid #4c9aff; 
            }
        """)

        # All your original elements now live inside this container
        layout = QtWidgets.QHBoxLayout(self.container)

        self.btn_panic = QtWidgets.QPushButton("PANIC")
        self.btn_panic.setFixedSize(60, 60)
        self.btn_panic.clicked.connect(self.panicRequested.emit)
        layout.addWidget(self.btn_panic)

        v_box = QtWidgets.QVBoxLayout()
        self.lbl_cpu = QtWidgets.QLabel("CPU: 0% | GPU: 0%")
        self.lbl_status = QtWidgets.QLabel("Status: Healthy")
        v_box.addWidget(self.lbl_cpu)
        v_box.addWidget(self.lbl_status)
        layout.addLayout(v_box)

        self.btn_set = QtWidgets.QPushButton("⚙")
        self.btn_set.setFixedSize(35, 35)
        self.btn_set.clicked.connect(self.showFullRequested.emit)
        layout.addWidget(self.btn_set)

        # Shadow (Optional but recommended to hide edges)
        shadow = QtWidgets.QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(10); shadow.setOffset(0, 2); shadow.setColor(QtGui.QColor(0, 0, 0, 80))
        self.container.setGraphicsEffect(shadow)

        self._drag_pos = None

    def mousePressEvent(self, e):
        self._drag_pos = e.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, e):
        if self._drag_pos:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def update_display(self, data):
        self.lbl_cpu.setText(f"CPU: {data['cpu']}% | GPU: {data['gpu']}%")
        color = "#ef4444" if data['suspended'] else ("#f59e0b" if data['throttled'] else "#4c9aff")
        self.btn_panic.setStyleSheet(f"background: {color}; color: white; border-radius: 10px; font-weight: bold;")
        self.lbl_status.setText("🧊 FROZEN" if data['suspended'] else ("⚠️ THROTTLED" if data['throttled'] else "Healthy"))

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setWindowTitle("Guardian Dashboard")
        self.resize(500, 350)
        self.setStyleSheet(STYLE_SHEET)
        
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)
        
        self.log_view = QtWidgets.QPlainTextEdit()
        layout.addWidget(QtWidgets.QLabel("Activity Log:"))
        layout.addWidget(self.log_view)
        
        btn_widget = QtWidgets.QPushButton("Back to Widget")
        btn_widget.clicked.connect(self.controller.show_widget)
        layout.addWidget(btn_widget)

    def add_log(self, msg):
        self.log_view.appendPlainText(f"[{time.strftime('%H:%M:%S')}] {msg}")

# ──────────────────────────────────────────────────────────────
# 4. CONTROLLER (Unchanged)
# ──────────────────────────────────────────────────────────────
class AppController(QtCore.QObject):
    def __init__(self):
        super().__init__()
        self.settings = AppSettings.load()
        self.engine = GuardianEngine()
        self.tile_win = ModernTile(self.settings)
        self.main_win = MainWindow(self)
        
        self.engine.stats_updated.connect(self.tile_win.update_display)
        self.engine.stats_updated.connect(self._log_changes)
        self.tile_win.panicRequested.connect(self.engine.toggle_panic)
        self.tile_win.showFullRequested.connect(self.show_full)
        
        self._last_state = False
        self.tile_win.show()

    def _log_changes(self, data):
        if data['throttled'] != self._last_state:
            self.main_win.add_log("System Throttled" if data['throttled'] else "System Restored")
            self._last_state = data['throttled']

    def show_full(self):
        self.tile_win.hide()
        self.main_win.show()

    def show_widget(self):
        self.main_win.hide()
        self.tile_win.show()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    ctrl = AppController()
    sys.exit(app.exec())