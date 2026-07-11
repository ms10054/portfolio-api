import os
import re
import uuid
from functools import wraps
from datetime import datetime, timezone

from flask import jsonify, current_app, request
from flask_jwt_extended import get_jwt_identity
from werkzeug.utils import secure_filename

from extensions import db
from models import User, ActivityLog

# ── Regex patterns ────────────────────────────────────────────────────────────
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
URL_RE = re.compile(r"^(https?://).+", re.IGNORECASE)


# ── String validation ─────────────────────────────────────────────────────────

def is_valid_email(email):
    return bool(email and EMAIL_RE.match(email))


def clean_string(value, max_length=None, required=False, field_name="field"):
    if value is None:
        if required:
            raise ValueError(f"{field_name} is required")
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    value = value.strip()
    if required and not value:
        raise ValueError(f"{field_name} is required")
    if max_length and len(value) > max_length:
        raise ValueError(f"{field_name} must be at most {max_length} characters")
    return value


def validate_url_or_none(value, field_name):
    value = clean_string(value, max_length=255, field_name=field_name)
    if not value:
        return None
    if not URL_RE.match(value):
        raise ValueError(f"{field_name} must start with http:// or https://")
    return value


def validate_password_strength(password):
    """
    Enforce password rules:
    - At least 8 characters
    - At least one letter
    - At least one digit
    Returns an error string or None if valid.
    """
    if not isinstance(password, str) or len(password) < 8:
        return "password must be at least 8 characters"
    if not any(c.isalpha() for c in password):
        return "password must contain at least one letter"
    if not any(c.isdigit() for c in password):
        return "password must contain at least one number"
    return None


def parse_positive_int(value, default, max_value=100):
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    if number < 1:
        number = default
    return min(number, max_value)


def pagination_meta(pagination):
    return {
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
    }


# ── Role-based access ─────────────────────────────────────────────────────────

def admin_required(fn):
    """Decorator: restricts endpoint to admin users only."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user or user.role != "admin":
            return jsonify({"error": "admin permission required"}), 403
        return fn(*args, **kwargs)
    return wrapper


# ── Activity logging ──────────────────────────────────────────────────────────

def log_activity(user_id, action, description=None, resource_type=None, resource_id=None):
    log = ActivityLog(
        user_id=user_id,
        action=action,
        description=description,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=request.headers.get("X-Forwarded-For", request.remote_addr),
        user_agent=request.headers.get("User-Agent"),
    )
    db.session.add(log)


# ── Image upload & processing ─────────────────────────────────────────────────

def allowed_image(filename):
    allowed = current_app.config.get("ALLOWED_IMAGE_EXTENSIONS", {"png","jpg","jpeg","gif","webp"})
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


def save_uploaded_image(file_storage, folder_name):
    """
    Validate, resize, and save an uploaded image.
    Returns a publicly accessible URL path like /uploads/profiles/abc123.jpg
    Raises ValueError with a user-friendly message on any problem.
    """
    if not file_storage or not file_storage.filename:
        raise ValueError("image file is required")
    if not allowed_image(file_storage.filename):
        raise ValueError("only png, jpg, jpeg, gif, and webp files are allowed")

    original_name = secure_filename(file_storage.filename)
    ext = original_name.rsplit(".", 1)[1].lower()
    safe_name = f"{uuid.uuid4().hex}.{ext}"

    upload_root = current_app.config["UPLOAD_FOLDER"]
    target_folder = os.path.join(upload_root, folder_name)
    os.makedirs(target_folder, exist_ok=True)
    file_path = os.path.join(target_folder, safe_name)

    # Resize image to max dimension to save storage and improve performance
    try:
        from PIL import Image
        max_dim = current_app.config.get("IMAGE_MAX_DIMENSION", 1024)
        img = Image.open(file_storage)
        img.thumbnail((max_dim, max_dim))
        # Convert palette/RGBA to RGB for JPEGs
        if ext in ("jpg", "jpeg") and img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.save(file_path, optimize=True, quality=85)
    except Exception:
        # Fallback: save raw without processing
        file_storage.seek(0)
        file_storage.save(file_path)

    return f"/uploads/{folder_name}/{safe_name}"


def delete_old_image(url_path):
    """Delete an old image file from disk when replaced."""
    if not url_path:
        return
    try:
        upload_root = current_app.config["UPLOAD_FOLDER"]
        # url_path is like /uploads/profiles/abc.jpg
        relative = url_path.lstrip("/uploads/")
        full_path = os.path.join(upload_root, relative)
        if os.path.exists(full_path):
            os.remove(full_path)
    except Exception:
        pass  # Non-critical — don't break the request if cleanup fails
