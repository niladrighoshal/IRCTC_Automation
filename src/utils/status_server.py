import http.server
import socketserver
import threading
import json
from datetime import datetime

# --- Global data store for bot statuses ---
# This dictionary will be shared across all threads and requests.
# The key is the instance_id, the value is a list of (timestamp, status) tuples.
bot_statuses = {}
status_lock = threading.Lock()

class StatusUpdateHandler(http.server.BaseHTTPRequestHandler):
    """A custom handler for GET and POST requests."""

    def do_POST(self):
        """Handles status updates from bot instances."""
        if self.path != '/update':
            self.send_error(404, "File Not Found")
            return
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)

            instance_id = data.get('instance_id')
            status = data.get('status')

            if instance_id and status:
                with status_lock:
                    if instance_id not in bot_statuses:
                        bot_statuses[instance_id] = []
                    # Prepend new status to the list
                    bot_statuses[instance_id].insert(0, (datetime.now(), status))
                    # Keep only the last 20 statuses for each bot
                    bot_statuses[instance_id] = bot_statuses[instance_id][:20]

                self.send_response(200)
                self.end_headers()
            else:
                self.send_error(400, "Bad Request: Missing 'instance_id' or 'status'")
        except Exception as e:
            self.send_error(500, f"Internal Server Error: {e}")

    def do_GET(self):
        """Serves the auto-refreshing HTML dashboard."""
        if self.path != '/':
            self.send_error(404, "File Not Found")
            return

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        html = """
        <html>
        <head>
            <title>IRCTC Bot Status Dashboard</title>
            <meta http-equiv="refresh" content="2">
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; background-color: #f0f2f5; color: #333; margin: 0; padding: 20px;}
                h1 { color: #1d3557; }
                .container { display: flex; flex-wrap: wrap; gap: 20px; }
                .bot-card { background-color: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); padding: 15px; min-width: 300px; flex-grow: 1; }
                .bot-title { font-size: 1.2em; font-weight: bold; color: #457b9d; border-bottom: 1px solid #eee; padding-bottom: 10px; margin-bottom: 10px; }
                .status-list { list-style-type: none; padding: 0; margin: 0; font-size: 0.9em; max-height: 400px; overflow-y: auto; }
                .status-list li { padding: 5px 0; border-bottom: 1px solid #f0f0f0; }
                .status-list li:first-child { font-weight: bold; color: #e63946; }
                .status-time { font-size: 0.8em; color: #999; margin-right: 10px; }
            </style>
        </head>
        <body>
            <h1>IRCTC Bot Status Dashboard</h1>
            <p>This page will automatically refresh every 2 seconds. Last updated: """ + datetime.now().strftime('%H:%M:%S') + """</p>
            <div class="container">
        """
        with status_lock:
            if not bot_statuses:
                html += "<p>No bot data received yet. Start a bot from the UI.</p>"
            else:
                sorted_instances = sorted(bot_statuses.keys())
                for instance_id in sorted_instances:
                    html += f'<div class="bot-card"><div class="bot-title">Browser Instance {instance_id}</div>'
                    html += '<ul class="status-list">'
                    statuses = bot_statuses.get(instance_id, [])
                    for i, (ts, status) in enumerate(statuses):
                        html += f'<li><span class="status-time">{ts.strftime("%H:%M:%S")}</span>{status}</li>'
                    html += '</ul></div>'

        html += """
            </div>
        </body>
        </html>
        """
        self.wfile.write(html.encode('utf-8'))

    def log_message(self, format, *args):
        """Suppress default request logging."""
        return

class StatusServer(threading.Thread):
    """A thread to run the HTTP server in the background."""
    def __init__(self, port=8889):
        super().__init__(daemon=True)
        self.port = port
        self.httpd = None
        self.server_started = threading.Event()

    def run(self):
        try:
            self.httpd = socketserver.TCPServer(("", self.port), StatusUpdateHandler)
            self.server_started.set()
            print(f"[StatusServer] Serving dashboard at http://localhost:{self.port}")
            self.httpd.serve_forever()
        except Exception as e:
            print(f"[StatusServer] Could not start server: {e}")
            self.server_started.set() # Set event even on failure to not block main thread

    def stop(self):
        if self.httpd:
            print("[StatusServer] Shutting down.")
            self.httpd.shutdown()
            self.httpd.server_close()
