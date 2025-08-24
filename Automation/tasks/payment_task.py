# ... (imports)
class PaymentTask:
    def __init__(self, orchestrator):
        self.bot = orchestrator
        self.driver = self.bot.driver
        self._log = self.bot._log
        self._click_with_retries = self.bot._click_with_retries

    def execute(self, config):
        self._log("On review page, handling final captcha before payment...")

        # --- Captcha Loop on Review Page ---
        # ... (logic is the same)

        # --- Click Pay & Book ---
        # ... (logic is the same)

        # --- Handle Payment Gateway ---
        payment_method = config.get("preferences", {}).get("payment_method")
        upi_id = config.get("preferences", {}).get("upi_id")

        if "BHIM UPI" in payment_method:
            return self._handle_upi_gateway(upi_id)
        # ...
        return False

    def _handle_upi_gateway(self, upi_id):
        # ... (logic is the same)
        return True # Placeholder

    def _pay_with_wallet(self):
        # ... (logic is the same)
        return False
