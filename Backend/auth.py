import bcrypt
import os
from flask import Blueprint, request, jsonify, redirect
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from db_users import (
    create_user, get_user_by_email, get_user_by_id,
    get_user_by_google_id, update_last_login
)

load_dotenv()

auth_bp = Blueprint("auth", __name__)
oauth = OAuth()

FRONTEND_URL = "http://localhost:5500/frontend/index.html"


def init_oauth(app):
    oauth.init_app(app)
    oauth.register(
        name="google",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"}
    )


# ─────────────────────────────────────────────
# Register
# ─────────────────────────────────────────────
@auth_bp.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json()
    name     = data.get("name", "").strip()
    email    = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()

    if not name or not email or not password:
        return jsonify({"error": "Name, email and password are required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    if "@" not in email:
        return jsonify({"error": "Invalid email address"}), 400

    existing = get_user_by_email(email)
    if existing:
        return jsonify({"error": "Email already registered"}), 409

    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user   = create_user(name, email, hashed, auth_type="email")

    if not user:
        return jsonify({"error": "Registration failed. Please try again."}), 500

    token = create_access_token(identity=str(user["id"]))
    return jsonify({
        "message": "Registration successful",
        "token": token,
        "user": {
            "id":     user["id"],
            "name":   user["name"],
            "email":  user["email"],
            "avatar": user.get("avatar")
        }
    }), 201


# ─────────────────────────────────────────────
# Login
# ─────────────────────────────────────────────
@auth_bp.route("/api/auth/login", methods=["POST"])
def login():
    data     = request.get_json()
    email    = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    user = get_user_by_email(email)
    if not user:
        return jsonify({"error": "Invalid email or password"}), 401

    if user["auth_type"] == "google":
        return jsonify({"error": "This account uses Google login"}), 401

    if not bcrypt.checkpw(password.encode("utf-8"), user["password"].encode("utf-8")):
        return jsonify({"error": "Invalid email or password"}), 401

    update_last_login(user["id"])
    token = create_access_token(identity=str(user["id"]))

    return jsonify({
        "message": "Login successful",
        "token": token,
        "user": {
            "id":     user["id"],
            "name":   user["name"],
            "email":  user["email"],
            "avatar": user.get("avatar")
        }
    })


# ─────────────────────────────────────────────
# Google OAuth — redirect to Google
# ─────────────────────────────────────────────
@auth_bp.route("/api/auth/google")
def google_login():
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    return oauth.google.authorize_redirect(redirect_uri)


# ─────────────────────────────────────────────
# Google OAuth — callback
# ─────────────────────────────────────────────
@auth_bp.route("/api/auth/google/callback")
def google_callback():
    try:
        token     = oauth.google.authorize_access_token()
        user_info = token.get("userinfo")

        if not user_info:
            return redirect(f"{FRONTEND_URL}?error=oauth_failed")

        google_id = user_info["sub"]
        email     = user_info["email"]
        name      = user_info.get("name", email.split("@")[0])
        avatar    = user_info.get("picture")

        user = get_user_by_google_id(google_id)
        if not user:
            user = get_user_by_email(email)
        if not user:
            user = create_user(
                name=name, email=email,
                hashed_password=None, auth_type="google",
                google_id=google_id, avatar=avatar
            )

        update_last_login(user["id"])
        jwt_token = create_access_token(identity=str(user["id"]))

        return redirect(f"{FRONTEND_URL}?token={jwt_token}&name={name}&avatar={avatar or ''}")

    except Exception as e:
        return redirect(f"{FRONTEND_URL}?error={str(e)}")


# ─────────────────────────────────────────────
# Get current user
# ─────────────────────────────────────────────
@auth_bp.route("/api/auth/me", methods=["GET"])
@jwt_required()
def get_me():
    user_id = get_jwt_identity()
    user    = get_user_by_id(int(user_id))
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({
        "id":         user["id"],
        "name":       user["name"],
        "email":      user["email"],
        "avatar":     user.get("avatar"),
        "auth_type":  user["auth_type"],
        "created_at": str(user["created_at"])
    })


# ─────────────────────────────────────────────
# Logout
# ─────────────────────────────────────────────
@auth_bp.route("/api/auth/logout", methods=["POST"])
@jwt_required()
def logout():
    return jsonify({"message": "Logged out successfully"})