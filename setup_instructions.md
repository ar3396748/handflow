# Gesture Control — Project & Setup Guide

A real-time 16-gesture recognition desktop application for Windows featuring 13 single-hand gestures and 3 two-hand gestures built with MediaPipe Hands, OpenCV, and pycaw.

---

## 1. Quick Start

### Step 1: Open Terminal & Navigate
```cmd
cd /d C:\Users\EliteBook\Desktop\HandFlow\handgesture
```

### Step 2: Activate Virtual Environment
**CMD:**
```cmd
venv\Scripts\activate.bat
```
**PowerShell:**
```powershell
.\venv\Scripts\Activate.ps1
```

### Step 3: Run the Application
```cmd
python main.py
```
*(Press **`q`** in the camera window to exit)*

---

## 2. System Architecture

- **Immediate Startup**: The application starts immediately armed and ready to dispatch actions upon gesture recognition.
- **Edge-Triggered Dispatch**: A temporal consistency buffer (8 frames) ensures gestures are stable before triggering actions, avoiding spurious activations.
- **Cooldown & Reset**: After an action is dispatched, the system waits for cooldown and neutral hand frames before re-arming to prevent repeat activations.

---

## 3. 16-Gesture Reference Table

| # | Gesture Name | Key | Type | Triggered Windows Action |
|:---:|:---|:---|:---:|:---|
| **1** | 👍 **Thumbs Up** | `thumbs_up` | 1-Hand | Screenshot (`screenshots/`) |
| **2** | 👎 **Thumbs Down** | `thumbs_down` | 1-Hand | Show Desktop (`Win + D`) |
| **3** | ✊ **Fist** | `fist` | 1-Hand | Toggle Mute / Unmute (`pycaw`) |
| **4** | ✋ **Open Palm** | `open_palm` | 1-Hand | Launch Google Chrome (`chrome.exe`) |
| **5** | ☝️ **Index Point** | `index_point` | 1-Hand | Media Play / Pause |
| **6** | ✌️ **Two Fingers / Peace** | `two_fingers` | 1-Hand | Open Calculator (`calc.exe`) |
| **7** | 🤟 **Three Fingers** | `three_fingers` | 1-Hand | Open Notepad (`notepad.exe`) |
| **8** | 🖖 **Four Fingers** | `four_fingers` | 1-Hand | Open File Explorer (`explorer.exe`) |
| **9** | 🤘 **Rock Sign / Horns** | `rock_sign` | 1-Hand | Open Task Manager (Elevated UAC) |
| **10** | 🤞 **Crossed Fingers** | `crossed_fingers` | 1-Hand | Volume Up (+10%) |
| **11** | 🔫 **L-Sign / Gun Shape** | `l_sign` | 1-Hand | Volume Down (-10%) |
| **12** | 👌 **OK Sign** | `ok_sign` | 1-Hand | Open Windows Settings (`ms-settings:`) |
| **13** | 🥊 **Double Fists Together** | `double_fist` | 2-Hands | Lock Workstation Screen |
| **14** | 🤚 **Back of Hand** | `back_of_hand` | 1-Hand | Switch Window (`Alt + Tab`) |
| **15** | 👐 **Double Open Palms** | `double_open_palm` | 2-Hands | Launch Claude Desktop App |
| **16** | 🔺 **Triangle** | `triangle` | 2-Hands | Open "This PC" (`shell:MyComputerFolder`) |

---

## 4. Author

- **Name:** Abdullah Abrar
- **GitHub:** [ar3396748](https://github.com/ar3396748)
- **Email:** [ar3396748@gmail.com](mailto:ar3396748@gmail.com)

