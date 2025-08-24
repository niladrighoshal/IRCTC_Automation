import http.server
import socketserver
import json
import threading
from urllib.parse import urlparse

STATUS_DATA = {}
STATUS_LOCK = threading.Lock()
PORT = 8000

class StatusServerHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            with STATUS_LOCK:
                self.wfile.write(json.dumps(STATUS_DATA).encode('utf-8'))
        else: self.send_error(404, "File Not Found")

    def do_POST(self):
        parsed_path = urlparse(self.path)
        path_parts = parsed_path.path.split('/')
        if len(path_parts) == 3 and path_parts[1] == 'status':
            try:
                bot_id = int(path_parts[2])
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length).decode('utf-8')
                new_status = json.loads(post_data).get('status', 'UNKNOWN')
                with STATUS_LOCK: STATUS_DATA[bot_id] = new_status
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b'{"success": true}')
            except: self.send_error(400, "Bad Request")
        elif parsed_path.path == '/clear':
            with STATUS_LOCK: STATUS_DATA.clear()
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(b'{"success": true}')
        else: self.send_error(404, "File Not Found")

    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-type")
        self.end_headers()

    def log_message(self, format, *args): return

def run_server():
    with socketserver.TCPServer(("", PORT), StatusServerHandler) as httpd:
        httpd.serve_forever()

def start_server_in_thread():
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    print("Live status server started in background thread.")
    return server_thread
