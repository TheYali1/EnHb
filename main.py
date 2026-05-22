import json
import os
import queue
import sys
import threading
import time
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

import keyboard
import clipboard
import pyautogui
import pystray
from PIL import Image


APP_NAME = "Enhb"
ICON_FILE = "a.ico"
DEFAULT_LANGUAGE = "en"
SINGLE_INSTANCE_MUTEX = "Local\\EnhbSingleInstanceMutex"
DEFAULT_HOTKEYS = {
    "to_heb": "ctrl+shift+h",
    "to_eng": "ctrl+shift+e",
}

TEXT = {
    "en": {
        "window_title": "Enhb Shortcuts",
        "to_heb_menu": "To Hebrew: {hotkey}",
        "to_eng_menu": "To English: {hotkey}",
        "to_heb_label": "Convert English to Hebrew",
        "to_eng_label": "Convert Hebrew to English",
        "language": "Language",
        "english": "English",
        "hebrew": "Hebrew",
        "change_shortcuts": "Change shortcuts...",
        "close": "Close",
        "record": "Change",
        "save": "Save",
        "cancel": "Cancel",
        "ready": "Press Change or type a shortcut.",
        "press_shortcut": "Press the new shortcut now...",
        "recorded": "Changed: {hotkey}",
        "saved": "Saved.",
        "could_not_record": "Could not change shortcut:\n{message}",
        "could_not_save": "Could not save settings:\n{message}",
        "shortcut_empty": "{label} is empty.",
        "shortcuts_same": "The two shortcuts must be different.",
        "hebrew_shortcut": "Hebrew shortcut",
        "english_shortcut": "English shortcut",
    },
    "he": {
        "window_title": "קיצורי הדרך של Enhb",
        "to_heb_menu": "לעברית: {hotkey}",
        "to_eng_menu": "לאנגלית: {hotkey}",
        "to_heb_label": "המרה מאנגלית לעברית",
        "to_eng_label": "המרה מעברית לאנגלית",
        "language": "שפה",
        "english": "אנגלית",
        "hebrew": "עברית",
        "change_shortcuts": "שינוי קיצורי דרך...",
        "close": "סגור",
        "record": "שנה",
        "save": "שמור",
        "cancel": "ביטול",
        "ready": "אפשר ללחוץ על כפתור ה\"שנה\" בשביל לשנות את הקיצור דרך",
        "press_shortcut": "לחץ עכשיו על הקיצור דרך החדש...",
        "recorded": "שונה: {hotkey}",
        "saved": "נשמר.",
        "could_not_record": "לא הצלחתי לשנות קיצור:\n{message}",
        "could_not_save": "לא הצלחתי לשמור הגדרות:\n{message}",
        "shortcut_empty": "{label} ריק.",
        "shortcuts_same": "שני הקיצורי דרך חייבים להיות שונים.",
        "hebrew_shortcut": "קיצור לעברית",
        "english_shortcut": "קיצור לאנגלית",
    },
}


eng_to_heb = {
    'q': '/', 'w': "'", 'e': 'ק', 'r': 'ר', 't': 'א', 'y': 'ט', 'u': 'ו', 'i': 'ן', 'o': 'ם', 'p': 'פ',
    'a': 'ש', 's': 'ד', 'd': 'ג', 'f': 'כ', 'g': 'ע', 'h': 'י', 'j': 'ח', 'k': 'ל', 'l': 'ך', ';': 'ף',
    "'": ',', 'z': 'ז', 'x': 'ס', 'c': 'ב', 'v': 'ה', 'b': 'נ', 'n': 'מ', 'm': 'צ', ',': 'ת', '.': 'ץ',
    '/': '.'
}

heb_to_eng = {v: k for k, v in eng_to_heb.items()}

hotkeys = DEFAULT_HOTKEYS.copy()
language = DEFAULT_LANGUAGE
hotkey_handles = []
hotkey_lock = threading.RLock()
conversion_lock = threading.Lock()
ui_queue = queue.Queue()
root = None
settings_window = None
tray_icon = None
instance_mutex = None


def text(key, **values):
    template = TEXT.get(language, TEXT[DEFAULT_LANGUAGE]).get(key, TEXT[DEFAULT_LANGUAGE][key])
    return template.format(**values)


def resource_path(filename):
    if getattr(sys, "frozen", False):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).resolve().parent
    return base_path / filename


def config_path():
    appdata = os.environ.get("APPDATA")
    if appdata:
        base_path = Path(appdata)
    else:
        base_path = Path.home() / "AppData" / "Roaming"
    return base_path / APP_NAME / "settings.json"


def ensure_single_instance():
    global instance_mutex
    if os.name != "nt":
        return

    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.windll.kernel32
        kernel32.CreateMutexW.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.GetLastError.restype = wintypes.DWORD
        instance_mutex = kernel32.CreateMutexW(None, False, SINGLE_INSTANCE_MUTEX)
        if instance_mutex and kernel32.GetLastError() == 183:
            sys.exit(0)
    except Exception:
        pass


def normalize_hotkey_text(value):
    return " ".join(str(value).strip().lower().split())


def compact_recorded_hotkey(value):
    hotkey = normalize_hotkey_text(value)
    replacements = {
        "left ctrl": "ctrl",
        "right ctrl": "ctrl",
        "left shift": "shift",
        "right shift": "shift",
        "left alt": "alt",
        "right alt": "alt",
        "left windows": "windows",
        "right windows": "windows",
    }
    for old, new in replacements.items():
        hotkey = hotkey.replace(old, new)
    parts = []
    for part in hotkey.split("+"):
        part = part.strip()
        if part and part not in parts:
            parts.append(part)
    return "+".join(parts)


def validate_hotkey(value, label):
    hotkey = compact_recorded_hotkey(value)
    if not hotkey:
        raise ValueError(text("shortcut_empty", label=label))
    keyboard.parse_hotkey(hotkey)
    return hotkey


def load_settings():
    path = config_path()
    loaded_hotkeys = DEFAULT_HOTKEYS.copy()
    loaded_language = DEFAULT_LANGUAGE

    try:
        if path.exists():
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
            if isinstance(data, dict):
                loaded_hotkeys.update({
                    "to_heb": data.get("to_heb", loaded_hotkeys["to_heb"]),
                    "to_eng": data.get("to_eng", loaded_hotkeys["to_eng"]),
                })
                if data.get("language") in TEXT:
                    loaded_language = data["language"]
    except (OSError, json.JSONDecodeError):
        return DEFAULT_HOTKEYS.copy(), DEFAULT_LANGUAGE

    try:
        loaded_hotkeys["to_heb"] = validate_hotkey(loaded_hotkeys["to_heb"], "Hebrew shortcut")
        loaded_hotkeys["to_eng"] = validate_hotkey(loaded_hotkeys["to_eng"], "English shortcut")
        if loaded_hotkeys["to_heb"] == loaded_hotkeys["to_eng"]:
            loaded_hotkeys = DEFAULT_HOTKEYS.copy()
    except ValueError:
        loaded_hotkeys = DEFAULT_HOTKEYS.copy()

    return loaded_hotkeys, loaded_language


def save_settings():
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "to_heb": hotkeys["to_heb"],
        "to_eng": hotkeys["to_eng"],
        "language": language,
    }
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def unregister_hotkeys():
    global hotkey_handles
    for handle in hotkey_handles:
        try:
            keyboard.remove_hotkey(handle)
        except (KeyError, ValueError):
            pass
    hotkey_handles = []


def add_app_hotkey(hotkey, callback):
    return keyboard.add_hotkey(hotkey, callback)


def register_hotkeys(new_hotkeys):
    global hotkeys, hotkey_handles
    with hotkey_lock:
        previous_hotkeys = hotkeys.copy()
        previous_handles = hotkey_handles[:]
        hotkey_handles = []

        for handle in previous_handles:
            try:
                keyboard.remove_hotkey(handle)
            except (KeyError, ValueError):
                pass

        new_handles = []
        try:
            new_handles.append(add_app_hotkey(new_hotkeys["to_heb"], convert_to_heb))
            new_handles.append(add_app_hotkey(new_hotkeys["to_eng"], convert_to_eng))
        except Exception:
            for handle in new_handles:
                try:
                    keyboard.remove_hotkey(handle)
                except (KeyError, ValueError):
                    pass
            hotkeys = previous_hotkeys
            hotkey_handles = [
                add_app_hotkey(previous_hotkeys["to_heb"], convert_to_heb),
                add_app_hotkey(previous_hotkeys["to_eng"], convert_to_eng),
            ]
            raise

        hotkeys = new_hotkeys.copy()
        hotkey_handles = new_handles
        if tray_icon:
            tray_icon.update_menu()


def get_selected_text():
    saved_clipboard = clipboard.paste()
    clipboard.copy("")
    pyautogui.hotkey("ctrl", "a")
    pyautogui.hotkey("ctrl", "c")
    time.sleep(0.1)
    text_value = clipboard.paste()
    if not text_value:
        clipboard.copy(saved_clipboard)
        return None
    return text_value, saved_clipboard


def replace_text(text_value, saved_clipboard):
    clipboard.copy(text_value)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.05)
    clipboard.copy(saved_clipboard)


def convert_to_heb():
    with conversion_lock:
        result = get_selected_text()
        if not result:
            return
        text_value, saved_clipboard = result
        converted = "".join(eng_to_heb.get(char.lower(), char) for char in text_value)
        replace_text(converted, saved_clipboard)


def convert_to_eng():
    with conversion_lock:
        result = get_selected_text()
        if not result:
            return
        text_value, saved_clipboard = result
        converted = "".join(heb_to_eng.get(char, char) for char in text_value)
        replace_text(converted, saved_clipboard)


def load_tray_image():
    icon_path = resource_path(ICON_FILE)
    if icon_path.exists():
        return Image.open(icon_path).convert("RGBA")
    return Image.new("RGBA", (64, 64), "white")


def post_to_ui(callback):
    ui_queue.put(callback)


def process_ui_queue():
    try:
        while True:
            try:
                callback = ui_queue.get_nowait()
            except queue.Empty:
                break
            try:
                callback()
            except Exception:
                pass
    finally:
        root.after(100, process_ui_queue)


def window_exists(window):
    if window is None:
        return False
    try:
        return bool(window.winfo_exists())
    except tk.TclError:
        return False


def close_settings_window():
    global settings_window
    window = settings_window
    settings_window = None
    if window_exists(window):
        window.destroy()


def bring_window_to_front(window):
    window.deiconify()
    window.lift()
    window.attributes("-topmost", True)
    window.after(150, lambda: window_exists(window) and window.attributes("-topmost", False))
    window.focus_force()


def set_language(new_language):
    global language
    if new_language not in TEXT:
        return
    language = new_language
    save_settings()
    if tray_icon:
        tray_icon.update_menu()


def show_settings_window():
    global settings_window, language
    if window_exists(settings_window):
        bring_window_to_front(settings_window)
        return
    settings_window = None

    settings_window = tk.Toplevel(root)
    settings_window.title(text("window_title"))
    settings_window.resizable(False, False)
    settings_window.configure(padx=18, pady=16)
    settings_window.protocol("WM_DELETE_WINDOW", close_settings_window)
    try:
        settings_window.iconbitmap(str(resource_path(ICON_FILE)))
    except tk.TclError:
        pass

    language_var = tk.StringVar(value=language)
    to_heb_var = tk.StringVar(value=hotkeys["to_heb"])
    to_eng_var = tk.StringVar(value=hotkeys["to_eng"])
    status_var = tk.StringVar(value=text("ready"))

    tk.Label(settings_window, text=text("language")).grid(row=0, column=0, sticky="w", pady=(0, 8))
    language_frame = tk.Frame(settings_window)
    language_frame.grid(row=0, column=1, columnspan=2, sticky="w", padx=(10, 0), pady=(0, 8))
    tk.Radiobutton(language_frame, text=text("english"), variable=language_var, value="en").pack(side="left")
    tk.Radiobutton(language_frame, text=text("hebrew"), variable=language_var, value="he").pack(side="left", padx=(12, 0))

    tk.Label(settings_window, text=text("to_heb_label")).grid(row=1, column=0, sticky="w", pady=(0, 6))
    to_heb_entry = tk.Entry(settings_window, width=28, textvariable=to_heb_var)
    to_heb_entry.grid(row=1, column=1, sticky="ew", padx=(10, 8), pady=(0, 6))

    tk.Label(settings_window, text=text("to_eng_label")).grid(row=2, column=0, sticky="w", pady=(0, 10))
    to_eng_entry = tk.Entry(settings_window, width=28, textvariable=to_eng_var)
    to_eng_entry.grid(row=2, column=1, sticky="ew", padx=(10, 8), pady=(0, 10))

    def capture_hotkey(target_var, button):
        button.configure(state="disabled")
        status_var.set(text("press_shortcut"))

        def worker():
            with hotkey_lock:
                unregister_hotkeys()
            try:
                recorded = keyboard.read_hotkey(suppress=False)
                recorded = compact_recorded_hotkey(recorded)
                post_to_ui(lambda: target_var.set(recorded))
                post_to_ui(lambda: status_var.set(text("recorded", hotkey=recorded)))
            except Exception as exc:
                message = str(exc)
                post_to_ui(lambda: messagebox.showerror(APP_NAME, text("could_not_record", message=message)))
            finally:
                with hotkey_lock:
                    register_hotkeys(hotkeys)
                post_to_ui(lambda: window_exists(settings_window) and button.configure(state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    heb_record_button = tk.Button(settings_window, text=text("record"), width=10)
    heb_record_button.configure(command=lambda: capture_hotkey(to_heb_var, heb_record_button))
    heb_record_button.grid(row=1, column=2, pady=(0, 6))

    eng_record_button = tk.Button(settings_window, text=text("record"), width=10)
    eng_record_button.configure(command=lambda: capture_hotkey(to_eng_var, eng_record_button))
    eng_record_button.grid(row=2, column=2, pady=(0, 10))

    tk.Label(settings_window, textvariable=status_var, fg="#555555").grid(
        row=3, column=0, columnspan=3, sticky="w", pady=(2, 12)
    )

    button_frame = tk.Frame(settings_window)
    button_frame.grid(row=4, column=0, columnspan=3, sticky="e")

    def save_changes():
        global language
        previous_language = language
        language = language_var.get()
        try:
            new_hotkeys = {
                "to_heb": validate_hotkey(to_heb_var.get(), text("hebrew_shortcut")),
                "to_eng": validate_hotkey(to_eng_var.get(), text("english_shortcut")),
            }
            if new_hotkeys["to_heb"] == new_hotkeys["to_eng"]:
                raise ValueError(text("shortcuts_same"))
            register_hotkeys(new_hotkeys)
            save_settings()
        except Exception as exc:
            language = previous_language
            messagebox.showerror(APP_NAME, text("could_not_save", message=str(exc)))
            return

        status_var.set(text("saved"))
        if tray_icon:
            tray_icon.update_menu()
        settings_window.after(250, close_settings_window)

    tk.Button(button_frame, text=text("cancel"), width=10, command=close_settings_window).pack(side="right")
    tk.Button(button_frame, text=text("save"), width=10, command=save_changes).pack(side="right", padx=(0, 8))

    settings_window.columnconfigure(1, weight=1)
    settings_window.bind("<Return>", lambda _event: save_changes())
    settings_window.bind("<Escape>", lambda _event: close_settings_window())
    bring_window_to_front(settings_window)
    to_heb_entry.focus_set()


def tray_menu():
    return pystray.Menu(
        pystray.MenuItem(lambda _item: text("to_heb_menu", hotkey=hotkeys["to_heb"]), None, enabled=False),
        pystray.MenuItem(lambda _item: text("to_eng_menu", hotkey=hotkeys["to_eng"]), None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(lambda _item: text("change_shortcuts"), lambda _icon, _item: post_to_ui(show_settings_window)),
        pystray.MenuItem(
            lambda _item: text("language"),
            pystray.Menu(
                pystray.MenuItem(lambda _item: text("english"), lambda _icon, _item: set_language("en"),
                                 checked=lambda _item: language == "en", radio=True),
                pystray.MenuItem(lambda _item: text("hebrew"), lambda _icon, _item: set_language("he"),
                                 checked=lambda _item: language == "he", radio=True),
            ),
        ),
        pystray.MenuItem(lambda _item: text("close"), lambda _icon, _item: post_to_ui(close_app)),
    )


def close_app():
    global instance_mutex
    close_settings_window()
    unregister_hotkeys()
    if tray_icon:
        tray_icon.stop()
    if os.name == "nt" and instance_mutex:
        try:
            import ctypes

            ctypes.windll.kernel32.CloseHandle(instance_mutex)
        except Exception:
            pass
        instance_mutex = None
    root.quit()


def keep_keyboard_listener_alive():
    try:
        keyboard.wait()
    except Exception:
        pass


def main():
    global hotkeys, language, root, tray_icon
    ensure_single_instance()
    hotkeys, language = load_settings()

    root = tk.Tk()
    root.withdraw()
    root.title(APP_NAME)
    try:
        root.iconbitmap(str(resource_path(ICON_FILE)))
    except tk.TclError:
        pass

    register_hotkeys(hotkeys)
    threading.Thread(target=keep_keyboard_listener_alive, daemon=True).start()
    tray_icon = pystray.Icon(APP_NAME, load_tray_image(), APP_NAME, tray_menu())
    threading.Thread(target=tray_icon.run, daemon=True).start()

    root.after(100, process_ui_queue)
    root.mainloop()


if __name__ == "__main__":
    main()
