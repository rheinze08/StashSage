import win32api
import win32con
import win32gui
import win32gui_struct
import os
import threading

TRAY_NOTIFY_ID = 1028
WM_NOTIFY_ICON = win32con.WM_USER + 20
CLASS_NAME = "StashSageTray"


class SystemTray:

    def _load_icon(self):
        icon_path = os.path.abspath(self.icon_path)
        if not os.path.exists(icon_path):
            raise FileNotFoundError(f"Icon file not found: {icon_path}")
        
        return win32gui.LoadImage(
            0,
            icon_path,
            win32con.IMAGE_ICON,
            0, 0,
            win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE
        )

    def __init__(self, icon_path: str, tk_root=None):
        self.hInstance = win32api.GetModuleHandle()
        self.class_name = CLASS_NAME
        self.icon_path = icon_path
        self.icon_handle = None
        self.tk_root = tk_root
        self.main_hwnd = None
        self.tray_hwnd = None

    def create_tray(self, hwnd):
        self.main_hwnd = hwnd
        self.icon_handle = self._load_icon()
        self._register_window_class()
        self._create_hidden_window()
        threading.Thread(target=self._tray_loop, daemon=True).start()


    def minimize(self, hwnd):
        self.main_hwnd = hwnd
        win32gui.ShowWindow(hwnd, win32con.SW_HIDE)

    def close(self):
        if self.tray_hwnd:
            try:
                self.tk_root.quit()
                self._remove_tray_icon(self.tray_hwnd)
                win32gui.DestroyWindow(self.tray_hwnd)
            except Exception as e:
                print("Error while closing tray icon:", e)
            self.tray_hwnd = None

    def _show_tray_icon(self, hwnd):
        nid = (
            hwnd,
            TRAY_NOTIFY_ID,
            win32gui.NIF_MESSAGE | win32gui.NIF_ICON | win32gui.NIF_TIP,
            WM_NOTIFY_ICON,
            self.icon_handle,
            "StashSage",
        )
        print(f"Adding tray icon with nid: {nid}")
        win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)

    def _remove_tray_icon(self, hwnd):
        nid = (
            hwnd,
            TRAY_NOTIFY_ID,
            win32gui.NIF_MESSAGE | win32gui.NIF_ICON | win32gui.NIF_TIP,
            WM_NOTIFY_ICON,
            self.icon_handle,
            "StashSage",
        )
        print(f"Removing tray icon with nid: {nid}")
        win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, nid)


    def _on_tray_notify(self, hwnd, msg, wparam, lparam):
        if lparam == win32con.WM_LBUTTONDBLCLK:
            win32gui.ShowWindow(self.main_hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(self.main_hwnd)
        elif lparam == win32con.WM_RBUTTONUP:
            self._show_context_menu(hwnd)
        return True

    def _show_context_menu(self, hwnd):
        menu = win32gui.CreatePopupMenu()

        win32gui.AppendMenu(menu, win32con.MF_STRING, 0, "Show")
        win32gui.AppendMenu(menu, win32con.MF_STRING, 1, "Hide")
        win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 2, "")
        win32gui.AppendMenu(menu, win32con.MF_STRING, 3, "Exit")

        pos = win32gui.GetCursorPos()
        win32gui.SetForegroundWindow(hwnd)
        win32gui.TrackPopupMenu(
            menu,
            win32con.TPM_LEFTALIGN,
            pos[0],
            pos[1],
            0,
            hwnd,
            None,
        )

    def _wndproc(self, hwnd, msg, wparam, lparam):
        if msg == WM_NOTIFY_ICON:
            return self._on_tray_notify(hwnd, msg, wparam, lparam)
        elif msg == win32con.WM_COMMAND:
            if wparam == 0:  # Show command
                win32gui.ShowWindow(self.main_hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(self.main_hwnd)
            if wparam == 1:  # Hide command
                win32gui.ShowWindow(self.main_hwnd, win32con.SW_HIDE)
            if wparam == 3: # Close command
                self.tk_root.quit()
                win32gui.PostQuitMessage(0)
                self._remove_tray_icon(hwnd)
        elif msg == win32con.WM_APP + 1:
            self._show_context_menu(hwnd)
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def _register_window_class(self):
        wndclass = win32gui.WNDCLASS()
        wndclass.hInstance = self.hInstance
        wndclass.lpszClassName = self.class_name
        wndclass.lpfnWndProc = self._wndproc
        try:
            win32gui.RegisterClass(wndclass)
        except Exception:
            pass  # already registered

    def _create_hidden_window(self):
        self.tray_hwnd = win32gui.CreateWindow(
            self.class_name,
            "StashSage Hidden Tray Window",
            0, 0, 0, 0, 0,
            0, 0,
            self.hInstance,
            None,
        )
        self._show_tray_icon(self.tray_hwnd)

    def _tray_loop(self):
        win32gui.PumpMessages()
