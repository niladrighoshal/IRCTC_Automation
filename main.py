import threading
import time
from gui_manager import GUIManager
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

def automation_task(bot_id, gui_manager):
    """The main task for a single browser/thread."""
    try:
        bot = BotOrchestrator(
            bot_id=bot_id,
            gui_manager=gui_manager,
            automation_folder=AUTOMATION_FOLDER,
            use_gpu=USE_GPU
        )
        bot.run_booking_flow(
            brave_path=BRAVE_PATH,
            profile_path=PROFILE_PATH,
            timed_booking=TIMED,
            ac_booking=AC,
            sl_booking=SL
        )
    except Exception as e:
        # Log fatal error to the GUI if possible
        if 'bot' in locals() and bot is not None:
            bot._log(f"FATAL ERROR: {e}")
            bot.stop()
        else:
            print(f"[{bot_id}] A fatal error occurred: {e}")

def main():
    if BROWSER_COUNT < 1:
        print("BROWSER_COUNT must be at least 1.")
        return

    gui_manager = GUIManager()
    threads = []

    for i in range(BROWSER_COUNT):
        bot_id = i + 1
        x_offset = (i % 4) * 320
        y_offset = (i // 4) * 220

        # GUIManager creates and stores the windows
        gui_manager.create_bot_windows(bot_id, x_offset, y_offset)

        thread = threading.Thread(target=automation_task, args=(bot_id, gui_manager), daemon=True)
        threads.append(thread)
        thread.start()
        time.sleep(2)

    # The GUIManager runs the main loop
    gui_manager.run()

if __name__ == "__main__":
    print(f"Starting IRCTC Bot with {BROWSER_COUNT} browser(s) in 3 seconds...")
    time.sleep(3)
    main()
