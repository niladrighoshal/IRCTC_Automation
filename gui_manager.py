import tkinter as tk
import queue
from gui_status import BotWindow

class GUIManager:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()  # Hide the main root window
        self.update_queue = queue.Queue()
        self.windows = {}  # To store windows by bot_id

    def create_bot_windows(self, bot_id, x_offset=0, y_offset=0):
        window_pair = BotWindow(self.root, x_offset, y_offset)
        self.windows[bot_id] = window_pair
        return window_pair

    def post_update(self, bot_id, window_type, text):
        """Post a GUI update to the queue. window_type is 'time' or 'status'."""
        self.update_queue.put((bot_id, window_type, text))

    def _process_queue(self):
        """Process all pending GUI updates."""
        try:
            while not self.update_queue.empty():
                bot_id, window_type, text = self.update_queue.get_nowait()
                if bot_id in self.windows:
                    self.windows[bot_id].update_label(window_type, text)
        finally:
            self.root.after(100, self._process_queue)  # Poll every 100ms

    def run(self):
        """Start the GUI main loop."""
        self._process_queue()  # Start the queue processor
        self.root.mainloop()
