# main.py
import threading
import time
from gui_status import FloatingGUI
from Automation.orchestrator import BotOrchestrator

# Configuration
BRAVE_PATH = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
PROFILE_PATH = r"G:\Project\IRCTC_Tatkal\Automation\BraveProfile"
AUTOMATION_FOLDER = r"G:\Project\IRCTC_Tatkal\Automation"

TIMED = False
AC = True
SL = True
USE_GPU = False
BROWSER_COUNT = 1 # Number of browsers to launch

def automation_task(gui):
    """The main task for a single browser/thread."""
    try:
        bot = BotOrchestrator(automation_folder=AUTOMATION_FOLDER, gui=gui, use_gpu=USE_GPU)
        bot.run_booking_flow(
            brave_path=BRAVE_PATH,
            profile_path=PROFILE_PATH,
            timed_booking=TIMED,
            ac_booking=AC,
            sl_booking=SL
        )
    except Exception as e:
        # Broad exception handler to catch any unexpected errors in the thread
        if 'bot' in locals() and bot is not None:
            bot._log(f"FATAL ERROR: {e}")
            bot.stop()
        else:
            print(f"A fatal error occurred before bot initialization: {e}")

def main():
    if BROWSER_COUNT < 1:
        print("BROWSER_COUNT must be at least 1.")
        return

    threads = []
    guis = []

    for i in range(BROWSER_COUNT):
        # Stagger the GUI windows
        x_offset = (i % 4) * 320
        y_offset = (i // 4) * 220

        gui = FloatingGUI(x_offset=x_offset, y_offset=y_offset)
        guis.append(gui)

        thread = threading.Thread(target=automation_task, args=(gui,), daemon=True)
        threads.append(thread)
        thread.start()
        time.sleep(2) # Stagger browser launches slightly

    # The mainloop of one GUI will keep the script alive for all windows
    if guis:
        guis[0].run()

if __name__ == "__main__":
    # Add a small delay before starting everything
    print(f"Starting IRCTC Bot with {BROWSER_COUNT} browser(s) in 3 seconds...")
    time.sleep(3)
    main()
