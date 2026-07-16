from collections import Counter

from flask import Blueprint, jsonify
from flask_jwt_extended import (
    jwt_required,
    get_jwt_identity
)
from sqlalchemy import func

from extensions import db, cache
from models import (
    Project,
    Skill,
    PROJECT_CATEGORIES,
    PROJECT_STATUSES
)

dashboard_bp = Blueprint(
    "dashboard",
    __name__,
    url_prefix="/api/dashboard"
)


@dashboard_bp.route("/stats", methods=["GET"])
@jwt_required()
@cache.cached(
    timeout=30,
    key_prefix=lambda: (
        f"dashboard_{get_jwt_identity()}"
    )
)
def get_stats():
    user_id = int(get_jwt_identity())

    category_rows = (
        db.session.query(
            Project.category,
            func.count(Project.id)
        )
        .filter(Project.user_id == user_id)
        .group_by(Project.category)
        .all()
    )

    status_rows = (
        db.session.query(
            Project.status,
            func.count(Project.id)
        )
        .filter(Project.user_id == user_id)
        .group_by(Project.status)
        .all()
    )

    skill_rows = (
        db.session.query(
            Skill.category,
            func.count(Skill.id),
            func.avg(Skill.proficiency)
        )
        .filter(Skill.user_id == user_id)
        .group_by(Skill.category)
        .all()
    )

    technologies = (
        db.session.query(Project.technologies)
        .filter(
            Project.user_id == user_id,
            Project.technologies.isnot(None)
        )
        .all()
    )

    category_counts = {
        name: 0
        for name in PROJECT_CATEGORIES
    }

    category_counts.update({
        name or "Other": count
        for name, count in category_rows
    })

    status_counts = {
        name: 0
        for name in PROJECT_STATUSES
    }

    status_counts.update({
        name: count
        for name, count in status_rows
    })

    tech_counter = Counter()

    for (value,) in technologies:
        tech_counter.update(
            technology.strip()
            for technology in value.split(",")
            if technology.strip()
        )

    total_skills = sum(
        row[1]
        for row in skill_rows
    )

    weighted_total = sum(
        (
            float(row[2])
            if row[2] is not None
            else 0
        ) * row[1]
        for row in skill_rows
    )

    skill_categories = {
        row[0] or "Uncategorized": row[1]
        for row in skill_rows
    }

    return jsonify({
        "total_projects": sum(
            category_counts.values()
        ),
        "total_skills": total_skills,
        "category_counts": category_counts,
        "status_counts": status_counts,
        "top_technologies": [
            {
                "name": name,
                "count": count
            }
            for name, count
            in tech_counter.most_common(5)
        ],
        "skill_categories": skill_categories,
        "average_skill_proficiency": (
            round(
                weighted_total / total_skills,
                1
            )
            if total_skills
            else 0
        ),
    }), 200