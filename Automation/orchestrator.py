# ... (imports) ...
import requests # Add requests for http calls

# ... (AppState Enum) ...

class BotOrchestrator:
    STATUS_SERVER_URL = "http://localhost:8000/status"
    PAGE_LOAD_TIMEOUT = 300

    def __init__(self, bot_id, automation_folder, use_gpu=False):
        self.bot_id = bot_id
        self.automation_folder = Path(automation_folder)
        # ... (other init remains the same, remove gui_manager)
        self.driver = None
        self._stop_event = threading.Event()
        self.use_gpu = use_gpu
        self.ocr = CaptchaSolver(use_gpu=self.use_gpu) if CaptchaSolver else None
        self.login_task = LoginTask(self)
        # ... (init other tasks)

    def _log(self, msg):
        stamp = datetime.now().strftime("%H:%M:%S")
        txt = f"[{self.bot_id}] {stamp} {msg}"
        print(txt) # Keep console logging
        try:
            payload = {"bot_id": self.bot_id, "status": txt}
            requests.post(self.STATUS_SERVER_URL, json=payload, timeout=0.5)
        except requests.exceptions.RequestException:
            pass # Ignore if status server is down

    def _time_log(self, time_str):
        try:
            payload = {"time": time_str}
            requests.post(self.STATUS_SERVER_URL, json=payload, timeout=0.5)
        except requests.exceptions.RequestException:
            pass

    # ... (the rest of the orchestrator, including the state machine
    # and helper methods, remains largely the same. The key change is
    # that it no longer knows about a GUI, only the status server)

    def run_booking_flow(self, config):
        # This method now only needs the config
        # It no longer needs brave_path or profile_path directly
        # These should be in the config if needed, or standardized
        # For simplicity, I'll keep the launch call as is

        run_config = config.get("run_config", {})
        brave_path = "C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe"
        profile_path = os.path.join(os.path.dirname(__file__), "BraveProfile")
        self.launch_browser(brave_path, profile_path, run_config.get("headless_mode", False))

        # Start background threads
        # ...

        # Start state machine loop
        while not self._stop_event.is_set():
            # ...
            pass

    # ...
