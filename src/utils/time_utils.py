import requests
import datetime
import time

IRCTC_TIME_API_URL = "https://www.irctc.co.in/eticketing/services/committable/bookingAvailability.ping"

def get_irctc_server_time(logger=None):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(IRCTC_TIME_API_URL, headers=headers, timeout=20)
        response.raise_for_status()
        return datetime.datetime.fromtimestamp(int(response.text) / 1000)
    except Exception as e:
        if logger: logger.error(f"Could not fetch IRCTC server time: {e}")
        return None

def wait_until(target_dt, logger=None):
    now = datetime.datetime.now()
    if now > target_dt:
        if logger: logger.warning(f"Target time {target_dt} is already in the past.")
        return
    if logger: logger.info(f"Waiting until {target_dt.strftime('%H:%M:%S.%f')[:-3]}...")
    while datetime.datetime.now() < target_dt:
        time.sleep(0.001)
    if logger: logger.info(f"Target time reached at {datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]}")

def get_synchronized_target_time(hour, minute, second=0, offset_seconds=0, logger=None):
    if logger: logger.info("Synchronizing with IRCTC Server Time...")
    server_time = get_irctc_server_time(logger)
    if not server_time:
        if logger: logger.warning("Could not get server time. Using local system time.")
        server_time = datetime.datetime.now()
    time_diff = server_time - datetime.datetime.now()
    if logger: logger.info(f"Server-Local time difference is {time_diff.total_seconds():.3f} seconds.")
    target_local_time = datetime.datetime.now().replace(hour=hour, minute=minute, second=second, microsecond=0) - time_diff + datetime.timedelta(seconds=offset_seconds)
    return target_local_time
