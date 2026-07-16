"""
Portfolio Management API — Week 5
Production-ready Flask application with:
  - Environment-based configuration
  - Centralized logging (app, error, access logs)
  - Rate limiting
  - Centralized error handling
  - Swagger API documentation
  - Connection pooling and caching
"""

import os
import time
import uuid
from collections import defaultdict, deque

from flask import Flask, jsonify, request, send_from_directory, g
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from flasgger import Swagger

from config import get_config
from extensions import db, bcrypt, jwt, cors, cache
from logger import setup_logging, setup_access_log


SWAGGER_CONFIG = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/apispec.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/docs/",
    "info": {
        "title": "Portfolio Management API",
        "description": (
            "Week 6 — Production API Enhancement & Final Optimization\n\n"
            "Features: JWT Auth, Role-Based Access, Image Uploads, "
            "Advanced Search, Pagination, Activity Logging, Rate Limiting, "
            "Environment Configuration, Centralized Error Handling."
        ),
        "version": "6.0.0",
        "contact": {
            "name": "Muhammad Saad",
            "url": "https://github.com/ms10054",
        },
    },
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "Enter: Bearer &lt;your_token&gt;",
        }
    },
}


RATE_BUCKETS = defaultdict(deque)


def apply_rate_limit(app):
    @app.before_request
    def rate_limit():
        skip = {
            "static",
            "flasgger.static",
            "uploaded_file",
            "health",
        }

        if request.endpoint in skip:
            return None

        ip_address = (
            request.headers.get(
                "X-Forwarded-For",
                request.remote_addr
            )
            or "unknown"
        )

        current_time = time.time()

        limit = app.config.get(
            "RATE_LIMIT_PER_MINUTE",
            60
        )

        hits = RATE_BUCKETS[ip_address]

        while (
            hits
            and hits[0] <= current_time - 60
        ):
            hits.popleft()

        if len(hits) >= limit:
            app.logger.warning(
                f"Rate limit exceeded — IP: {ip_address}"
            )

            return jsonify({
                "error": "rate limit exceeded",
                "message": (
                    "too many requests, "
                    "please wait and try again"
                ),
            }), 429

        hits.append(current_time)
        return None


def apply_access_logging(app):
    access_log = setup_access_log()

    @app.before_request
    def before():
        g.start_time = time.time()

        g.request_id = request.headers.get(
            "X-Request-ID",
            str(uuid.uuid4())
        )[:100]

    @app.after_request
    def after(response):
        duration = round(
            (
                time.time()
                - g.get(
                    "start_time",
                    time.time()
                )
            ) * 1000,
            2
        )

        request_id = g.get(
            "request_id",
            "unknown"
        )

        forwarded = request.headers.get(
            "X-Forwarded-For",
            ""
        )

        ip_address = (
            forwarded.split(",")[0].strip()
            if forwarded
            else request.remote_addr
        )

        message = (
            f"request_id={request_id} "
            f"method={request.method} "
            f"path={request.path} "
            f"status={response.status_code} "
            f"duration_ms={duration} "
            f"ip={ip_address}"
        )

        access_log.info(message)

        if response.status_code >= 500:
            app.logger.error(
                "Failed request: %s",
                message
            )

        elif response.status_code >= 400:
            app.logger.warning(
                "Failed request: %s",
                message
            )

        response.headers[
            "X-Request-ID"
        ] = request_id

        response.headers[
            "X-Content-Type-Options"
        ] = "nosniff"

        response.headers[
            "X-Frame-Options"
        ] = "DENY"

        response.headers[
            "Referrer-Policy"
        ] = "no-referrer"

        response.headers[
            "Permissions-Policy"
        ] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=()"
        )

        if (
            request.is_secure
            or app.config.get("ENV")
            == "production"
        ):
            response.headers[
                "Strict-Transport-Security"
            ] = (
                "max-age=31536000; "
                "includeSubDomains"
            )

        if request.path.startswith("/api/auth"):
            response.headers[
                "Cache-Control"
            ] = "no-store"

        else:
            response.headers[
                "Cache-Control"
            ] = response.headers.get(
                "Cache-Control",
                "no-cache"
            )

        return response


def ensure_schema_updates(app):
    database_url = app.config[
        "SQLALCHEMY_DATABASE_URI"
    ]

    if not database_url.startswith("sqlite"):
        return

    with db.engine.connect() as connection:
        tables = {}

        rows = connection.exec_driver_sql(
            "SELECT name FROM sqlite_master "
            "WHERE type='table'"
        )

        for row in rows:
            columns = {
                column[1]
                for column
                in connection.exec_driver_sql(
                    f"PRAGMA table_info({row[0]})"
                )
            }

            tables[row[0]] = columns

        migrations = [
            (
                "users",
                "role",
                "ALTER TABLE users "
                "ADD COLUMN role VARCHAR(20) "
                "NOT NULL DEFAULT 'user'",
            ),
            (
                "projects",
                "status",
                "ALTER TABLE projects "
                "ADD COLUMN status VARCHAR(30) "
                "NOT NULL DEFAULT 'planned'",
            ),
            (
                "projects",
                "project_image",
                "ALTER TABLE projects "
                "ADD COLUMN project_image VARCHAR(255)",
            ),
        ]

        for table, column, sql in migrations:
            if (
                table in tables
                and column not in tables[table]
            ):
                connection.exec_driver_sql(sql)

                app.logger.info(
                    f"Migration applied: "
                    f"added {table}.{column}"
                )

        connection.commit()


def create_app():
    app = Flask(__name__)
    app.config.from_object(get_config())

    os.makedirs(
        app.config["UPLOAD_FOLDER"],
        exist_ok=True
    )

    setup_logging(app)

    app.logger.info(
        f"Starting Portfolio API "
        f"in {app.config['ENV']} mode"
    )

    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    cors.init_app(app)
    cache.init_app(app)

    Swagger(
        app,
        config=SWAGGER_CONFIG
    )

    apply_rate_limit(app)
    apply_access_logging(app)

    from routes.auth import (
        auth_bp,
        TOKEN_BLOCKLIST
    )

    from routes.projects import projects_bp
    from routes.skills import skills_bp
    from routes.portfolio import portfolio_bp
    from routes.dashboard import dashboard_bp
    from routes.activity import activity_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(skills_bp)
    app.register_blueprint(portfolio_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(activity_bp)

    @jwt.token_in_blocklist_loader
    def check_revoked(jwt_header, jwt_payload):
        return (
            jwt_payload["jti"]
            in TOKEN_BLOCKLIST
        )

    @jwt.unauthorized_loader
    def missing_token(error):
        return jsonify({
            "error": (
                "authorization token "
                "is missing or invalid"
            )
        }), 401

    @jwt.invalid_token_loader
    def invalid_token(error):
        return jsonify({
            "error": "token is invalid"
        }), 401

    @jwt.expired_token_loader
    def expired_token(
        jwt_header,
        jwt_payload
    ):
        return jsonify({
            "error": (
                "token has expired, "
                "please login again"
            )
        }), 401

    @jwt.revoked_token_loader
    def revoked_token(
        jwt_header,
        jwt_payload
    ):
        return jsonify({
            "error": (
                "token has been revoked, "
                "please login again"
            )
        }), 401

    @app.errorhandler(400)
    def bad_request(error):
        app.logger.warning(
            "400 Bad Request: %s",
            request.path
        )

        return jsonify({
            "error": "bad request",
            "message": (
                "the request could "
                "not be processed"
            ),
        }), 400

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({
            "error": "unauthorized",
            "message": (
                "authentication required"
            ),
        }), 401

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            "error": "forbidden",
            "message": (
                "you do not have permission"
            ),
        }), 403

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "error": "not found",
            "message": (
                "the requested resource "
                "does not exist"
            ),
        }), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({
            "error": "method not allowed"
        }), 405

    @app.errorhandler(413)
    def file_too_large(error):
        maximum_size = (
            app.config["MAX_CONTENT_LENGTH"]
            // (1024 * 1024)
        )

        return jsonify({
            "error": "file too large",
            "message": (
                f"maximum file size "
                f"is {maximum_size} MB"
            ),
        }), 413

    @app.errorhandler(429)
    def too_many_requests(error):
        return jsonify({
            "error": "rate limit exceeded",
            "message": "too many requests",
        }), 429

    @app.errorhandler(SQLAlchemyError)
    def database_error(error):
        db.session.rollback()

        app.logger.exception(
            "Database error on %s",
            request.path
        )

        return jsonify({
            "error": "database error",
            "message": (
                "the database operation "
                "could not be completed"
            ),
        }), 500

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()

        app.logger.exception(
            "500 Internal Server Error on %s",
            request.path
        )

        return jsonify({
            "error": "internal server error",
            "message": (
                "something went wrong "
                "on our end"
            ),
        }), 500

    @app.route("/uploads/<path:filename>")
    def uploaded_file(filename):
        return send_from_directory(
            app.config["UPLOAD_FOLDER"],
            filename
        )

    @app.route("/health")
    def health():
        return jsonify({
            "status": "healthy",
            "environment": app.config["ENV"],
            "version": "6.0.0",
        }), 200

    @app.route("/ready")
    def ready():
        try:
            db.session.execute(
                text("SELECT 1")
            )

            return jsonify({
                "status": "ready",
                "database": "connected",
                "version": "6.0.0",
            }), 200

        except SQLAlchemyError:
            db.session.rollback()

            app.logger.exception(
                "Readiness database check failed"
            )

            return jsonify({
                "status": "not ready",
                "database": "unavailable",
            }), 503

    @app.route("/")
    def index():
        return jsonify({
            "message": (
                "Portfolio Management API — "
                "Week 6 (Production Ready)"
            ),
            "docs": "/docs/",
            "health": "/health",
            "version": "6.0.0",
            "week_6_features": [
                (
                    "1. Deployment-ready — "
                    "Procfile and gunicorn "
                    "for Render/Railway"
                ),
                (
                    "2. Environment configuration — "
                    "all secrets in .env, "
                    "never in code"
                ),
                (
                    "3. Advanced validation — "
                    "email, password strength, "
                    "types, lengths"
                ),
                (
                    "4. Logging — app.log, "
                    "errors.log, access.log "
                    "with rotation"
                ),
                (
                    "5. API Documentation — "
                    "Swagger UI at /docs/"
                ),
                (
                    "6. Fully tested — "
                    "all endpoints verified "
                    "with correct responses"
                ),
            ],
            "all_endpoints": {
                "auth": [
                    "POST /api/auth/register",
                    "POST /api/auth/login",
                    "POST /api/auth/logout",
                    "GET  /api/auth/me",
                    "PUT  /api/auth/change-password",
                    (
                        "GET  /api/auth/users "
                        "[admin only]"
                    ),
                    (
                        "PUT  /api/auth/users/"
                        "<id>/role [admin only]"
                    ),
                ],
                "portfolio": [
                    "GET /api/portfolio",
                    "POST/PUT /api/portfolio",
                    (
                        "POST /api/portfolio/"
                        "profile-image (multipart)"
                    ),
                ],
                "skills": [
                    (
                        "GET /api/skills"
                        "?page=1&per_page=10"
                    ),
                    "POST /api/skills",
                    "PUT /api/skills/<id>",
                    "DELETE /api/skills/<id>",
                ],
                "projects": [
                    (
                        "GET /api/projects"
                        "?search=&category="
                        "&technology=&status="
                        "&page=&per_page="
                    ),
                    "GET /api/projects/categories",
                    "GET /api/projects/statuses",
                    "GET /api/projects/<id>",
                    "POST /api/projects",
                    "PUT /api/projects/<id>",
                    (
                        "POST /api/projects/"
                        "<id>/image (multipart)"
                    ),
                    "DELETE /api/projects/<id>",
                ],
                "dashboard": [
                    "GET /api/dashboard/stats"
                ],
                "activity": [
                    (
                        "GET /api/activity"
                        "?page=1&action=login"
                    ),
                    (
                        "GET /api/activity/all "
                        "[admin only]"
                    ),
                ],
                "system": [
                    "GET /health",
                    "GET /ready",
                    "GET /docs/",
                ],
            },
        })

    with app.app_context():
        db.create_all()
        ensure_schema_updates(app)

        app.logger.info(
            "Database tables created/verified"
        )

    return app


if __name__ == "__main__":
    application = create_app()

    debug_mode = (
        os.environ.get(
            "FLASK_DEBUG",
            "1"
        ) == "1"
    )

    application.run(
        debug=debug_mode,
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        ),
    )