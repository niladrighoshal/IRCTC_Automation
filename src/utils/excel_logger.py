import xlwings as xw
import threading
import time
from datetime import datetime
import os
from collections import deque

class ExcelLogger:
    """
    A thread-safe, real-time logger using xlwings with a batching mechanism.
    Logs are buffered in memory and flushed to Excel by a background thread.
    """
    def __init__(self, filename="irctc_booking_log.xlsx"):
        self.filename = filename
        self.log_buffer = deque()
        self.lock = threading.Lock()
        self.stop_event = threading.Event()

        # Initialize the Excel application and workbook
        try:
            self.app = xw.App(visible=False)
            if os.path.exists(self.filename):
                self.book = self.app.books.open(self.filename)
            else:
                self.book = self.app.books.add()
                self.book.save(self.filename)

            if 'Logs' not in [sheet.name for sheet in self.book.sheets]:
                self.book.sheets.add('Logs')
            self.sheet = self.book.sheets['Logs']
            self.sheet.activate()
            print("[ExcelLogger] Successfully connected to Excel.")
        except Exception as e:
            print(f"[ExcelLogger] CRITICAL: Failed to initialize xlwings. Real-time logging will be disabled. Error: {e}")
            self.app = self.book = self.sheet = None

        # Start the background thread to flush logs
        self.flusher_thread = threading.Thread(target=self._log_flusher, daemon=True)
        self.flusher_thread.start()

    def _get_column_letter(self, instance_id):
        return chr(ord('A') + instance_id)

    def setup_column(self, instance_id, bot_config, config_filename):
        if not self.book: return
        with self.lock:
            try:
                col = self._get_column_letter(instance_id)
                self.sheet.range(f'{col}1:{col}20').clear_contents() # Clear previous logs for this instance
                row = 1

                account = bot_config.get('account', {})
                train_details = bot_config.get('train', {})
                passengers = bot_config.get('passengers', [])

                data_to_log = {
                    "Browser Instance": instance_id, "Using Config": os.path.basename(config_filename),
                    "Username": account.get('username', 'N/A'), "Password": "*" * len(account.get('password', '')),
                    "Train No": train_details.get('train_no', 'N/A'), "From": train_details.get('from_code', 'N/A'),
                    "To": train_details.get('to_code', 'N/A'),
                    "Date": datetime.strptime(train_details.get('date'), '%d%m%Y').strftime('%d-%b-%Y') if train_details.get('date') else 'N/A',
                    "Class": train_details.get('class', 'N/A'), "Quota": train_details.get('quota', 'N/A'),
                }

                header_range = self.sheet.range(f'{col}{row}').options(transpose=True)
                header_range.value = [[f"{key}: {value}"] for key, value in data_to_log.items()]
                row += len(data_to_log)

                pass_header_cell = self.sheet.range(f'{col}{row}')
                pass_header_cell.value = "--- Passengers ---"
                row += 1

                if passengers:
                    pass_range = self.sheet.range(f'{col}{row}').options(transpose=True)
                    pass_range.value = [[f"P{i+1}: {p.get('name')}, {p.get('age')}, {p.get('sex')}"] for i, p in enumerate(passengers)]
                    row += len(passengers)

                row += 1
                status_header_cell = self.sheet.range(f'{col}{row}')
                status_header_cell.value = "--- Status Log ---"
                ts_header_cell = self.sheet.range(f'A{row}')
                ts_header_cell.value = "Timestamp"

                # Apply bold formatting
                self.sheet.range(f'{col}1:{col}{row}').font.bold = True
                ts_header_cell.font.bold = True

                self.sheet.range(f'A1:{col}1').columns.autofit()
                self.book.save()
            except Exception as e:
                print(f"[ExcelLogger] Error setting up column for instance {instance_id}: {e}")

    def log(self, instance_id, message):
        """Appends a log message to the in-memory buffer."""
        timestamp = datetime.now()
        with self.lock:
            self.log_buffer.append((timestamp, instance_id, message))

    def _log_flusher(self):
        """Background thread function to write buffered logs to Excel."""
        while not self.stop_event.is_set():
            time.sleep(1) # Flush every 1 second

            logs_to_write = []
            with self.lock:
                if self.log_buffer:
                    logs_to_write = list(self.log_buffer)
                    self.log_buffer.clear()

            if logs_to_write and self.book:
                try:
                    # Group logs by instance_id to write them in batches
                    logs_by_instance = {}
                    for ts, inst_id, msg in logs_to_write:
                        if inst_id not in logs_by_instance:
                            logs_by_instance[inst_id] = []
                        logs_by_instance[inst_id].append((ts.strftime('%H:%M:%S.%f')[:-3], msg))

                    for inst_id, logs in logs_by_instance.items():
                        col = self._get_column_letter(inst_id)
                        last_row = self.sheet.range(f'{col}' + str(self.sheet.cells.last_cell.row)).end('up').row

                        ts_col_letter = 'A'
                        ts_write_range = self.sheet.range(f'{ts_col_letter}{last_row + 1}').options(transpose=True)
                        msg_write_range = self.sheet.range(f'{col}{last_row + 1}').options(transpose=True)

                        ts_data = [[log[0]] for log in logs]
                        msg_data = [[log[1]] for log in logs]

                        ts_write_range.value = ts_data
                        msg_write_range.value = msg_data

                    self.book.save()
                except Exception as e:
                    print(f"[ExcelLogger] Error flushing logs to Excel: {e}")

    def close(self):
        """Signals the flusher thread to stop and closes the Excel app."""
        print("[ExcelLogger] Closing logger...")
        self.stop_event.set()
        self.flusher_thread.join(timeout=2) # Wait for the flusher to finish
        # Final flush
        self._log_flusher()
        if self.app:
            try:
                self.book.close()
                self.app.quit()
                print("[ExcelLogger] Closed Excel workbook and application.")
            except Exception as e:
                print(f"[ExcelLogger] Error closing Excel: {e}")
