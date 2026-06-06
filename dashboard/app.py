import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, ".env"))

from flask import Flask, jsonify, render_template, request
from database import Database, VALID_STATUSES

app = Flask(__name__)
db = Database(path=os.path.join(ROOT, os.getenv("DATABASE_PATH", "data/applications.db")))


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/data")
def api_data():
    jobs = db.get_jobs(limit=100)
    status_counts = db.get_job_status_counts()
    return jsonify({
        "jobs": jobs,
        "stats": {
            "total_jobs": len(jobs),
            "by_status": status_counts,
        },
    })


@app.route("/api/jobs/<int:job_id>/status", methods=["POST"])
def set_job_status(job_id):
    body = request.get_json(silent=True) or {}
    status = body.get("status", "").strip()
    if status not in VALID_STATUSES:
        return jsonify({"error": f"Invalid status. Must be one of: {sorted(VALID_STATUSES)}"}), 400
    try:
        db.update_job_status(job_id, status)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"ok": True, "job_id": job_id, "status": status})


if __name__ == "__main__":
    port = int(os.getenv("DASHBOARD_PORT", 8080))
    print(f"Dashboard running at http://localhost:{port}")
    app.run(debug=True, port=port, use_reloader=False)
