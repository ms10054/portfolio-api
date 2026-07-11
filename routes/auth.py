from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity, get_jwt,
)
from extensions import db
from models import User
from utils import is_valid_email, clean_string, log_activity, admin_required, validate_password_strength

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")
TOKEN_BLOCKLIST = set()


@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Register a new user account.
    ---
    tags: [Auth]
    parameters:
      - in: body
        name: body
        required: true
        schema:
          required: [name, email, password]
          properties:
            name: {type: string, example: "Muhammad Saad"}
            email: {type: string, example: "saad@gmail.com"}
            password: {type: string, example: "password1", description: "Min 8 chars, 1 letter, 1 number"}
            role: {type: string, example: "user", description: "user or admin"}
            admin_secret: {type: string, description: "Required only when role=admin"}
    responses:
      201: {description: User registered successfully}
      400: {description: Validation error}
      409: {description: Email already exists}
    """
    data = request.get_json(silent=True) or {}

    try:
        name = clean_string(data.get("name"), max_length=100, required=True, field_name="name")
        email = clean_string(data.get("email"), max_length=120, required=True, field_name="email").lower()
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    password = data.get("password", "")
    requested_role = str(data.get("role", "user")).strip().lower()
    admin_secret = str(data.get("admin_secret", ""))

    if not is_valid_email(email):
        return jsonify({"error": "email format is invalid"}), 400

    pwd_error = validate_password_strength(password)
    if pwd_error:
        return jsonify({"error": pwd_error}), 400

    if requested_role not in ["admin", "user"]:
        return jsonify({"error": "role must be admin or user"}), 400

    role = "user"
    if requested_role == "admin":
        expected = current_app.config.get("ADMIN_REGISTRATION_SECRET")
        if not admin_secret or admin_secret != expected:
            return jsonify({"error": "invalid admin secret"}), 403
        role = "admin"

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "a user with this email already exists"}), 409

    user = User(name=name, email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "user registered successfully", "user": user.to_dict()}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Login and receive a JWT access token.
    ---
    tags: [Auth]
    parameters:
      - in: body
        name: body
        required: true
        schema:
          required: [email, password]
          properties:
            email: {type: string, example: "saad@gmail.com"}
            password: {type: string, example: "password1"}
    responses:
      200: {description: Login successful, returns JWT token}
      400: {description: Missing fields}
      401: {description: Invalid credentials}
    """
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "invalid email or password"}), 401

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role},
    )
    log_activity(user.id, "login", "User logged in", "user", user.id)
    db.session.commit()

    return jsonify({
        "message": "login successful",
        "access_token": access_token,
        "user": user.to_dict(),
    }), 200


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    """
    Logout and revoke the current JWT token.
    ---
    tags: [Auth]
    security:
      - Bearer: []
    responses:
      200: {description: Logout successful}
    """
    jti = get_jwt()["jti"]
    TOKEN_BLOCKLIST.add(jti)
    log_activity(get_jwt_identity(), "logout", "User logged out")
    db.session.commit()
    return jsonify({"message": "logout successful"}), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    """
    Get the currently authenticated user's profile.
    ---
    tags: [Auth]
    security:
      - Bearer: []
    responses:
      200: {description: Current user info}
      404: {description: User not found}
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "user not found"}), 404
    return jsonify({"user": user.to_dict()}), 200


@auth_bp.route("/change-password", methods=["PUT"])
@jwt_required()
def change_password():
    """
    Change the current user's password.
    ---
    tags: [Auth]
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          required: [current_password, new_password]
          properties:
            current_password: {type: string}
            new_password: {type: string, description: "Min 8 chars, 1 letter, 1 number"}
    responses:
      200: {description: Password changed}
      400: {description: Validation error}
      401: {description: Wrong current password}
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    data = request.get_json(silent=True) or {}

    current_password = data.get("current_password", "")
    new_password = data.get("new_password", "")

    if not current_password or not new_password:
        return jsonify({"error": "current_password and new_password are required"}), 400
    if not user.check_password(current_password):
        return jsonify({"error": "current password is incorrect"}), 401

    pwd_error = validate_password_strength(new_password)
    if pwd_error:
        return jsonify({"error": pwd_error}), 400

    user.set_password(new_password)
    log_activity(user_id, "change_password", "Password was changed")
    db.session.commit()
    return jsonify({"message": "password changed successfully"}), 200


@auth_bp.route("/users", methods=["GET"])
@jwt_required()
@admin_required
def list_users():
    """
    Admin only: list all registered users.
    ---
    tags: [Auth]
    security:
      - Bearer: []
    responses:
      200: {description: List of all users}
      403: {description: Admin access required}
    """
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify({"users": [u.to_dict() for u in users], "total": len(users)}), 200


@auth_bp.route("/users/<int:user_id>/role", methods=["PUT"])
@jwt_required()
@admin_required
def update_user_role(user_id):
    """
    Admin only: change a user's role.
    ---
    tags: [Auth]
    security:
      - Bearer: []
    parameters:
      - {in: path, name: user_id, type: integer, required: true}
      - in: body
        name: body
        schema:
          required: [role]
          properties:
            role: {type: string, example: "admin", description: "admin or user"}
    responses:
      200: {description: Role updated}
      400: {description: Invalid role}
      404: {description: User not found}
    """
    data = request.get_json(silent=True) or {}
    role = data.get("role", "").strip().lower()
    if role not in ["admin", "user"]:
        return jsonify({"error": "role must be admin or user"}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "user not found"}), 404

    user.role = role
    log_activity(get_jwt_identity(), "role_update", f"Changed user {user_id} role to {role}", "user", user_id)
    db.session.commit()
    return jsonify({"message": "role updated successfully", "user": user.to_dict()}), 200
