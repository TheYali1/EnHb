import time
import keyboard
import clipboard
import pyautogui

eng_to_heb = {
    'q': '/', 'w': "'", 'e': 'ק', 'r': 'ר', 't': 'א', 'y': 'ט', 'u': 'ו', 'i': 'ן', 'o': 'ם', 'p': 'פ',
    'a': 'ש', 's': 'ד', 'd': 'ג', 'f': 'כ', 'g': 'ע', 'h': 'י', 'j': 'ח', 'k': 'ל', 'l': 'ך', ';': 'ף',
    "'": ',', 'z': 'ז', 'x': 'ס', 'c': 'ב', 'v': 'ה', 'b': 'נ', 'n': 'מ', 'm': 'צ', ',': 'ת', '.': 'ץ',
    '/': '.'
}

heb_to_eng = {v: k for k, v in eng_to_heb.items()}

def get_selected_text():
    saved_clipboard = clipboard.paste()
    clipboard.copy('')
    pyautogui.hotkey('ctrl', 'a')
    pyautogui.hotkey('ctrl', 'c')
    time.sleep(0.1)
    text = clipboard.paste()
    if not text:
        clipboard.copy(saved_clipboard)
        return None
    return text, saved_clipboard

def convert_to_heb():
    res = get_selected_text()
    if not res:
        return
    text, saved_clipboard = res
    
    converted = "".join(eng_to_heb.get(char.lower(), char) for char in text)
    
    clipboard.copy(converted)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.05)
    clipboard.copy(saved_clipboard)

def convert_to_eng():
    res = get_selected_text()
    if not res:
        return
    text, saved_clipboard = res
    
    converted = "".join(heb_to_eng.get(char, char) for char in text)
    
    clipboard.copy(converted)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.05)
    clipboard.copy(saved_clipboard)

keyboard.add_hotkey('ctrl+shift+h', convert_to_heb)
keyboard.add_hotkey('ctrl+shift+e', convert_to_eng)

keyboard.wait()