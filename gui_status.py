import tkinter as tk

class BotWindow:
    def __init__(self, root, x_offset=0, y_offset=0):
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()

        # === Time Window (Top-Right) ===
        self.time_window = tk.Toplevel(root)
        self.time_window.overrideredirect(True)
        self.time_window.attributes("-topmost", True)
        time_x = screen_width - 300 - 50
        time_y = 50
        self.time_window.geometry(f"300x60+{time_x - x_offset}+{time_y + y_offset}")
        self.time_label = tk.Label(self.time_window, text="--:--:--.---", font=("Courier", 16, "bold"), fg="lime", bg="black")
        self.time_label.pack(expand=True, fill="both")

        # === Status Window (Bottom-Left) ===
        self.status_window = tk.Toplevel(root)
        self.status_window.overrideredirect(True)
        self.status_window.attributes("-topmost", True)
        status_x = 50
        status_y = screen_height - 60 - 50
        self.status_window.geometry(f"300x60+{status_x + x_offset}+{status_y - y_offset}")
        self.status_label = tk.Label(self.status_window, text="Status: Initializing...", font=("Helvetica", 14), fg="black", bg="yellow")
        self.status_label.pack(expand=True, fill="both")

    def update_label(self, window_type, text):
        """Updates the text of the specified label."""
        if window_type == 'time':
            self.time_label.config(text=text)
        elif window_type == 'status':
            self.status_label.config(text=text)
