import threading
import time
import json
import os
from Automation.orchestrator import BotOrchestrator
from status_server import run_server
import json
import os
import threading
import time

def load_config():
    """Loads the run configuration from config.json."""
    try:
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config.json: {e}")
        return None

def automation_task(bot_id, config):
    """The main task for a single browser/thread."""
    run_config = config.get("run_config", {})
    try:
        bot = BotOrchestrator(
            bot_id=bot_id,
            automation_folder=os.path.join(os.path.dirname(__file__), "Automation"),
            use_gpu=run_config.get("use_gpu", False)
        )
        bot.run_booking_flow(config=config)
    except Exception as e:
        # The bot's own logging will handle reporting this to the server
        print(f"[{bot_id}] A fatal error occurred: {e}")
        if 'bot' in locals() and bot is not None:
            bot.stop()

def main():
    config = load_config()
    if not config:
        print("Could not load config.json. Exiting.")
        return

    browser_count = config.get("run_config", {}).get("browser_count", 1)

    threads = []
    for i in range(browser_count):
        bot_id = i + 1
        thread = threading.Thread(target=automation_task, args=(bot_id, config))
        threads.append(thread)
        thread.start()
        time.sleep(2) # Stagger browser launches slightly

    for t in threads:
        t.join() # Wait for all bot threads to complete

if __name__ == "__main__":
    print("Bot process started. Reading config.json...")
    main()
