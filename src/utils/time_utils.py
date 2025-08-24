import requests
import datetime
import time

IRCTC_TIME_API_URL = "https://www.irctc.co.in/eticketing/services/committable/bookingAvailability.ping"

def get_irctc_server_time():
    """
    Fetches the official time from IRCTC's servers.

    The server responds with a timestamp in milliseconds. This function
    converts it into a standard Python datetime object.

    Returns:
        A datetime object representing the current time on IRCTC servers,
        or None if the request fails.
    """
    try:
        # Using a user-agent header to mimic a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(IRCTC_TIME_API_URL, headers=headers, timeout=5)
        response.raise_for_status() # Raises an HTTPError for bad responses (4xx or 5xx)

        # The response text is a plain timestamp in milliseconds
        server_timestamp_ms = int(response.text)

        # Convert milliseconds to seconds and create a datetime object
        server_time = datetime.datetime.fromtimestamp(server_timestamp_ms / 1000)
        return server_time

    except requests.exceptions.RequestException as e:
        print(f"[TimeUtil] Error fetching IRCTC server time: {e}")
        return None
    except (ValueError, KeyError) as e:
        print(f"[TimeUtil] Error parsing IRCTC server time response: {e}")
        return None

def wait_until(target_dt):
    """
    Waits with precision until the system clock reaches the target datetime.

    Args:
        target_dt (datetime.datetime): The target time to wait for.
    """
    while datetime.datetime.now() < target_dt:
        time.sleep(0.001) # Sleep for 1ms to avoid busy-waiting and reduce CPU usage

def wait_until_tatkal_time(hour=10, minute=0, second=0, offset_seconds=0, logger=None):
    """
    Waits until the specified Tatkal booking time, synchronized with IRCTC server time.
    """
    if logger:
        logger.info("Synchronizing with IRCTC Server Time...")
    else:
        print("[TimeUtil] Synchronizing with IRCTC Server Time...")

    server_time = get_irctc_server_time()
    if not server_time:
        if logger:
            logger.warning("Could not get server time. Using local system time.")
        else:
            print("[TimeUtil] Could not get server time. Using local system time.")
        server_time = datetime.datetime.now()

    local_time = datetime.datetime.now()
    time_diff = server_time - local_time

    log_msg = f"Server-Local time difference is {time_diff.total_seconds():.3f} seconds."
    if logger:
        logger.info(log_msg)
    else:
        print(f"[TimeUtil] {log_msg}")

    # Calculate the target time in our local timezone, adjusted by the server difference
    target_local_time = datetime.datetime.now().replace(
        hour=hour, minute=minute, second=second, microsecond=0
    ) - time_diff + datetime.timedelta(seconds=offset_seconds)


    if datetime.datetime.now() > target_local_time:
        log_msg = f"Target time {target_local_time.strftime('%H:%M:%S')} is already in the past."
        if logger:
            logger.warning(log_msg)
        else:
            print(f"[TimeUtil] {log_msg}")
        return

    log_msg = f"Waiting until {target_local_time.strftime('%H:%M:%S')} (Synchronized Target)..."
    if logger:
        logger.info(log_msg)
    else:
        print(f"[TimeUtil] {log_msg}")

    wait_until(target_local_time)

    log_msg = f"TATKAL TIME REACHED at {datetime.datetime.now().strftime('%H:%M:%S.%f')}"
    if logger:
        logger.info(log_msg)
    else:
        print(f"[TimeUtil] {log_msg}")


if __name__ == '__main__':
    print("--- IRCTC Time Utility Test ---")
    get_irctc_server_time()

    print("\n--- Tatkal Wait Test ---")
    # Test waiting for a time 5 seconds from now
    now = datetime.datetime.now()
    target = now + datetime.timedelta(seconds=5)
    print(f"Local time now is {now.strftime('%H:%M:%S')}")
    wait_until_tatkal_time(target.hour, target.minute, target.second)
    print("Test complete.")
