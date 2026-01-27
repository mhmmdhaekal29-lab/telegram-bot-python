try:
    from flask import Flask, render_template, request, jsonify
    from core import get_bot_reply
    FLASK_AVAILABLE = True
except Exception:
    FLASK_AVAILABLE = False


if FLASK_AVAILABLE:
    app = Flask(__name__)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/chat", methods=["POST"])
    def chat():
        data = request.get_json() or {}
        user_message = data.get("message", "")
        reply = get_bot_reply(user_message)
        return jsonify({"reply": reply})

    if __name__ == "__main__":
        # debug=True supaya mudah melihat error saat pengembangan
        app.run(debug=True)
else:
    # Lightweight fallback server so the app can run without Flask
    import json
    from http.server import HTTPServer, BaseHTTPRequestHandler
    from pathlib import Path
    from urllib.parse import urlparse

    BASE_DIR = Path(__file__).resolve().parent
    TEMPLATES_DIR = BASE_DIR / "templates"
    INDEX_FILE = TEMPLATES_DIR / "index.html"

    # import core module (safe relative import)
    from core import get_bot_reply as _get_bot_reply


    class SimpleHandler(BaseHTTPRequestHandler):
        def _send_text(self, data: bytes, status=200, content_type="text/html; charset=utf-8"):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == "/" or parsed.path == "/index.html":
                try:
                    with INDEX_FILE.open("rb") as f:
                        self._send_text(f.read(), content_type="text/html; charset=utf-8")
                except FileNotFoundError:
                    self.send_error(404, "index.html not found")
            else:
                self.send_error(404)

        def do_POST(self):
            parsed = urlparse(self.path)
            if parsed.path == "/chat":
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode("utf-8") if length else ""
                try:
                    data = json.loads(body) if body else {}
                except Exception:
                    data = {}
                user_message = data.get("message", "")
                reply = _get_bot_reply(user_message)
                resp = json.dumps({"reply": reply}, ensure_ascii=False).encode("utf-8")
                self._send_text(resp, content_type="application/json; charset=utf-8")
            else:
                self.send_error(404)


    def run_no_flask(host="0.0.0.0", port=5000):
        server = HTTPServer((host, port), SimpleHandler)
        print(f"Serving on http://127.0.0.1:{port} (fallback, Flask not available)")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            server.server_close()


    if __name__ == "__main__":
        run_no_flask()