from datetime import datetime, timezone
from extensions import db, bcrypt


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False,
        index=True
    )
    password_hash = db.Column(
        db.String(255),
        nullable=False
    )
    role = db.Column(
        db.String(20),
        nullable=False,
        default="user"
    )
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    projects = db.relationship(
        "Project",
        backref="owner",
        lazy=True,
        cascade="all, delete-orphan"
    )

    skills = db.relationship(
        "Skill",
        backref="owner",
        lazy=True,
        cascade="all, delete-orphan"
    )

    portfolio = db.relationship(
        "Portfolio",
        backref="owner",
        uselist=False,
        cascade="all, delete-orphan"
    )

    activity_logs = db.relationship(
        "ActivityLog",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan"
    )

    def set_password(self, password):
        self.password_hash = (
            bcrypt.generate_password_hash(password)
            .decode("utf-8")
        )

    def check_password(self, password):
        return bcrypt.check_password_hash(
            self.password_hash,
            password
        )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),
        }


class Portfolio(db.Model):
    __tablename__ = "portfolios"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        unique=True
    )

    phone = db.Column(
        db.String(30),
        nullable=True
    )

    location = db.Column(
        db.String(100),
        nullable=True
    )

    job_title = db.Column(
        db.String(100),
        nullable=True
    )

    profile_image = db.Column(
        db.String(255),
        nullable=True
    )

    bio = db.Column(
        db.Text,
        nullable=True
    )

    education = db.Column(
        db.Text,
        nullable=True
    )

    career_goals = db.Column(
        db.Text,
        nullable=True
    )

    github = db.Column(
        db.String(255),
        nullable=True
    )

    linkedin = db.Column(
        db.String(255),
        nullable=True
    )

    twitter = db.Column(
        db.String(255),
        nullable=True
    )

    website = db.Column(
        db.String(255),
        nullable=True
    )

    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "phone": self.phone,
            "location": self.location,
            "job_title": self.job_title,
            "profile_image": self.profile_image,
            "bio": self.bio,
            "education": self.education,
            "career_goals": self.career_goals,
            "github": self.github,
            "linkedin": self.linkedin,
            "twitter": self.twitter,
            "website": self.website,
            "updated_at": (
                self.updated_at.isoformat()
                if self.updated_at
                else None
            ),
        }


class Skill(db.Model):
    __tablename__ = "skills"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    category = db.Column(
        db.String(100),
        nullable=True
    )

    proficiency = db.Column(
        db.Integer,
        default=50
    )

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    __table_args__ = (
        db.Index(
            "ix_skills_user_category_name",
            "user_id",
            "category",
            "name"
        ),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "proficiency": self.proficiency,
            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),
            "updated_at": (
                self.updated_at.isoformat()
                if self.updated_at
                else None
            ),
            "user_id": self.user_id,
        }


PROJECT_CATEGORIES = [
    "Web Development",
    "Mobile Development",
    "Graphic Design",
    "Data Analysis",
    "Other",
]

PROJECT_STATUSES = [
    "planned",
    "in_progress",
    "completed",
    "archived"
]


class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    title = db.Column(
        db.String(150),
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=True
    )

    technologies = db.Column(
        db.String(255),
        nullable=True
    )

    project_url = db.Column(
        db.String(255),
        nullable=True
    )

    category = db.Column(
        db.String(100),
        nullable=True,
        default="Other"
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="planned"
    )

    project_image = db.Column(
        db.String(255),
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    __table_args__ = (
        db.Index(
            "ix_projects_user_created",
            "user_id",
            "created_at"
        ),
        db.Index(
            "ix_projects_user_status",
            "user_id",
            "status"
        ),
        db.Index(
            "ix_projects_user_category",
            "user_id",
            "category"
        ),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "technologies": (
                [
                    technology.strip()
                    for technology in self.technologies.split(",")
                ]
                if self.technologies
                else []
            ),
            "project_url": self.project_url,
            "category": self.category,
            "status": self.status,
            "project_image": self.project_image,
            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),
            "updated_at": (
                self.updated_at.isoformat()
                if self.updated_at
                else None
            ),
            "user_id": self.user_id,
        }


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    action = db.Column(
        db.String(80),
        nullable=False
    )

    description = db.Column(
        db.String(255),
        nullable=True
    )

    resource_type = db.Column(
        db.String(50),
        nullable=True
    )

    resource_id = db.Column(
        db.Integer,
        nullable=True
    )

    ip_address = db.Column(
        db.String(80),
        nullable=True
    )

    user_agent = db.Column(
        db.String(255),
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        index=True
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action,
            "description": self.description,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),
        }