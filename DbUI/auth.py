from flask import Blueprint, request, redirect, url_for, render_template_string, session, has_request_context
from functools import wraps
from datetime import datetime, timedelta

auth = Blueprint("auth", __name__, url_prefix="/auth")

# Plaintext password
PLAIN_PASSWORD = "harvestking"
LOGIN_DURATION = 300  # 60 seconds from login time

# HTML login template
login_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Login - Shutter Control</title>
    <style>
        body { font-family: Arial; background: #f4f4f4; text-align: center; padding-top: 100px; }
        form { background: white; display: inline-block; padding: 30px; border-radius: 8px; box-shadow: 0 0 10px #ccc; }
        input[type=password] { padding: 10px; width: 80%; margin: 10px 0; }
        input[type=submit] { padding: 10px 20px; background: #007BFF; color: white; border: none; cursor: pointer; }
    </style>
</head>
<body>
    <form method="POST">
        <h2>Enter Access Code</h2>
        <input type="password" name="password" placeholder="Password" required><br>
        <input type="submit" value="Enter">
        {% if error %}<p style="color: red;">{{ error }}</p>{% endif %}
    </form>
</body>
</html>
"""

# Route to log in
@auth.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        password = request.form.get("password")
        if password == PLAIN_PASSWORD:
            session["logged_in"] = True
            session["login_time"] = datetime.utcnow().isoformat()
            return redirect(url_for("index"))
        else:
            error = "Incorrect password"
    return render_template_string(login_template, error=error)

# Route to log out
@auth.route("/logout")
def logout():
    session.pop("logged_in", None)
    session.pop("login_time", None)
    return redirect(url_for("auth.login"))

# Route protection decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function

# Expire the session after 60 seconds from login
@auth.before_app_request
def enforce_session_expiration():
    if not has_request_context():
        return  # Skip for GPIO or background threads

    allowed_paths = [
        "/auth/login",
        "/auth/logout",
        "/static",
        "/favicon.ico"
    ]
    if any(request.path.startswith(p) for p in allowed_paths):
        return

    # If not logged in, redirect to login
    if not session.get("logged_in"):
        return redirect(url_for("auth.login"))

    # Check if 60 seconds have passed since login
    login_time = session.get("login_time")
    if login_time:
        try:
            login_dt = datetime.fromisoformat(login_time)
            if datetime.utcnow() - login_dt > timedelta(seconds=LOGIN_DURATION):
                session.pop("logged_in", None)
                session.pop("login_time", None)
                return redirect(url_for("auth.login"))
        except Exception as e:
            print(f"[AUTH] Error checking login_time: {e}")
            session.pop("logged_in", None)
            session.pop("login_time", None)
            return redirect(url_for("auth.login"))
