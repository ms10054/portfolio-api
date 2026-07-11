from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from models import ActivityLog
from utils import admin_required, parse_positive_int, pagination_meta

activity_bp = Blueprint("activity", __name__, url_prefix="/api/activity")


@activity_bp.route("", methods=["GET"])
@jwt_required()
def my_activity():
    """Current user: view own login history, project updates, and profile changes."""
    user_id = get_jwt_identity()
    page = parse_positive_int(request.args.get("page"), default=1)
    per_page = parse_positive_int(request.args.get("per_page"), default=10, max_value=50)
    action = request.args.get("action", "").strip()

    query = ActivityLog.query.filter_by(user_id=user_id)
    if action:
        query = query.filter(ActivityLog.action == action)

    pagination = query.order_by(ActivityLog.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return jsonify({
        "activity": [item.to_dict() for item in pagination.items],
        "pagination": pagination_meta(pagination),
    }), 200


@activity_bp.route("/all", methods=["GET"])
@jwt_required()
@admin_required
def all_activity():
    """Admin only: view activity logs for every user."""
    page = parse_positive_int(request.args.get("page"), default=1)
    per_page = parse_positive_int(request.args.get("per_page"), default=10, max_value=50)
    user_id = request.args.get("user_id")
    action = request.args.get("action", "").strip()

    query = ActivityLog.query
    if user_id:
        query = query.filter(ActivityLog.user_id == int(user_id))
    if action:
        query = query.filter(ActivityLog.action == action)

    pagination = query.order_by(ActivityLog.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return jsonify({
        "activity": [item.to_dict() for item in pagination.items],
        "pagination": pagination_meta(pagination),
    }), 200
