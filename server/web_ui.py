import json
from flask import Flask, Response, jsonify, render_template, request
import bridge
import database

app = Flask(__name__, template_folder="templates", static_folder="static")


# ── Pages ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ── Stats & feed ──────────────────────────────────────────────────────────────

@app.route("/api/stats")
def api_stats():
    return jsonify(database.get_stats())


@app.route("/api/recent")
def api_recent():
    limit = request.args.get("limit", 200, type=int)
    return jsonify(database.get_recent_queries(limit))


@app.route("/api/top-talkers")
def api_top_talkers():
    rows = database.get_top_talkers(10)
    return jsonify([{"src": r[0], "count": r[1]} for r in rows])


# ── SSE stream ────────────────────────────────────────────────────────────────

def _event_stream():
    """
    Blocks on the queue — zero CPU, zero latency.
    Sends a keepalive ping every 15 seconds if no events arrive.
    """
    while True:
        try:
            item = bridge.live_traffic_queue.get(timeout=15)
            yield f"data: {json.dumps(item)}\n\n"
        except Exception:
            yield ": ping\n\n"   # keepalive — prevents browser from closing SSE


@app.route("/stream")
def stream():
    return Response(
        _event_stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── Blocklist ─────────────────────────────────────────────────────────────────

@app.route("/api/blocklist", methods=["GET"])
def api_blocklist_get():
    return jsonify(database.get_all_blocked_domains())


@app.route("/api/blocklist", methods=["POST"])
def api_blocklist_add():
    data   = request.get_json(silent=True) or {}
    domain = (data.get("domain") or "").strip().lower()

    if not domain:
        return jsonify({"success": False, "message": "Missing domain"}), 400

    added = database.add_to_blocklist(domain)
    if added:
        return jsonify({"success": True,  "message": f"Blocked {domain}"})
    else:
        return jsonify({"success": False, "message": f"{domain} is already blocked"}), 409


@app.route("/api/blocklist", methods=["DELETE"])
def api_blocklist_delete():
    data   = request.get_json(silent=True) or {}
    domain = (data.get("domain") or "").strip().lower()

    if not domain:
        return jsonify({"success": False, "message": "Missing domain"}), 400

    removed = database.remove_from_blocklist(domain)
    if removed:
        return jsonify({"success": True,  "message": f"Unblocked {domain}"})
    else:
        return jsonify({"success": False, "message": f"{domain} not found"}), 404


# ── Demo ──────────────────────────────────────────────────────────────────────

@app.route("/api/demo/populate", methods=["POST"])
def api_demo_populate():
    samples = [
        {"type": "QUERY",  "src": "192.168.1.10", "dst": "1.1.1.1", "domain": "youtube.com"},
        {"type": "QUERY",  "src": "192.168.1.11", "dst": "1.1.1.1", "domain": "api.whatsapp.com"},
        {"type": "QUERY",  "src": "192.168.1.10", "dst": "1.1.1.1", "domain": "ads.doubleclick.net"},
        {"type": "ANSWER", "src": "1.1.1.1",       "dst": "192.168.1.10", "data": "142.250.80.46"},
    ]
    for item in samples:
        database.insert_data(item)

    database.add_to_blocklist("ads.doubleclick.net")

    return jsonify({"success": True, "message": "Demo data inserted"})


# ── Entry point ───────────────────────────────────────────────────────────────

def run_server(host="0.0.0.0", port=5000):
    import logging

    # Silence Werkzeug's access logs (HTTP requests) while keeping errors visible
    werkzeug_logger = logging.getLogger("werkzeug")
    werkzeug_logger.setLevel(logging.ERROR)
    werkzeug_logger.propagate = False

    # Reduce Flask's own logger noise (optional)
    flask_logger = logging.getLogger("flask.app")
    flask_logger.setLevel(logging.ERROR)
    flask_logger.propagate = False

    # Disable the Flask app logger to avoid duplicate messages on some setups
    app.logger.disabled = True

    app.run(host=host, port=port, threaded=True, use_reloader=False)


if __name__ == "__main__":
    run_server()