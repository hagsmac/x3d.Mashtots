#!/usr/bin/env python3
"""Receives one captured frame from capture.html and writes it into the Landing folder (local only, one fixed name).
usage: python3 receive.py 8795   (then open http://127.0.0.1:8794/explore/poster/capture.html)"""
import http.server, os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
ALLOWED = {"poster.jpg"}
class H(http.server.BaseHTTPRequestHandler):
    def cors(self):
        self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1:8794"); self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS"); self.send_header("Access-Control-Allow-Headers", "Content-Type")
    def do_OPTIONS(self): self.send_response(204); self.cors(); self.end_headers()
    def do_POST(self):
        name = self.path.strip("/")
        if name not in ALLOWED: self.send_response(403); self.cors(); self.end_headers(); return
        data = self.rfile.read(int(self.headers["Content-Length"]))
        open(os.path.join(ROOT, name), "wb").write(data)
        self.send_response(200); self.cors(); self.end_headers(); self.wfile.write(f"wrote {name}: {len(data)} bytes".encode())
    def log_message(self, *a): pass
http.server.HTTPServer(("127.0.0.1", int(sys.argv[1]) if len(sys.argv) > 1 else 8795), H).serve_forever()
