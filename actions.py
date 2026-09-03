"""Windows system actions dispatched by recognized hand gestures."""

from __future__ import annotations

import ctypes
import datetime
import os
import subprocess
import pyautogui


def take_screenshot(folder: str) -> str:
    """Capture full screen and save to a timestamped PNG file."""
    try:
        os.makedirs(folder, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(folder, f"screenshot_{timestamp}.png")
        pyautogui.screenshot(path)
        return "Screenshot saved!"
    except Exception as exc:
        return f"Screenshot failed: {exc}"


def show_desktop() -> str:
    """Toggle showing the desktop (Win + D)."""
    try:
        pyautogui.hotkey("win", "d")
        return "Desktop toggled (Win+D)!"
    except Exception as exc:
        return f"Desktop toggle failed: {exc}"


def toggle_mute() -> str:
    """Toggle Windows master audio mute via pycaw."""
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

        speakers = AudioUtilities.GetSpeakers()
        if hasattr(speakers, "EndpointVolume") and speakers.EndpointVolume is not None:
            volume = speakers.EndpointVolume
        elif hasattr(speakers, "_dev"):
            interface = speakers._dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
        elif hasattr(speakers, "Activate"):
            interface = speakers.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
        else:
            raise RuntimeError("AudioEndpointVolume interface could not be resolved.")

        currently_muted = volume.GetMute()
        volume.SetMute(0 if currently_muted else 1, None)
        return "Unmuted!" if currently_muted else "Muted!"
    except Exception as exc:
        return f"Mute failed: {exc}"


def open_browser() -> str:
    """Launch Google Chrome or fall back to the default web browser."""
    candidate_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Google\Chrome\Application\chrome.exe"),
    ]

    for path in candidate_paths:
        if os.path.exists(path):
            try:
                subprocess.Popen([path])
                return "Google Chrome opened!"
            except Exception as exc:
                return f"Chrome launch error: {exc}"

    try:
        os.startfile("https://www.google.com")
        return "Web Browser opened (Chrome exe not found)!"
    except Exception as exc:
        return f"Browser launch failed: {exc}"


def media_play_pause() -> str:
    """Send system play/pause media key."""
    try:
        pyautogui.press("playpause")
        return "Play/Pause toggled!"
    except Exception as exc:
        return f"Media control failed: {exc}"


def open_calculator() -> str:
    """Launch Windows Calculator."""
    try:
        subprocess.Popen("calc.exe")
        return "Calculator opened!"
    except Exception as exc:
        return f"Calculator failed: {exc}"


def open_notepad() -> str:
    """Launch Windows Notepad."""
    try:
        subprocess.Popen("notepad.exe")
        return "Notepad opened!"
    except Exception as exc:
        return f"Notepad failed: {exc}"


def open_file_explorer() -> str:
    """Launch Windows File Explorer."""
    try:
        subprocess.Popen("explorer.exe")
        return "File Explorer opened!"
    except Exception as exc:
        return f"Explorer failed: {exc}"


def open_task_manager() -> str:
    """Launch Task Manager elevated via ShellExecuteW to avoid UAC error 740."""
    try:
        res = ctypes.windll.shell32.ShellExecuteW(None, "runas", "taskmgr.exe", None, None, 1)
        if res > 32:
            return "Task Manager opened (Elevated)!"
        else:
            return f"Task Manager launch returned code {res}"
    except Exception as exc:
        return f"Task Manager failed: {exc}"


def volume_up() -> str:
    """Increase master audio volume."""
    try:
        pyautogui.press("volumeup", presses=5)
        return "Volume Up (+10%)!"
    except Exception as exc:
        return f"Volume Up failed: {exc}"


def volume_down() -> str:
    """Decrease master audio volume."""
    try:
        pyautogui.press("volumedown", presses=5)
        return "Volume Down (-10%)!"
    except Exception as exc:
        return f"Volume Down failed: {exc}"


def open_settings() -> str:
    """Open Windows Settings."""
    try:
        subprocess.Popen("cmd /c start ms-settings:", shell=True)
        return "Settings opened!"
    except Exception as exc:
        return f"Settings failed: {exc}"


def lock_workstation() -> str:
    """Lock the Windows workstation screen."""
    try:
        ctypes.windll.user32.LockWorkStation()
        return "Screen Locked (Double Fist)!"
    except Exception as exc:
        return f"Lock screen failed: {exc}"


def switch_window() -> str:
    """Trigger Alt + Tab window switcher."""
    try:
        pyautogui.hotkey("alt", "tab")
        return "Switched Window (Alt+Tab)!"
    except Exception as exc:
        return f"Switch window failed: {exc}"


def open_claude_app() -> str:
    """Launch Claude Desktop App or fall back to web portal."""
    try:
        desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        claude_shortcut = os.path.join(desktop_dir, "Claude.lnk")

        if os.path.exists(claude_shortcut):
            os.startfile(claude_shortcut)
            return "Claude Desktop launched (Double Palm)!"

        local_app_data = os.environ.get("LOCALAPPDATA", "")
        fallback_exe = os.path.join(local_app_data, "Programs", "Claude", "Claude.exe")
        if os.path.exists(fallback_exe):
            os.startfile(fallback_exe)
            return "Claude Desktop launched (Double Palm)!"

        os.startfile("https://claude.ai")
        return "Claude Web opened (Double Palm)!"
    except Exception as exc:
        return f"Claude launch failed: {exc}"


def open_this_pc() -> str:
    """Open 'This PC' in Windows File Explorer."""
    try:
        subprocess.Popen("explorer.exe shell:MyComputerFolder")
        return "This PC opened (Triangle)!"
    except Exception as exc:
        return f"This PC failed: {exc}"

