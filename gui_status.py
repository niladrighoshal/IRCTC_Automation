# gui_status.py
import threading
import tkinter as tk
from datetime import datetime, timedelta
import time

class FloatingGUI:
    def __init__(self, driver=None, x_offset=0, y_offset=0):
        self.driver = driver
        self.running = True

        # Time sync variables
        self.server_datetime = None
        self.last_sync_local_time = 0
        self.time_lock = threading.Lock()

        self.time_root = tk.Tk()
        self.time_root.withdraw()
        screen_width = self.time_root.winfo_screenwidth()
        screen_height = self.time_root.winfo_screenheight()
        self.time_root.deiconify()

        # === Time Window (Top floating window) ===
        self.time_root.overrideredirect(True)
        self.time_root.attributes("-topmost", True)
        time_x = screen_width - 300 - 50
        time_y = 50
        self.time_root.geometry(f"300x60+{time_x - x_offset}+{time_y + y_offset}")
        self.time_label = tk.Label(self.time_root, text="--:--:--.---", font=("Courier", 16, "bold"), fg="lime", bg="black")
        self.time_label.pack(expand=True, fill="both")

        # === Status Window (Bottom floating window) ===
        self.status_root = tk.Toplevel(self.time_root)
        self.status_root.overrideredirect(True)
        self.status_root.attributes("-topmost", True)
        status_x = 50
        status_y = screen_height - 60 - 50
        self.status_root.geometry(f"300x60+{status_x + x_offset}+{status_y - y_offset}")
        self.status_label = tk.Label(self.status_root, text="Status: Initializing...", font=("Helvetica", 14), fg="black", bg="yellow")
        self.status_label.pack(expand=True, fill="both")

        # Start background threads
        threading.Thread(target=self._sync_server_time_loop, daemon=True).start()
        threading.Thread(target=self._update_display_loop, daemon=True).start()
        threading.Thread(target=self.update_status_loop, daemon=True).start()

    def _sync_server_time_loop(self):
        """Periodically fetches time from the server to sync."""
        while self.running:
            if not self.driver:
                time.sleep(1)
                continue
            try:
                time_element = self.driver.find_element("css selector", "span strong")
                raw_time = time_element.text.strip()
                time_str = raw_time.split("[", 1)[1].split("]", 1)[0].strip()

                with self.time_lock:
                    # Combine with today's date to get a full datetime object
                    server_time_obj = datetime.strptime(time_str, "%H:%M:%S").time()
                    self.server_datetime = datetime.combine(datetime.today(), server_time_obj)
                    self.last_sync_local_time = time.perf_counter()
            except Exception:
                pass
            time.sleep(10)

    def _update_display_loop(self):
        """Updates the time display with millisecond precision."""
        while self.running:
            display_str = "--:--:--.---"
            with self.time_lock:
                if self.server_datetime:
                    elapsed = time.perf_counter() - self.last_sync_local_time
                    current_precise_time = self.server_datetime + timedelta(seconds=elapsed)
                    display_str = current_precise_time.strftime("%H:%M:%S") + f".{current_precise_time.microsecond // 1000:03d}"

            self.time_label.config(text=display_str)
            time.sleep(0.05)

    def update_status_loop(self):
        while self.running:
            try:
                if hasattr(self, "custom_status"): status = self.custom_status
                elif self.driver: status = "🟢 Logged In" if "train-search" in self.driver.current_url else "🔴 Logged Out"
                else: status = "⚪ Driver not ready"
                self.status_label.config(text=status)
            except Exception: self.status_label.config(text="⚪ Error")
            time.sleep(1)

    def set_driver(self, driver): self.driver = driver
    def set_status_text(self, text): self.custom_status = text
    def close(self):
        self.running = False
        self.time_root.destroy()
    def run(self):
        try: self.time_root.mainloop()
        finally: self.running = False
