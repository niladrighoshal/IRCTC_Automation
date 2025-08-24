from src.core.bot import IRCTCBot

def run_bot_thread(account_details, booking_data, instance_id):
    try:
        bot = IRCTCBot(account_details, booking_data, instance_id)
        bot.run()
    except Exception as e:
        print(f"[BotRunner] Thread for Bot {instance_id} crashed: {e}")
