from pathlib import Path

main_py = r'''"""
YT Downloader backend — NO FLASK

Run:
    python main.py

Then open:
    http://127.0.0.1:8000

This server is designed to work with the separate index.html frontend.
Requirements:
    pip install yt-dlp
    Install FFmpeg and make sure it is available in PATH.
"""

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from pathlib import Path

import yt_dlp


HOST = "127.0.0.1"
PORT = 8000
BASE_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = Path.home() / "Downloads"

QUALITY_OPTIONS = {
    "best": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    "1080": "bestvideo[height<=1080][height>=1080]+bestaudio/best[height<=1080]",
    "720": "bestvideo[height<=720]+bestaudio/best[height<=720]",
    "480": "bestvideo[height<=480]+bestaudio/best[height<=480]",
    "audio": "bestaudio/best",
}


class Handler(BaseHTTPRequestHandler):

    def send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path

        # Health check
        if path == "/api/status":
            self.send_json({
                "ok": True,
                "message": "YT Downloader backend is running"
            })
            return

        # Serve index.html from the same folder
        if path in ("/", "/index.html"):
            index_file = BASE_DIR / "index.html"

            if not index_file.exists():
                self.send_error(404, "index.html not found")
                return

            try:
                data = index_file.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except Exception as exc:
                self.send_error(500, str(exc))
            return

        self.send_error(404, "Not found")

    def do_POST(self):
        path = urlparse(self.path).path

        if path != "/api/download":
            self.send_json({"ok": False, "error": "Unknown API endpoint"}, 404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            data = json.loads(raw.decode("utf-8"))

            url = str(data.get("url", "")).strip()
            quality = str(data.get("quality", "best")).strip()

            if not url:
                self.send_json({
                    "ok": False,
                    "error": "YouTube URL is required"
                }, 400)
                return

            if quality not in QUALITY_OPTIONS:
                quality = "best"

            # Keep downloads inside the user's Downloads folder.
            DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

            result = download_video(url, quality)

            self.send_json({
                "ok": True,
                "message": "Download completed",
                "file": result
            })

        except json.JSONDecodeError:
            self.send_json({
                "ok": False,
                "error": "Invalid JSON request"
            }, 400)

        except Exception as exc:
            self.send_json({
                "ok": False,
                "error": str(exc)
            }, 500)

    def log_message(self, format, *args):
        print("[SERVER]", format % args)


def download_video(url, quality):
    """
    Uses the same yt-dlp approach as the original desktop downloader,
    but without Tkinter.
    """

    is_audio = quality == "audio"

    options = {
        "format": QUALITY_OPTIONS[quality],
        "outtmpl": str(DOWNLOAD_DIR / "%(title)s.%(ext)s"),
        "noplaylist": True,
        "quiet": False,
        "merge_output_format": "mp4",
    }

    if is_audio:
        options["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
        options.pop("merge_output_format", None)

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)

        if is_audio:
            filename = str(Path(filename).with_suffix(".mp3"))
        elif info.get("requested_downloads"):
            # yt-dlp may merge video/audio into an mp4.
            filename = str(Path(filename).with_suffix(".mp4"))

    return filename


def main():
    print("=" * 55)
    print("YT Downloader - Python backend (NO FLASK)")
    print("=" * 55)
    print(f"Server: http://{HOST}:{PORT}")
    print(f"Downloads: {DOWNLOAD_DIR}")
    print("Press Ctrl+C to stop.")
    print("=" * 55)

    server = ThreadingHTTPServer((HOST, PORT), Handler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
'''

path = Path("/mnt/data/main.py")
path.write_text(main_py, encoding="utf-8")
print(path)
