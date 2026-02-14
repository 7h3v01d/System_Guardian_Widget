# Guardian Dashboard & Mini-Widget

A modern, lightweight system monitoring utility built with Python and PySide6. It features a dual-interface design: a comprehensive Full Dashboard for logs and settings, and a sleek, Transparent Mini-Widget for real-time performance tracking and emergency process control.

## 🚀 Features

- Dual-State UI: Seamlessly switch between a detailed dashboard and a space-saving desktop tile.
- Transparent "Floating" Widget: Modern frameless design with rounded corners and soft drop shadows that blend perfectly with any desktop background.
- Guardian Engine: Active monitoring of CPU and GPU loads using psutil and GPUtil.
- Dynamic Throttling: Automatically adjusts process priorities (specifically for Vivaldi) based on system load to prevent hardware thermal-bottlenecking.
- One-Click Panic: Instantly suspend or resume target processes directly from the mini-widget.
- Persistent Settings: Automatically saves widget position and user preferences to local storage.

## 🛠️ Installation

1. Clone the repository:
```Bash
git clone https://github.com/your-username/guardian-dashboard.git
cd guardian-dashboard
```
2. Install dependencies:<br>
This project requires Python 3.8+ and the following libraries:
```Bash
pip install PySide6 psutil gputil
```
3. Run the application:
```Bash
python main.py
```

## 🖥️ Usage

- Widget Mode: Click and drag anywhere on the mini-widget to move it. It will remember its position on the next launch.
- Panic Button: The large button on the widget toggles between active and suspended states for managed processes.
- Status Indicators:
    - Blue: Healthy / Normal Operation
    - Orange: System Throttled (Automatic Priority Reduction)
    - Red: Panic Mode / Processes Suspended
- System Tray: Use the tray icon to toggle visibility or exit the application completely.

## 📁 Project Structure
`.py`: The main entry point containing the UI logic, Guardian Engine, and Controller.

`settings.json`: (Generated) Stores persistent window coordinates and user configurations.
