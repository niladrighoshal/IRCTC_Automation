import threading
import time
from src.core.bot import IRCTCBot

class BotRunner:
    """
    Manages the creation and execution of multiple IRCTCBot instances,
    each in its own thread.
    """
    def __init__(self, config, excel_logger, config_filename):
        """
        Initializes the BotRunner with the booking configuration and logger.

        Args:
            config (dict): The configuration dictionary loaded from the JSON file.
            excel_logger (ExcelLogger): An instance of the Excel logger.
            config_filename (str): The filename of the config being used.
        """
        self.config = config
        self.excel_logger = excel_logger
        self.config_filename = config_filename
        self.threads = []

    def _run_bot_instance(self, credentials, instance_id):
        """
        The target function for each bot thread. Instantiates and runs a single bot.
        """
        print(f"[BotRunner] Starting bot instance {instance_id} for user '{credentials.get('username', 'N/A')}'.")
        try:
            # Pass the logger and other details down to the bot instance
            bot_config = {
                'account': credentials,
                'train': self.config.get('train', {}),
                'passengers': self.config.get('passengers', []),
                'preferences': self.config.get('preferences', {})
            }
            bot = IRCTCBot(
                bot_config=bot_config,
                excel_logger=self.excel_logger,
                config_filename=self.config_filename,
                instance_id=instance_id
            )
            bot.run()
        except Exception as e:
            print(f"[BotRunner] Thread for Bot {instance_id} crashed: {e}")

    def start(self):
        """
        Starts the bot instances based on the configuration.
        """
        preferences = self.config.get("preferences", {})
        logins = self.config.get("logins", [])

        browser_count = preferences.get("browser_count", 1)

        if not logins:
            print("[BotRunner] Error: No login credentials found in the configuration file.")
            return

        # Determine the number of bots to launch
        num_to_launch = min(browser_count, len(logins))

        if num_to_launch == 0:
            print("[BotRunner] No bots to launch. Check browser count and credentials.")
            return

        print(f"[BotRunner] Launching {num_to_launch} bot instance(s).")

        for i in range(num_to_launch):
            credentials = logins[i]
            if not credentials.get("username") or not credentials.get("password"):
                print(f"[BotRunner] Skipping instance {i+1} due to missing username or password.")
                continue

            thread = threading.Thread(
                target=self._run_bot_instance,
                args=(credentials, i + 1)
            )
            self.threads.append(thread)
            thread.start()
            time.sleep(2) # Stagger browser launches slightly

        # Wait for all threads to complete
        print("[BotRunner] All bot threads have been started. Waiting for them to complete.")
        for thread in self.threads:
            thread.join()

        print("[BotRunner] All bot instances have finished their execution.")
