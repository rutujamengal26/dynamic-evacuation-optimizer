"""Serve EvacuateLab locally using only Python's standard library.

Usage: python serve.py [--port 8000]
Open http://127.0.0.1:8000 in your browser. No data is uploaded.
"""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import argparse
import os

ROOT = Path(__file__).resolve().parent

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def log_message(self, fmt, *args):
        print(f"[{self.log_date_time_string()}] {fmt % args}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the EvacuateLab local web UI")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    os.chdir(ROOT)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"EvacuateLab is running at http://127.0.0.1:{args.port}")
    print("Press Ctrl+C to stop. The app runs locally in your browser.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down EvacuateLab…")
    finally:
        server.server_close()
