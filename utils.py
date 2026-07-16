import os
import re
import uuid
from functools import wraps

from flask import jsonify, current_app, request
from flask_jwt_extended import get_jwt_identity
from werkzeug.utils import secure_filename

from extensions import db
from models import User, ActivityLog

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
URL_RE = re.compile(r"^https?://[^\s]+$", re.IGNORECASE)
CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def is_valid_email(email):
    return bool(email and EMAIL_RE.fullmatch(email))


def clean_string(value, max_length=None, required=False, field_name="field"):
    if value is None:
        if required:
            raise ValueError(f"{field_name} is required")
        return None

    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")

    value = CONTROL_CHARS_RE.sub("", value).strip()

    if required and not value:
        raise ValueError(f"{field_name} is required")

    if max_length and len(value) > max_length:
        raise ValueError(
            f"{field_name} must be at most {max_length} characters"
        )

    return value


def validate_url_or_none(value, field_name):
    value = clean_string(
        value,
        max_length=255,
        field_name=field_name
    )

    if not value:
        return None

    if not URL_RE.fullmatch(value):
        raise ValueError(
            f"{field_name} must be a valid http:// or https:// URL"
        )

    return value


def validate_password_strength(password):
    if not isinstance(password, str) or len(password) < 8:
        return "password must be at least 8 characters"

    if len(password) > 128:
        return "password must be at most 128 characters"

    if not any(character.isalpha() for character in password):
        return "password must contain at least one letter"

    if not any(character.isdigit() for character in password):
        return "password must contain at least one number"

    return None


def require_json_object():
    if not request.is_json:
        raise ValueError(
            "Content-Type must be application/json"
        )

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        raise ValueError(
            "request body must be a JSON object"
        )

    return data


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


def admin_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        user = db.session.get(
            User,
            int(get_jwt_identity())
        )

        if not user or user.role != "admin":
            return jsonify({
                "error": "admin permission required"
            }), 403

        return function(*args, **kwargs)

    return wrapper


def log_activity(
    user_id,
    action,
    description=None,
    resource_type=None,
    resource_id=None
):
    forwarded = request.headers.get(
        "X-Forwarded-For",
        ""
    )

    ip_address = (
        forwarded.split(",")[0].strip()
        if forwarded
        else request.remote_addr
    )

    db.session.add(
        ActivityLog(
            user_id=int(user_id),
            action=action,
            description=description,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=(
                request.headers.get("User-Agent") or ""
            )[:255],
        )
    )


def allowed_image(filename):
    allowed_extensions = current_app.config.get(
        "ALLOWED_IMAGE_EXTENSIONS",
        set()
    )

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in allowed_extensions
    )


def save_uploaded_image(file_storage, folder_name):
    if not file_storage or not file_storage.filename:
        raise ValueError("image file is required")

    if not allowed_image(file_storage.filename):
        raise ValueError(
            "only png, jpg, jpeg, gif, and webp files are allowed"
        )

    original_name = secure_filename(
        file_storage.filename
    )

    extension = original_name.rsplit(
        ".",
        1
    )[1].lower()

    safe_name = (
        f"{uuid.uuid4().hex}.{extension}"
    )

    target_folder = os.path.join(
        current_app.config["UPLOAD_FOLDER"],
        folder_name
    )

    os.makedirs(
        target_folder,
        exist_ok=True
    )

    file_path = os.path.join(
        target_folder,
        safe_name
    )

    try:
        from PIL import Image, UnidentifiedImageError

        file_storage.stream.seek(0)

        with Image.open(file_storage.stream) as image:
            image.verify()

        file_storage.stream.seek(0)

        with Image.open(file_storage.stream) as image:
            maximum_dimension = current_app.config.get(
                "IMAGE_MAX_DIMENSION",
                1024
            )

            image.thumbnail(
                (
                    maximum_dimension,
                    maximum_dimension
                )
            )

            if (
                extension in ("jpg", "jpeg")
                and image.mode not in ("RGB", "L")
            ):
                image = image.convert("RGB")

            image.save(
                file_path,
                optimize=True,
                quality=85
            )

    except (
        UnidentifiedImageError,
        OSError,
        ValueError
    ) as error:
        if os.path.exists(file_path):
            os.remove(file_path)

        raise ValueError(
            "uploaded file is not a valid image"
        ) from error

    return (
        f"/uploads/{folder_name}/{safe_name}"
    )


def delete_old_image(url_path):
    if (
        not url_path
        or not url_path.startswith("/uploads/")
    ):
        return

    try:
        relative_path = url_path[
            len("/uploads/"):
        ]

        upload_root = os.path.realpath(
            current_app.config["UPLOAD_FOLDER"]
        )

        full_path = os.path.realpath(
            os.path.join(
                upload_root,
                relative_path
            )
        )

        if (
            full_path.startswith(
                upload_root + os.sep
            )
            and os.path.isfile(full_path)
        ):
            os.remove(full_path)

    except OSError:
        current_app.logger.warning(
            "Could not delete old image: %s",
            url_path
        )