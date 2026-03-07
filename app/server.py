from http.server import BaseHTTPRequestHandler, HTTPServer


class TaskServer(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Server is working")

        elif self.path == "/overlay":
            html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Overlay Test</title>
    <style>
        body {
            margin: 0;
            background: rgba(255, 0, 0, 0.35);
            color: white;
            font-family: Arial, sans-serif;
        }
        .box {
            margin: 40px;
            padding: 30px;
            background: rgba(0, 0, 0, 0.85);
            border: 4px solid lime;
            border-radius: 16px;
            font-size: 32px;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="box">OVERLAY IS CONNECTED</div>
</body>
</html>
"""
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))

        elif self.path == "/tasks":
            self.send_response(200)
            self.send_header("Content-type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(b'{"Emily": ["Test task from server"]}')

        else:
            self.send_response(404)
            self.send_header("Content-type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Not found")


def run_server():
    server_address = ("0.0.0.0", 5000)
    httpd = HTTPServer(server_address, TaskServer)
    print("Server running on port 5000")
    httpd.serve_forever()


if __name__ == "__main__":
    run_server()