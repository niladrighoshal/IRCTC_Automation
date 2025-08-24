import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# In-memory storage for bot statuses, with a lock for thread safety
STATUS_DATA = {
    "time": "--:--:--.---",
    "bots": {}
}
STATUS_LOCK = threading.Lock()

class StatusRequestHandler(BaseHTTPRequestHandler):
    """A custom request handler for the status server."""
    def do_GET(self):
        if self.path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*') # Allow CORS
            self.end_headers()
            with STATUS_LOCK:
                self.wfile.write(json.dumps(STATUS_DATA).encode('utf-8'))
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        if self.path == '/status':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                update = json.loads(post_data)
                bot_id = update.get("bot_id")

                with STATUS_LOCK:
                    if "status" in update:
                        STATUS_DATA["bots"][bot_id] = update["status"]
                    if "time" in update:
                        STATUS_DATA["time"] = update["time"]

                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b'OK')
            except json.JSONDecodeError:
                self.send_error(400, "Bad Request: Invalid JSON")
        else:
            self.send_error(404, "Not Found")

    def do_OPTIONS(self):
        """Handle pre-flight CORS requests."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        """Silence the default logging."""
        return

class ThreadedHTTPServer(HTTPServer):
    """Handle requests in a separate thread."""
    def process_request(self, request, client_address):
        thread = threading.Thread(target=self.finish_request, args=(request, client_address))
        thread.daemon = True
        thread.start()

def run_server(port=8000):
    """Runs the status server in a background thread."""
    server_address = ('', port)
    httpd = ThreadedHTTPServer(server_address, StatusRequestHandler)

    server_thread = threading.Thread(target=httpd.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    print(f"Status server running in background on port {port}...")
    return httpd
