from __future__ import annotations

import csv
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict

from flask import Flask, jsonify, render_template, request, send_from_directory

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
RECORD_DIR = BASE_DIR / "record"


def ensure_record_dir() -> None:
    RECORD_DIR.mkdir(parents=True, exist_ok=True)


@app.route("/")
def index():
    return render_template("client.html")


@app.route("/health")
def health():
    return jsonify({"ok": True, "message": "server is running"})


@app.route("/save_quiz", methods=["POST"])
def save_quiz():
    ensure_record_dir()

    data = request.get_json(force=True)
    session_id = str(data.get("session_id", "unknown_session"))

    filename = f"quiz_{session_id}.json"
    filepath = RECORD_DIR / filename

    with filepath.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return jsonify({
        "success": True,
        "message": "quiz saved",
        "session_id": session_id,
        "filepath": str(filepath.name),
    })


@app.route("/save_eeg", methods=["POST"])
def save_eeg():
    ensure_record_dir()

    data = request.get_json(force=True)
    session_id = str(data.get("session_id", "unknown_session"))
    eeg_records = data.get("eeg_records", [])

    filename = f"eeg_{session_id}.csv"
    filepath = RECORD_DIR / filename

    with filepath.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "session_id",
            "timestamp_iso",
            "timestamp_ms_epoch",
            "timestamp_ms_since_exam_start",
            "ch1_raw",
            "ch2_raw",
            "ch1_uV",
            "ch2_uV",
        ])

        for r in eeg_records:
            writer.writerow([
                session_id,
                r.get("timestamp_iso", ""),
                r.get("timestamp_ms_epoch", ""),
                r.get("timestamp_ms_since_exam_start", ""),
                r.get("ch1_raw", ""),
                r.get("ch2_raw", ""),
                r.get("ch1_uV", ""),
                r.get("ch2_uV", ""),
            ])

    return jsonify({
        "success": True,
        "message": "eeg saved",
        "session_id": session_id,
        "filepath": str(filepath.name),
    })


@app.route("/records")
def records():
    ensure_record_dir()
    files: List[Dict[str, object]] = []

    for path in sorted(RECORD_DIR.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True):
        if path.is_file():
            stat = path.stat()
            files.append({
                "filename": path.name,
                "size_bytes": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "download_url": f"/records/{path.name}",
            })

    rows = "".join(
        f"<tr><td>{f['filename']}</td><td>{f['size_bytes']}</td><td>{f['modified']}</td>"
        f"<td><a href='{f['download_url']}'>download</a></td></tr>"
        for f in files
    )

    return f"""
    <!doctype html>
    <html lang='ko'>
    <head>
      <meta charset='utf-8'>
      <meta name='viewport' content='width=device-width, initial-scale=1'>
      <title>Saved Records</title>
      <style>
        body {{ font-family: Arial, sans-serif; margin: 30px; background: #f7f7f7; }}
        .card {{ max-width: 1000px; margin: 0 auto; background: white; padding: 24px; border-radius: 12px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 10px; border-bottom: 1px solid #ddd; text-align: left; }}
        a {{ color: #2563eb; }}
      </style>
    </head>
    <body>
      <div class='card'>
        <h1>Saved Records</h1>
        <p><a href='/'>시험 화면으로 돌아가기</a></p>
        <table>
          <thead><tr><th>파일명</th><th>크기(bytes)</th><th>수정 시각</th><th>다운로드</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
    </body>
    </html>
    """


@app.route("/records/<path:filename>")
def download_record(filename: str):
    ensure_record_dir()
    return send_from_directory(RECORD_DIR, filename, as_attachment=True)


if __name__ == "__main__":
    ensure_record_dir()
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
