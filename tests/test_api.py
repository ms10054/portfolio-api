import io
import os

os.environ["FLASK_ENV"] = "testing"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret"
os.environ[
    "ADMIN_REGISTRATION_SECRET"
] = "admin-test-secret"

import pytest
from PIL import Image

from app import create_app
from extensions import db


@pytest.fixture()
def app():
    application = create_app()

    with application.app_context():
        db.drop_all()
        db.create_all()

    yield application


@pytest.fixture()
def client(app):
    return app.test_client()


def register_and_login(client):
    register_response = client.post(
        "/api/auth/register",
        json={
            "name": "Test User",
            "email": "test@example.com",
            "password": "password1",
        },
    )

    assert register_response.status_code == 201

    login_response = client.post(
        "/api/auth/login",
        json={
            "email": "test@example.com",
            "password": "password1",
        },
    )

    assert login_response.status_code == 200

    access_token = (
        login_response.get_json()[
            "access_token"
        ]
    )

    return {
        "Authorization": (
            f"Bearer {access_token}"
        )
    }


def test_health_and_ready(client):
    health_response = client.get(
        "/health"
    )

    ready_response = client.get(
        "/ready"
    )

    assert health_response.status_code == 200
    assert ready_response.status_code == 200


def test_auth_security_and_headers(client):
    response = client.get(
        "/api/auth/me"
    )

    assert response.status_code == 401

    assert (
        response.headers[
            "X-Content-Type-Options"
        ]
        == "nosniff"
    )

    assert response.headers.get(
        "X-Request-ID"
    )


def test_project_skill_dashboard_flow(client):
    headers = register_and_login(client)

    project_response = client.post(
        "/api/projects",
        headers=headers,
        json={
            "title": "Portfolio API",
            "technologies": [
                "Python",
                "Flask"
            ],
            "category": "Web Development",
            "status": "completed",
        },
    )

    assert project_response.status_code == 201

    skill_response = client.post(
        "/api/skills",
        headers=headers,
        json={
            "name": "Python",
            "category": "Backend",
            "proficiency": 90,
        },
    )

    assert skill_response.status_code == 201

    dashboard_response = client.get(
        "/api/dashboard/stats",
        headers=headers,
    )

    response_body = (
        dashboard_response.get_json()
    )

    assert dashboard_response.status_code == 200

    assert (
        response_body[
            "total_projects"
        ]
        == 1
    )

    assert (
        response_body[
            "total_skills"
        ]
        == 1
    )


def test_invalid_image_is_rejected(client):
    headers = register_and_login(client)

    response = client.post(
        "/api/portfolio/profile-image",
        headers=headers,
        data={
            "image": (
                io.BytesIO(
                    b"not an image"
                ),
                "fake.jpg",
            )
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400


def test_valid_image_upload(client):
    headers = register_and_login(client)

    image = Image.new(
        "RGB",
        (10, 10)
    )

    image_data = io.BytesIO()
    image.save(
        image_data,
        "JPEG"
    )

    image_data.seek(0)

    response = client.post(
        "/api/portfolio/profile-image",
        headers=headers,
        data={
            "image": (
                image_data,
                "photo.jpg"
            )
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200