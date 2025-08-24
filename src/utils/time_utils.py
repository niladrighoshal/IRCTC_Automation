import requests
import datetime
import time

IRCTC_TIME_API_URL = "https://www.irctc.co.in/eticketing/services/committable/bookingAvailability.ping"

def get_irctc_server_time(logger=None):
    """
    Fetches the official time from IRCTC's servers.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # Increased timeout as requested, though 5s is usually plenty for this API
        response = requests.get(IRCTC_TIME_API_URL, headers=headers, timeout=20)
        response.raise_for_status()
        server_timestamp_ms = int(response.text)
        return datetime.datetime.fromtimestamp(server_timestamp_ms / 1000)
    except Exception as e:
        if logger:
            logger.error(f"Could not fetch IRCTC server time: {e}")
        return None

def wait_until(target_dt, logger=None):
    """
    Waits with precision until the system clock reaches the target datetime.
    """
    now = datetime.datetime.now()
    if now > target_dt:
        if logger:
            logger.warning(f"Target time {target_dt} is already in the past.")
        return

    if logger:
        logger.info(f"Waiting until {target_dt.strftime('%H:%M:%S.%f')[:-3]}...")

    while datetime.datetime.now() < target_dt:
        # Sleep for a short duration to avoid high CPU usage
        time.sleep(0.001)

    if logger:
        logger.info(f"Target time reached at {datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]}")

def get_synchronized_target_time(hour, minute, second=0, offset_seconds=0, logger=None):
    """
    Calculates the target time synchronized with IRCTC server time.
    """
    log_msg = "Synchronizing with IRCTC Server Time..."
    if logger: logger.info(log_msg)

    server_time = get_irctc_server_time(logger)
    if not server_time:
        log_msg = "Could not get server time. Using local system time for sync calculation."
        if logger: logger.warning(log_msg)
        server_time = datetime.datetime.now()

    local_time = datetime.datetime.now()
    time_diff = server_time - local_time

    log_msg = f"Server-Local time difference is {time_diff.total_seconds():.3f} seconds."
    if logger: logger.info(log_msg)

    # Calculate the target time in our local timezone, adjusted by the server difference
    target_local_time = datetime.datetime.now().replace(
        hour=hour, minute=minute, second=second, microsecond=0
    ) - time_diff + datetime.timedelta(seconds=offset_seconds)

    return target_local_time
