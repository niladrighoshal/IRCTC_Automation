# gui_status.py
import threading
import tkinter as tk
from datetime import datetime
import time

class FloatingGUI:
    def __init__(self, driver=None):
        self.driver = driver  # Can be set later
        self.running = True

        # === Time Window (Top floating window) ===
        self.time_root = tk.Tk()
        self.time_root.overrideredirect(True)  # Remove title bar
        self.time_root.attributes("-topmost", True)
        self.time_root.geometry("300x60+50+50")  # Initial position

        self.time_label = tk.Label(
            self.time_root,
            text="Fetching Time...",
            font=("Helvetica", 14),
            fg="white",
            bg="black"
        )
        self.time_label.pack(expand=True, fill="both")

        # === Status Window (Bottom floating window) ===
        self.status_root = tk.Toplevel(self.time_root)
        self.status_root.overrideredirect(True)
        self.status_root.attributes("-topmost", True)
        self.status_root.geometry("300x60+50+150")  # Positioned below

        self.status_label = tk.Label(
            self.status_root,
            text="Status: Waiting...",
            font=("Helvetica", 14),
            fg="black",
            bg="yellow"
        )
        self.status_label.pack(expand=True, fill="both")

        # Start background threads
        threading.Thread(target=self.update_time_loop, daemon=True).start()
        threading.Thread(target=self.update_status_loop, daemon=True).start()

    # === Time Updater ===
    def update_time_loop(self):
        while self.running:
            try:
                if self.driver:
                    # Get time from IRCTC dynamic span
                    time_element = self.driver.find_element("css selector", "span strong")
                    site_time = time_element.text.strip()
                else:
                    site_time = datetime.now().strftime("%d-%b-%Y [%H:%M:%S]")

                self.time_label.config(text=site_time)
            except Exception:
                # fallback: local time
                self.time_label.config(
                    text=datetime.now().strftime("%d-%b-%Y [%H:%M:%S]")
                )
            time.sleep(1)

    # === Status Updater ===
    def update_status_loop(self):
        while self.running:
            try:
                if hasattr(self, "custom_status"):
                    status = self.custom_status
                elif self.driver:
                    if "login" in self.driver.current_url.lower():
                        status = "🔴 Logged Out"
                    else:
                        status = "🟢 Logged In"
                else:
                    status = "⚪ Driver not ready"

                self.status_label.config(text=status)
            except Exception:
                self.status_label.config(text="⚪ Error Checking Status")
            time.sleep(1)

    # === Set driver dynamically ===
    def set_driver(self, driver):
        self.driver = driver

    # === Update status dynamically ===
    def set_status_text(self, text):
        self.custom_status = text

    # === Close GUI ===
    def close(self):
        self.running = False
        self.time_root.destroy()

    # === Run GUI loop ===
    def run(self):
        try:
            self.time_root.mainloop()
        finally:
            self.running = False
