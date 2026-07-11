from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db, cache
from models import Portfolio
from utils import (
    clean_string, save_uploaded_image, delete_old_image,
    log_activity, validate_url_or_none,
)

portfolio_bp = Blueprint("portfolio", __name__, url_prefix="/api/portfolio")


@portfolio_bp.route("", methods=["GET"])
@jwt_required()
@cache.cached(timeout=30, key_prefix=lambda: f"portfolio_{get_jwt_identity()}")
def get_portfolio():
    """
    Get the current user's portfolio information.
    ---
    tags: [Portfolio]
    security:
      - Bearer: []
    responses:
      200:
        description: Portfolio info or null if not created yet
    """
    user_id = get_jwt_identity()
    portfolio = Portfolio.query.filter_by(user_id=user_id).first()
    if not portfolio:
        return jsonify({"portfolio": None, "message": "No portfolio created yet"}), 200
    return jsonify({"portfolio": portfolio.to_dict()}), 200


@portfolio_bp.route("", methods=["POST", "PUT"])
@jwt_required()
def upsert_portfolio():
    """
    Create or update portfolio information.
    ---
    tags: [Portfolio]
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        schema:
          properties:
            phone: {type: string, example: "+92-300-1234567"}
            location: {type: string, example: "Karachi, Pakistan"}
            job_title: {type: string, example: "Backend Developer"}
            bio: {type: string}
            education: {type: string}
            career_goals: {type: string}
            github: {type: string, example: "https://github.com/username"}
            linkedin: {type: string, example: "https://linkedin.com/in/username"}
            twitter: {type: string}
            website: {type: string}
    responses:
      200: {description: Portfolio updated}
      201: {description: Portfolio created}
      400: {description: Validation error}
    """
    user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}

    portfolio = Portfolio.query.filter_by(user_id=user_id).first()
    created = portfolio is None

    if not portfolio:
        portfolio = Portfolio(user_id=user_id)
        db.session.add(portfolio)

    simple_fields = {
        "phone": 30,
        "location": 100,
        "job_title": 100,
        "bio": None,
        "education": None,
        "career_goals": None,
    }

    try:
        for field, max_length in simple_fields.items():
            if field in data:
                setattr(portfolio, field, clean_string(data.get(field), max_length=max_length, field_name=field))

        for field in ["github", "linkedin", "twitter", "website"]:
            if field in data:
                setattr(portfolio, field, validate_url_or_none(data.get(field), field))
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    db.session.flush()
    action = "profile_created" if created else "profile_updated"
    log_activity(user_id, action, "Portfolio profile was changed", "portfolio", portfolio.id)
    db.session.commit()

    # Invalidate cache
    cache.delete(f"portfolio_{user_id}")

    status = 201 if created else 200
    msg = "portfolio created successfully" if created else "portfolio updated successfully"
    return jsonify({"message": msg, "portfolio": portfolio.to_dict()}), status


@portfolio_bp.route("/profile-image", methods=["POST"])
@jwt_required()
def upload_profile_image():
    """
    Upload or replace the current user's profile image.
    ---
    tags: [Portfolio]
    security:
      - Bearer: []
    consumes:
      - multipart/form-data
    parameters:
      - in: formData
        name: image
        type: file
        required: true
        description: Image file (png, jpg, jpeg, gif, webp — max 5MB)
    responses:
      200: {description: Profile image uploaded}
      400: {description: Invalid file}
    """
    user_id = get_jwt_identity()
    portfolio = Portfolio.query.filter_by(user_id=user_id).first()
    if not portfolio:
        portfolio = Portfolio(user_id=user_id)
        db.session.add(portfolio)

    # Delete old image before saving new one
    old_image = portfolio.profile_image
    try:
        portfolio.profile_image = save_uploaded_image(request.files.get("image"), "profiles")
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    delete_old_image(old_image)

    db.session.flush()
    log_activity(user_id, "profile_image_uploaded", "Uploaded profile image", "portfolio", portfolio.id)
    db.session.commit()
    cache.delete(f"portfolio_{user_id}")

    return jsonify({
        "message": "profile image uploaded successfully",
        "image_url": portfolio.profile_image,
        "portfolio": portfolio.to_dict(),
    }), 200
