# main.py
import threading
from gui_status import FloatingGUI
from Automation.login import IRCTCLogin

# Configuration
BRAVE_PATH = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
PROFILE_PATH = r"G:\Project\IRCTC_Tatkal\Automation\BraveProfile"
AUTOMATION_FOLDER = r"G:\Project\IRCTC_Tatkal\Automation"

TIMED = True
AC = True
SL = False
USE_GPU = False

def automation_task(gui):
    bot = IRCTCLogin(automation_folder=AUTOMATION_FOLDER, gui=gui, use_gpu=USE_GPU)
    success = bot.login(brave_path=BRAVE_PATH, profile_path=PROFILE_PATH)
    # give driver to GUI (GUI itself does not use it directly, but you may want it)
    if bot.driver:
        gui.set_driver(bot.driver)
    if success:
        gui.set_status_text("Logged in successfully")
    else:
        gui.set_status_text("Login failed")

    # timed booking flow (placeholders)
    if success and TIMED:
        target_time = "09:59:00" if AC else "10:59:00"
        gui.set_status_text(f"Waiting until {target_time} to start booking...")
        bot.wait_until(target_time)
        gui.set_status_text("Filling train details...")
        bot.fill_train_details(AC=AC, SL=SL)
        target_time_search = "10:00:00" if AC else "11:00:00"
        gui.set_status_text(f"Waiting until {target_time_search} to press Search...")
        bot.wait_until(target_time_search)
        gui.set_status_text("Pressing search...")
        bot.press_search_button()

def main():
    gui = FloatingGUI()
    t = threading.Thread(target=automation_task, args=(gui,), daemon=True)
    t.start()
    gui.run()
    

if __name__ == "__main__":
    main()
