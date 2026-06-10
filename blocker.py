import random
from datetime import datetime
from flask import Flask, request, jsonify, session, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)
app.secret_key = "shieldai-secret-2024"

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["100 per day", "10 per minute"],
    storage_uri="memory://"
)

AI_BOTS = [
    "GPTBot", "ClaudeBot", "Google-Extended",
    "CCBot", "anthropic-ai", "cohere-ai",
    "Bytespider", "Amazonbot",
]

BLOCKED_IPS = []
REQUEST_LOGS = []
STATS = {
    "total_requests": 0,
    "bots_blocked": 0,
    "ips_blocked": 0,
    "humans_allowed": 0
}

def is_ai_bot(user_agent):
    if not user_agent:
        return True
    for bot in AI_BOTS:
        if bot.lower() in user_agent.lower():
            return True
    return False

def is_blocked_ip(ip):
    return ip in BLOCKED_IPS

def log_request(ip, user_agent, status):
    STATS["total_requests"] += 1
    if status == "blocked":
        STATS["bots_blocked"] += 1
    else:
        STATS["humans_allowed"] += 1
    REQUEST_LOGS.append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "ip": ip,
        "user_agent": user_agent,
        "status": status
    })
    if len(REQUEST_LOGS) > 50:
        REQUEST_LOGS.pop(0)

@app.before_request
def check_request():
    client_ip = request.remote_addr
    user_agent = request.headers.get("User-Agent", "")
    skip_paths = ["/block-ip", "/blocked-ips", "/challenge",
                  "/verify-challenge", "/dashboard", "/api/stats"]
    if request.path in skip_paths:
        return None
    if is_blocked_ip(client_ip):
        log_request(client_ip, user_agent, "blocked")
        return jsonify({
            "error": "Access denied",
            "message": f"IP {client_ip} is permanently blocked 🚫"
        }), 403
    if is_ai_bot(user_agent):
        log_request(client_ip, user_agent, "blocked")
        return jsonify({
            "error": "Access denied",
            "message": "AI bots not allowed 🚫"
        }), 403
    log_request(client_ip, user_agent, "allowed")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/api/stats")
def api_stats():
    return jsonify({
        "total_requests": STATS["total_requests"],
        "bots_blocked": STATS["bots_blocked"],
        "ips_blocked": len(BLOCKED_IPS),
        "humans_allowed": STATS["humans_allowed"],
        "recent_logs": REQUEST_LOGS[-10:]
    })

@app.route("/")
@limiter.limit("10 per minute")
def home():
    return jsonify({
        "message": "Welcome! You are human ✅",
        "your_ip": request.remote_addr
    })

@app.route("/about")
def about():
    return jsonify({"message": "About page — protected! 🛡️"})

@app.route("/products")
def products():
    return jsonify({"message": "Products page — protected! 🛡️"})

@app.route("/challenge")
def get_challenge():
    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    session["challenge_answer"] = str(num1 + num2)
    return jsonify({
        "question": f"What is {num1} + {num2}?",
        "hint": "Solve this to prove you are human"
    })

@app.route("/verify-challenge", methods=["POST"])
def verify_challenge():
    data = request.get_json()
    user_answer = str(data.get("answer", ""))
    correct_answer = session.get("challenge_answer", "")
    if user_answer == correct_answer:
        session["verified"] = True
        return jsonify({
            "message": "Challenge passed! You are human ✅",
            "verified": True
        })
    return jsonify({
        "message": "Wrong answer! Bot detected 🚫",
        "verified": False
    }), 403

@app.route("/block-ip", methods=["POST"])
def block_ip():
    data = request.get_json()
    ip = data.get("ip")
    if not ip:
        return jsonify({"error": "No IP provided"}), 400
    if ip not in BLOCKED_IPS:
        BLOCKED_IPS.append(ip)
        STATS["ips_blocked"] += 1
        return jsonify({
            "message": f"IP {ip} has been blocked ✅",
            "total_blocked": len(BLOCKED_IPS)
        })
    return jsonify({"message": f"IP {ip} already blocked"})

@app.route("/blocked-ips")
def get_blocked_ips():
    return jsonify({
        "blocked_ips": BLOCKED_IPS,
        "total": len(BLOCKED_IPS)
    })

@app.errorhandler(429)
def rate_limit_exceeded(e):
    return jsonify({
        "error": "Too many requests",
        "message": "Slow down! Rate limited 🚫"
    }), 429

if __name__ == "__main__":
    app.run(debug=True)