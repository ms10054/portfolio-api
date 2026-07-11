from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from models import Skill
from utils import clean_string, parse_positive_int, pagination_meta

skills_bp = Blueprint("skills", __name__, url_prefix="/api/skills")


@skills_bp.route("", methods=["GET"])
@jwt_required()
def get_skills():
    """Get skills for the current user with pagination."""
    user_id = get_jwt_identity()
    page = parse_positive_int(request.args.get("page"), default=1)
    per_page = parse_positive_int(request.args.get("per_page"), default=10, max_value=50)

    pagination = Skill.query.filter_by(user_id=user_id).order_by(
        Skill.category, Skill.name
    ).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "skills": [s.to_dict() for s in pagination.items],
        "pagination": pagination_meta(pagination),
    }), 200


@skills_bp.route("/<int:skill_id>", methods=["GET"])
@jwt_required()
def get_skill(skill_id):
    user_id = get_jwt_identity()
    skill = Skill.query.filter_by(id=skill_id, user_id=user_id).first()
    if not skill:
        return jsonify({"error": "skill not found"}), 404
    return jsonify({"skill": skill.to_dict()}), 200


@skills_bp.route("", methods=["POST"])
@jwt_required()
def create_skill():
    user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}

    try:
        name = clean_string(data.get("name"), max_length=100, required=True, field_name="name")
        category = clean_string(data.get("category"), max_length=100, field_name="category")
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    proficiency = data.get("proficiency", 50)
    if not isinstance(proficiency, int) or not (0 <= proficiency <= 100):
        return jsonify({"error": "proficiency must be an integer between 0 and 100"}), 400

    skill = Skill(name=name, category=category, proficiency=proficiency, user_id=user_id)
    db.session.add(skill)
    db.session.commit()
    return jsonify({"message": "skill created successfully", "skill": skill.to_dict()}), 201


@skills_bp.route("/<int:skill_id>", methods=["PUT", "PATCH"])
@jwt_required()
def update_skill(skill_id):
    user_id = get_jwt_identity()
    skill = Skill.query.filter_by(id=skill_id, user_id=user_id).first()
    if not skill:
        return jsonify({"error": "skill not found"}), 404

    data = request.get_json(silent=True) or {}

    try:
        if "name" in data:
            skill.name = clean_string(data.get("name"), max_length=100, required=True, field_name="name")
        if "category" in data:
            skill.category = clean_string(data.get("category"), max_length=100, field_name="category")
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    if "proficiency" in data:
        proficiency = data["proficiency"]
        if not isinstance(proficiency, int) or not (0 <= proficiency <= 100):
            return jsonify({"error": "proficiency must be an integer between 0 and 100"}), 400
        skill.proficiency = proficiency

    db.session.commit()
    return jsonify({"message": "skill updated successfully", "skill": skill.to_dict()}), 200


@skills_bp.route("/<int:skill_id>", methods=["DELETE"])
@jwt_required()
def delete_skill(skill_id):
    user_id = get_jwt_identity()
    skill = Skill.query.filter_by(id=skill_id, user_id=user_id).first()
    if not skill:
        return jsonify({"error": "skill not found"}), 404

    db.session.delete(skill)
    db.session.commit()
    return jsonify({"message": "skill deleted successfully"}), 200
