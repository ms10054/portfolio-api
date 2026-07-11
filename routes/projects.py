from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_

from extensions import db, cache
from models import Project, PROJECT_CATEGORIES, PROJECT_STATUSES
from utils import (
    clean_string, parse_positive_int, pagination_meta,
    save_uploaded_image, delete_old_image,
    log_activity, validate_url_or_none,
)

projects_bp = Blueprint("projects", __name__, url_prefix="/api/projects")


def current_user_project(project_id):
    return Project.query.filter_by(id=project_id, user_id=get_jwt_identity()).first()


def normalize_technologies(value):
    if value is None:
        return None
    if isinstance(value, list):
        cleaned = [str(t).strip() for t in value if str(t).strip()]
        return ", ".join(cleaned) if cleaned else None
    if isinstance(value, str):
        return value.strip() or None
    raise ValueError("technologies must be a string or array")


@projects_bp.route("", methods=["GET"])
@jwt_required()
def get_projects():
    """
    List projects with search, filter, and pagination.
    ---
    tags: [Projects]
    security:
      - Bearer: []
    parameters:
      - {in: query, name: search, type: string, description: "Search title, description, or technologies"}
      - {in: query, name: category, type: string, description: "Filter by category"}
      - {in: query, name: technology, type: string, description: "Filter by technology"}
      - {in: query, name: status, type: string, description: "Filter by status (planned/in_progress/completed/archived)"}
      - {in: query, name: page, type: integer, default: 1}
      - {in: query, name: per_page, type: integer, default: 10}
    responses:
      200:
        description: Paginated list of projects
        schema:
          properties:
            projects: {type: array}
            pagination: {type: object}
            filters_applied: {type: object}
    """
    user_id = get_jwt_identity()

    # Use select_entity with only needed columns for performance
    query = Project.query.filter_by(user_id=user_id)

    search = request.args.get("search", "").strip()
    category = request.args.get("category", "").strip()
    technology = request.args.get("technology", "").strip()
    status = request.args.get("status", "").strip().lower()

    if search:
        query = query.filter(
            or_(
                Project.title.ilike(f"%{search}%"),
                Project.description.ilike(f"%{search}%"),
                Project.technologies.ilike(f"%{search}%"),
            )
        )
    if category:
        query = query.filter(Project.category.ilike(f"%{category}%"))
    if technology:
        query = query.filter(Project.technologies.ilike(f"%{technology}%"))
    if status:
        query = query.filter(Project.status == status)

    page = parse_positive_int(request.args.get("page"), default=1)
    per_page = parse_positive_int(request.args.get("per_page"), default=10, max_value=50)

    pagination = query.order_by(Project.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        "projects": [p.to_dict() for p in pagination.items],
        "pagination": pagination_meta(pagination),
        "filters_applied": {
            "search": search or None,
            "category": category or None,
            "technology": technology or None,
            "status": status or None,
        },
    }), 200


@projects_bp.route("/categories", methods=["GET"])
@jwt_required()
@cache.cached(timeout=3600, key_prefix="project_categories")
def get_categories():
    """
    Get all available project categories.
    ---
    tags: [Projects]
    security:
      - Bearer: []
    responses:
      200:
        description: List of categories
    """
    return jsonify({"categories": PROJECT_CATEGORIES}), 200


@projects_bp.route("/statuses", methods=["GET"])
@jwt_required()
@cache.cached(timeout=3600, key_prefix="project_statuses")
def get_statuses():
    """
    Get all available project statuses.
    ---
    tags: [Projects]
    security:
      - Bearer: []
    responses:
      200:
        description: List of statuses
    """
    return jsonify({"statuses": PROJECT_STATUSES}), 200


@projects_bp.route("/<int:project_id>", methods=["GET"])
@jwt_required()
def get_project(project_id):
    """
    Get a single project by ID.
    ---
    tags: [Projects]
    security:
      - Bearer: []
    parameters:
      - {in: path, name: project_id, type: integer, required: true}
    responses:
      200: {description: Project details}
      404: {description: Project not found}
    """
    project = current_user_project(project_id)
    if not project:
        return jsonify({"error": "project not found"}), 404
    return jsonify({"project": project.to_dict()}), 200


@projects_bp.route("", methods=["POST"])
@jwt_required()
def create_project():
    """
    Create a new project.
    ---
    tags: [Projects]
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          required: [title]
          properties:
            title: {type: string, example: "Portfolio Website"}
            description: {type: string}
            technologies: {type: array, items: {type: string}, example: ["Python", "Flask"]}
            project_url: {type: string, example: "https://github.com/user/project"}
            category: {type: string, example: "Web Development"}
            status: {type: string, example: "in_progress"}
    responses:
      201: {description: Project created}
      400: {description: Validation error}
    """
    user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}

    try:
        title = clean_string(data.get("title"), max_length=150, required=True, field_name="title")
        description = clean_string(data.get("description"), field_name="description")
        technologies = normalize_technologies(data.get("technologies"))
        project_url = validate_url_or_none(data.get("project_url"), "project_url")
        category = clean_string(data.get("category", "Other"), max_length=100, field_name="category") or "Other"
        status = clean_string(data.get("status", "planned"), max_length=30, field_name="status").lower()
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    if category not in PROJECT_CATEGORIES:
        return jsonify({"error": f"category must be one of: {', '.join(PROJECT_CATEGORIES)}"}), 400
    if status not in PROJECT_STATUSES:
        return jsonify({"error": f"status must be one of: {', '.join(PROJECT_STATUSES)}"}), 400

    project = Project(
        title=title, description=description, technologies=technologies,
        project_url=project_url, category=category, status=status, user_id=user_id,
    )
    db.session.add(project)
    db.session.flush()
    log_activity(user_id, "project_created", f"Created project: {project.title}", "project", project.id)
    db.session.commit()
    return jsonify({"message": "project created successfully", "project": project.to_dict()}), 201


@projects_bp.route("/<int:project_id>", methods=["PUT", "PATCH"])
@jwt_required()
def update_project(project_id):
    """
    Update an existing project.
    ---
    tags: [Projects]
    security:
      - Bearer: []
    parameters:
      - {in: path, name: project_id, type: integer, required: true}
      - in: body
        name: body
        schema:
          properties:
            title: {type: string}
            description: {type: string}
            technologies: {type: array, items: {type: string}}
            project_url: {type: string}
            category: {type: string}
            status: {type: string}
    responses:
      200: {description: Project updated}
      400: {description: Validation error}
      404: {description: Not found}
    """
    user_id = get_jwt_identity()
    project = current_user_project(project_id)
    if not project:
        return jsonify({"error": "project not found"}), 404

    data = request.get_json(silent=True) or {}

    try:
        if "title" in data:
            project.title = clean_string(data["title"], max_length=150, required=True, field_name="title")
        if "description" in data:
            project.description = clean_string(data["description"], field_name="description")
        if "technologies" in data:
            project.technologies = normalize_technologies(data["technologies"])
        if "project_url" in data:
            project.project_url = validate_url_or_none(data["project_url"], "project_url")
        if "category" in data:
            category = clean_string(data["category"], max_length=100, required=True, field_name="category")
            if category not in PROJECT_CATEGORIES:
                return jsonify({"error": f"category must be one of: {', '.join(PROJECT_CATEGORIES)}"}), 400
            project.category = category
        if "status" in data:
            status = clean_string(data["status"], max_length=30, required=True, field_name="status").lower()
            if status not in PROJECT_STATUSES:
                return jsonify({"error": f"status must be one of: {', '.join(PROJECT_STATUSES)}"}), 400
            project.status = status
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    log_activity(user_id, "project_updated", f"Updated project: {project.title}", "project", project.id)
    db.session.commit()
    return jsonify({"message": "project updated successfully", "project": project.to_dict()}), 200


@projects_bp.route("/<int:project_id>/image", methods=["POST"])
@jwt_required()
def upload_project_image(project_id):
    """
    Upload or replace a project's image.
    ---
    tags: [Projects]
    security:
      - Bearer: []
    consumes:
      - multipart/form-data
    parameters:
      - {in: path, name: project_id, type: integer, required: true}
      - {in: formData, name: image, type: file, required: true, description: "Image file max 5MB"}
    responses:
      200: {description: Image uploaded}
      400: {description: Invalid file}
      404: {description: Project not found}
    """
    user_id = get_jwt_identity()
    project = current_user_project(project_id)
    if not project:
        return jsonify({"error": "project not found"}), 404

    old_image = project.project_image
    try:
        project.project_image = save_uploaded_image(request.files.get("image"), "projects")
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    delete_old_image(old_image)
    log_activity(user_id, "project_image_uploaded", f"Uploaded image for: {project.title}", "project", project.id)
    db.session.commit()
    return jsonify({
        "message": "project image uploaded successfully",
        "image_url": project.project_image,
        "project": project.to_dict(),
    }), 200


@projects_bp.route("/<int:project_id>", methods=["DELETE"])
@jwt_required()
def delete_project(project_id):
    """
    Delete a project and its image.
    ---
    tags: [Projects]
    security:
      - Bearer: []
    parameters:
      - {in: path, name: project_id, type: integer, required: true}
    responses:
      200: {description: Project deleted}
      404: {description: Not found}
    """
    user_id = get_jwt_identity()
    project = current_user_project(project_id)
    if not project:
        return jsonify({"error": "project not found"}), 404

    title = project.title
    old_image = project.project_image
    db.session.delete(project)
    delete_old_image(old_image)
    log_activity(user_id, "project_deleted", f"Deleted project: {title}", "project", project_id)
    db.session.commit()
    return jsonify({"message": "project deleted successfully"}), 200
