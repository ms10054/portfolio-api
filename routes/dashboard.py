from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Project, Skill, PROJECT_CATEGORIES, PROJECT_STATUSES

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


@dashboard_bp.route("/stats", methods=["GET"])
@jwt_required()
def get_stats():
    """Get dashboard statistics for the current user."""
    user_id = get_jwt_identity()

    total_projects = Project.query.filter_by(user_id=user_id).count()
    total_skills = Skill.query.filter_by(user_id=user_id).count()

    category_counts = {}
    for cat in PROJECT_CATEGORIES:
        category_counts[cat] = Project.query.filter_by(user_id=user_id, category=cat).count()

    status_counts = {}
    for status in PROJECT_STATUSES:
        status_counts[status] = Project.query.filter_by(user_id=user_id, status=status).count()

    projects = Project.query.filter_by(user_id=user_id).all()
    tech_count = {}
    for project in projects:
        if project.technologies:
            for tech in project.technologies.split(","):
                tech = tech.strip()
                if tech:
                    tech_count[tech] = tech_count.get(tech, 0) + 1
    top_technologies = sorted(
        [{"name": k, "count": v} for k, v in tech_count.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:5]

    skills = Skill.query.filter_by(user_id=user_id).all()
    skill_categories = {}
    for skill in skills:
        cat = skill.category or "Uncategorized"
        skill_categories[cat] = skill_categories.get(cat, 0) + 1

    avg_proficiency = 0
    if skills:
        avg_proficiency = round(sum(s.proficiency for s in skills) / len(skills), 1)

    return jsonify({
        "total_projects": total_projects,
        "total_skills": total_skills,
        "category_counts": category_counts,
        "status_counts": status_counts,
        "top_technologies": top_technologies,
        "skill_categories": skill_categories,
        "average_skill_proficiency": avg_proficiency,
    }), 200
