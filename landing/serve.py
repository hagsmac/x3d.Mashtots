#!/usr/bin/env python3
"""Static server for the Landing with caching off (the generator rewrites textures while you inspect stills) and byte ranges on
(a browser can only seek inside an audio file it has fully downloaded unless the server answers Range requests; the page seeks the score whenever you click a section).
usage: python3 serve.py [port]"""
import http.server, sys, functools, os, re

class H(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, max-age=0")
        if not getattr(self, "_partial", False): self.send_header("Accept-Ranges", "bytes")
        super().end_headers()
    def log_message(self, *a): pass
    def send_head(self):
        self._partial = False; self._left = None
        rng = self.headers.get("Range"); path = self.translate_path(self.path)
        m = re.match(r"bytes=(\d*)-(\d*)$", (rng or "").strip())
        if not m or not os.path.isfile(path) or (m.group(1) == "" and m.group(2) == ""): return super().send_head()
        size = os.path.getsize(path)
        start, end = (max(0, size - int(m.group(2))), size - 1) if m.group(1) == "" else (int(m.group(1)), int(m.group(2)) if m.group(2) else size - 1)
        end = min(end, size - 1)
        if start > end:
            self.send_error(416, "Requested Range Not Satisfiable"); return None
        f = open(path, "rb"); f.seek(start); self._partial = True; self._left = end - start + 1
        self.send_response(206); self.send_header("Content-Type", self.guess_type(path)); self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Range", "bytes %d-%d/%d" % (start, end, size)); self.send_header("Content-Length", str(self._left)); self.end_headers()
        return f
    def copyfile(self, source, outputfile):
        left = getattr(self, "_left", None)
        if left is None: return super().copyfile(source, outputfile)
        while left > 0:
            chunk = source.read(min(65536, left))
            if not chunk: break
            outputfile.write(chunk); left -= len(chunk)

port = int(sys.argv[1]) if len(sys.argv) > 1 else 8794
http.server.ThreadingHTTPServer(("127.0.0.1", port), functools.partial(H, directory=".")).serve_forever()
