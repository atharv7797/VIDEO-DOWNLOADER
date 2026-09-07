"""
YT Downloader — backend

SETUP:
    pip install flask yt-dlp
    Install ffmpeg (needed to merge video+audio):
        Windows: winget install ffmpeg
        Mac:     brew install ffmpeg
        Linux:   sudo apt install ffmpeg

RUN:
    python app.py
Then open http://127.0.0.1:5000 in your browser.
"""

import os
import re
import tempfile
import uuid

from flask import Flask, request, jsonify, send_file, render_template

import yt_dlp

app = Flask(__name__)

DOWNLOAD_DIR = os.path.join(tempfile.gettempdir(), "yt_downloader_tmp")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

QUALITY_FORMATS = {
    "best": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    "1080": "bestvideo[height<=1080][height>=1080]+bestaudio/best[height<=1080]",
    "720": "bestvideo[height<=720]+bestaudio/best[height<=720]",
    "480": "bestvideo[height<=480]+bestaudio/best[height<=480]",
    "audio": "bestaudio/best",
}


def safe_filename(name: str) -> str:
    name = re.sub(r"[^\w\s\-\.]", "", name).strip()
    return re.sub(r"\s+", "_", name)[:80]


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/info")
def info():
    url = request.args.get("url", "").strip()
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    try:
        with yt_dlp.YoutubeDL({"quiet": True, "noplaylist": True}) as ydl:
            data = ydl.extract_info(url, download=False)
        return jsonify({
            "title": data.get("title"),
            "thumbnail": data.get("thumbnail"),
            "duration": data.get("duration"),
            "uploader": data.get("uploader"),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/download")
def download():
    url = request.args.get("url", "").strip()
    quality = request.args.get("quality", "best")
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    if quality not in QUALITY_FORMATS:
        return jsonify({"error": "Invalid quality"}), 400

    job_id = uuid.uuid4().hex
    out_template = os.path.join(DOWNLOAD_DIR, f"{job_id}.%(ext)s")

    ydl_opts = {
        "format": QUALITY_FORMATS[quality],
        "outtmpl": out_template,
        "noplaylist": True,
        "quiet": True,
    }

    is_audio = quality == "audio"
    if is_audio:
        ydl_opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
    else:
        ydl_opts["merge_output_format"] = "mp4"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            title = safe_filename(info_dict.get("title", "video"))

        ext = "mp3" if is_audio else "mp4"
        result_path = os.path.join(DOWNLOAD_DIR, f"{job_id}.{ext}")
        if not os.path.exists(result_path):
            # fall back: find whatever file got produced with this job_id
            matches = [f for f in os.listdir(DOWNLOAD_DIR) if f.startswith(job_id)]
            if not matches:
                return jsonify({"error": "Download produced no file"}), 500
            result_path = os.path.join(DOWNLOAD_DIR, matches[0])
            ext = matches[0].rsplit(".", 1)[-1]

        download_name = f"{title}.{ext}"
        return send_file(result_path, as_attachment=True, download_name=download_name)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
