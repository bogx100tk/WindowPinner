import keyboard
import win32gui
import win32con
import tkinter as tk
from tkinter import messagebox
import threading
from pystray import MenuItem as item, Icon as icon
from PIL import Image, ImageDraw
import os
from pynput import mouse
from pynput import keyboard as pynput_keyboard

current_hotkey = "ctrl+alt+t"
settings_window = None
root = None
notification_window = None

def show_notification(message, x, y):
    global notification_window

    if notification_window and notification_window.winfo_exists():
        notification_window.destroy()

    notification_window = tk.Toplevel(root)
    notification_window.overrideredirect(True)
    notification_window.attributes('-alpha', 0.8)
    notification_window.attributes('-topmost', True)

    label = tk.Label(notification_window, text=message, bg="black", fg="white",
                     padx=10, pady=5, font=("Arial", 10, "bold"))
    label.pack()

    notification_window.geometry(f"+{x+20}+{y+20}")
    notification_window.after(1500, notification_window.destroy)

def toggle_always_on_top(x=None, y=None):
    try:
        hwnd = win32gui.GetForegroundWindow()
        if hwnd:
            if x is None or y is None:
                pos = win32gui.GetCursorPos()
                x, y = pos

            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            is_topmost = ex_style & win32con.WS_EX_TOPMOST

            if is_topmost:
                win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0,
                                      win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
                print("🔽 Окно откреплено")
                show_notification("Окно не зафиксировано", x, y)
            else:
                win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                                      win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
                print("📌 Окно зафиксировано")
                show_notification("Окно зафиксировано по верх", x, y)
    except Exception as e:
        print(f"Ошибка при переключении окна: {e}")

def setup_mouse_listener():
    currently_pressed = set()

    keys_to_track = {
        pynput_keyboard.Key.ctrl_l, pynput_keyboard.Key.ctrl_r,
        pynput_keyboard.Key.alt_l, pynput_keyboard.Key.alt_r
    }

    def on_press(key):
        if key in keys_to_track:
            currently_pressed.add(key)

    def on_release(key):
        currently_pressed.discard(key)

    key_listener = pynput_keyboard.Listener(on_press=on_press, on_release=on_release)
    key_listener.start()

    def on_click(x, y, button, pressed):
        if button == mouse.Button.left and pressed:
            ctrl_is_pressed = any(k in currently_pressed for k in {pynput_keyboard.Key.ctrl_l, pynput_keyboard.Key.ctrl_r})
            alt_is_pressed = any(k in currently_pressed for k in {pynput_keyboard.Key.alt_l, pynput_keyboard.Key.alt_r})

            if ctrl_is_pressed and alt_is_pressed:
                print("Обнаружен клик Ctrl+Alt+ЛКМ")
                toggle_always_on_top(x, y)

    mouse_listener = mouse.Listener(on_click=on_click)
    threading.Thread(target=mouse_listener.start, daemon=True).start()
    print("Слушатель мыши запущен (Ctrl+Alt+ЛКМ).")

def show_settings_window():
    global settings_window

    if settings_window and settings_window.winfo_exists():
        settings_window.lift()
        settings_window.focus_force()
        return

    settings_window = tk.Toplevel(root)
    settings_window.title("Настройка горячей клавиши")
    settings_window.geometry("450x180")
    settings_window.attributes('-topmost', True)

    settings_window.update_idletasks()
    width = settings_window.winfo_width()
    height = settings_window.winfo_height()
    x = (settings_window.winfo_screenwidth() // 2) - (width // 2)
    y = (settings_window.winfo_screenheight() // 2) - (height // 2)
    settings_window.geometry(f'{width}x{height}+{x}+{y}')

    def record_and_apply():
        nonlocal set_button, status_label
        status_label.config(text="Нажмите желаемую комбинацию...")
        set_button.config(state=tk.DISABLED, text="Идет запись...")
        threading.Thread(target=read_hotkey_thread, args=(status_label, set_button), daemon=True).start()

    def read_hotkey_thread(s_label, s_button):
        global current_hotkey
        try:
            new_hotkey = keyboard.read_hotkey(suppress=False)
            keyboard.remove_hotkey(current_hotkey)
            keyboard.add_hotkey(new_hotkey, toggle_always_on_top)
            current_hotkey = new_hotkey
            settings_window.after(0, lambda: s_label.config(text=f"Новая клавиша: {current_hotkey}", fg="green"))
            print(f"Новая горячая клавиша '{current_hotkey}' установлена.")
        except Exception as e:
            keyboard.add_hotkey(current_hotkey, toggle_always_on_top)
            settings_window.after(0, lambda: s_label.config(text=f"Ошибка! Текущая: {current_hotkey}", fg="red"))
            print(f"Ошибка при установке новой горячей клавиши: {e}")
        finally:
            settings_window.after(0, lambda: s_button.config(state=tk.NORMAL, text="Задать новую горячую клавишу"))

    info_label = tk.Label(settings_window, text="Нажмите кнопку и затем нажмите комбинацию клавиш,\nкоторую хотите использовать.", pady=10)
    info_label.pack(pady=(5, 0))
    status_label = tk.Label(settings_window, text=f"Текущая клавиша: {current_hotkey}", font=("Arial", 10, "bold"), fg="blue")
    status_label.pack(pady=10)
    set_button = tk.Button(settings_window, text="Задать новую горячую клавишу", command=record_and_apply, width=30)
    set_button.pack(pady=10)

def create_tray_image():
    width, height = 64, 64
    image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    dc = ImageDraw.Draw(image)
    dc.rectangle((28, 5, 36, 15), fill='gray')
    dc.line((32, 15, 32, 55), fill='white', width=4)
    dc.polygon([(32, 60), (28, 55), (36, 55)], fill='white')
    return image

def on_exit_clicked(icon, item):
    print("Программа завершена.")
    icon.stop()
    if root:
        root.quit()
    os._exit(0)

def setup_and_run_tray():
    tray_menu = (
        item('Настроить горячую клавишу', show_settings_window),
        item('Выход', on_exit_clicked)
    )
    image = create_tray_image()
    icon("WindowPinner", image, "Закрепитель окон", tray_menu).run()

if __name__ == "__main__":
    try:
        keyboard.add_hotkey(current_hotkey, toggle_always_on_top)
        print(f"Программа запущена. Горячая клавиша по умолчанию: '{current_hotkey}'")

        setup_mouse_listener()

        root = tk.Tk()
        root.withdraw()

        tray_thread = threading.Thread(target=setup_and_run_tray, daemon=True)
        tray_thread.start()

        root.mainloop()

    except Exception as e:
        print(f"Произошла критическая ошибка: {e}")
        messagebox.showerror("Критическая ошибка", str(e))```