# Portfolio Management API

A production-ready REST API backend for a personal portfolio management system, built with Flask and SQLAlchemy. Developed progressively over 5 weeks as part of the Codiora Backend Development internship.

## Live API
> Deploy to Render using the steps below — your live URL will be:
> `https://portfolio-api-xxxx.onrender.com`

---

## Features

- **JWT Authentication** — register, login, logout, token revocation
- **Role-Based Access Control** — user and admin roles with protected endpoints
- **Portfolio Management** — personal info, about, contact, social links
- **Skills CRUD** — add, update, delete skills with proficiency levels
- **Project Management** — full CRUD with categories, statuses, and search
- **Image Uploads** — profile and project images with auto-resize (max 1024×1024)
- **Advanced Search** — filter projects by keyword, category, technology, status
- **Pagination** — all list endpoints support page and per_page parameters
- **Activity Logging** — login history, project updates, profile changes
- **Dashboard Stats** — project counts, skill stats, top technologies
- **Rate Limiting** — 60 requests/minute per IP (configurable)
- **Centralized Logging** — rotating log files for app events, errors, and access
- **Swagger Docs** — interactive API docs at `/docs/`
- **Health Check** — `/health` endpoint for deployment platforms

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Flask 3.x |
| Database ORM | Flask-SQLAlchemy |
| Authentication | Flask-JWT-Extended |
| Password Hashing | Flask-Bcrypt |
| Image Processing | Pillow |
| API Docs | Flasgger (Swagger UI) |
| Caching | Flask-Caching |
| CORS | Flask-Cors |
| Production Server | Gunicorn |
| Database (dev) | SQLite |
| Database (prod) | PostgreSQL |

---

## Project Structure

```
portfolio/
├── app.py              # App factory, middleware, error handlers
├── config.py           # Environment-based configuration
├── extensions.py       # Shared Flask extensions
├── models.py           # Database models
├── utils.py            # Validation, file upload, logging helpers
├── logger.py           # Centralized logging setup
├── Procfile            # Gunicorn startup command for Render/Railway
├── render.yaml         # Render deployment configuration
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
├── .gitignore          # Files excluded from Git
├── README.md           # This file
├── routes/
│   ├── auth.py         # Register, login, logout, user management
│   ├── portfolio.py    # Personal info and profile image
│   ├── projects.py     # Project CRUD, search, image upload
│   ├── skills.py       # Skills CRUD with pagination
│   ├── dashboard.py    # Stats and analytics
│   └── activity.py     # Activity log viewer
├── uploads/            # Uploaded images (not committed to Git)
│   ├── profiles/
│   └── projects/
└── logs/               # Log files (not committed to Git)
    ├── app.log
    ├── errors.log
    └── access.log
```

---

## Local Setup

### 1. Clone the repository
```bash
git clone https://github.com/ms10054/portfolio-api.git
cd portfolio-api
```

### 2. Create a virtual environment
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up environment variables
```bash
# Copy the template
copy .env.example .env   # Windows
cp .env.example .env     # Mac/Linux

# Open .env and fill in your values
# At minimum set SECRET_KEY and JWT_SECRET_KEY
```

### 5. Run the server
```bash
python app.py
```

Server starts at `http://127.0.0.1:5000`

### 6. View API docs
Open `http://127.0.0.1:5000/docs/` in your browser.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes | Flask secret key |
| `JWT_SECRET_KEY` | Yes | JWT signing key |
| `DATABASE_URL` | No | DB connection string (defaults to SQLite) |
| `ADMIN_REGISTRATION_SECRET` | No | Secret code to register admin accounts |
| `FLASK_ENV` | No | `development` or `production` |
| `FLASK_DEBUG` | No | `1` for debug mode, `0` for production |
| `RATE_LIMIT_PER_MINUTE` | No | Requests per minute per IP (default: 60) |
| `MAX_CONTENT_MB` | No | Max upload size in MB (default: 5) |
| `UPLOAD_FOLDER` | No | Path to store uploaded images |

---

## API Overview

All protected endpoints require the header:
```
Authorization: Bearer <your_access_token>
```

### Auth
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/register` | No | Register new user |
| POST | `/api/auth/login` | No | Login, returns token |
| POST | `/api/auth/logout` | Yes | Revoke current token |
| GET | `/api/auth/me` | Yes | Get current user |
| PUT | `/api/auth/change-password` | Yes | Change password |
| GET | `/api/auth/users` | Admin | List all users |
| PUT | `/api/auth/users/<id>/role` | Admin | Update user role |

### Portfolio
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/portfolio` | Get portfolio info |
| POST/PUT | `/api/portfolio` | Create or update portfolio |
| POST | `/api/portfolio/profile-image` | Upload profile image (multipart) |

### Projects
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/projects` | List with search/filter/pagination |
| POST | `/api/projects` | Create project |
| GET | `/api/projects/<id>` | Get single project |
| PUT | `/api/projects/<id>` | Update project |
| DELETE | `/api/projects/<id>` | Delete project |
| POST | `/api/projects/<id>/image` | Upload project image (multipart) |
| GET | `/api/projects/categories` | Get category list |
| GET | `/api/projects/statuses` | Get status list |

### Skills
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/skills` | List skills (paginated) |
| POST | `/api/skills` | Add skill |
| PUT | `/api/skills/<id>` | Update skill |
| DELETE | `/api/skills/<id>` | Delete skill |

### Dashboard & Activity
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/dashboard/stats` | Portfolio statistics |
| GET | `/api/activity` | My activity log |
| GET | `/api/activity/all` | All users activity (admin) |

### System
| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/docs/` | Swagger UI |

---

## Deployment on Render (Free)

### Step 1 — Push code to GitHub
```bash
git init
git add .
git commit -m "Week 5 — production ready API"
git remote add origin https://github.com/ms10054/portfolio-api.git
git push -u origin main
```

### Step 2 — Create account on Render
Go to https://render.com and sign up with GitHub.

### Step 3 — Create a new Web Service
- Click **New** → **Web Service**
- Connect your GitHub repo
- Settings:
  - **Runtime:** Python
  - **Build Command:** `pip install -r requirements.txt`
  - **Start Command:** `gunicorn "app:create_app()" --bind 0.0.0.0:$PORT`

### Step 4 — Add environment variables
In Render dashboard → Environment tab, add:
```
FLASK_ENV=production
SECRET_KEY=<generate a long random string>
JWT_SECRET_KEY=<generate another long random string>
ADMIN_REGISTRATION_SECRET=<your choice>
DATABASE_URL=<your PostgreSQL connection string>
```

### Step 5 — Deploy
Click **Deploy** — Render will build and start your API.
Your live URL will be `https://your-service-name.onrender.com`

---

## Testing

All endpoints are tested using Postman. The Postman collection covers:
- Full auth flow (register → login → protected routes → logout)
- All CRUD operations for projects and skills
- File uploads (profile image, project image)
- Search and filter combinations
- Error responses (401, 403, 404, 400 validation)
- Rate limiting (429)
- Admin routes

Interactive docs also available at `/docs/` (Swagger UI).

---

## Security Practices

- Passwords hashed with bcrypt (never stored in plain text)
- JWT tokens expire after 24 hours
- Revoked tokens tracked in-memory blocklist
- Admin routes protected by role check
- Rate limiting prevents brute force attacks
- All secrets loaded from environment variables
- `.env` and `uploads/` excluded from Git via `.gitignore`
- Input validation on every endpoint (required fields, email format, password strength, data types)
- File uploads validated by extension and size (max 5 MB)

---

*Built by Muhammad Saad — Codiora Backend Development Internship*
