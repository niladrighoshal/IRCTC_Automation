from src.core.bot import IRCTCBot

def run_bot_thread(account_details, booking_data, instance_id):
    """
    This function is the target for each bot's thread.
    It creates an instance of the IRCTCBot and calls its run method.
    """
    try:
        bot = IRCTCBot(account_details, booking_data, instance_id)
        bot.run()
    except Exception as e:
        # This is a top-level catch to prevent a single bot crash
        # from taking down the whole application.
        print(f"[BotRunner] Thread for Bot {instance_id} crashed: {e}")
