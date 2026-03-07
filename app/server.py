from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os

from app.storage.task_manager import load_tasks

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
WEB_DIR = os.path.join(PROJECT_ROOT, "web")


class TaskServer(BaseHTTPRequestHandler):

    def do_GET(self):

        # API endpoint for task data
        if self.path == "/tasks":

            tasks = load_tasks()

            response = json.dumps(tasks)

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()

            self.wfile.write(response.encode())

        # Serve the overlay HTML
        elif self.path == "/overlay":

            file_path = os.path.join(WEB_DIR, "overlay.html")

            with open(file_path, "r", encoding="utf-8") as f:
                html = f.read()

            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()

            self.wfile.write(html.encode())

        else:
            self.send_response(404)
            self.end_headers()


def run_server():

    server_address = ("0.0.0.0", 5000)
    httpd = HTTPServer(server_address, TaskServer)

    print("Server running on port 5000")

    httpd.serve_forever()


if __name__ == "__main__":
    run_server()