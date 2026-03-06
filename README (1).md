# CivicFix – Citizen Infrastructure Reporting Platform

CivicFix connects citizens with local authorities so infrastructure issues (potholes, lighting, drainage, etc.) can be reported, triaged, and resolved quickly. Citizens submit reports with photos and location details, while administrators monitor dashboards, assign priority, and update statuses with real-time notifications.

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Environment Variables](#environment-variables)
- [Setup & Installation](#setup--installation)
- [Running the App](#running-the-app)
- [Utility Scripts](#utility-scripts)
- [Key Workflows](#key-workflows)
- [API Overview](#api-overview)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Features

### Citizen Experience

- Report issues with photos, province/district/sector, and descriptive location text.
- Track issue status changes (Open → In Progress → Resolved).
- Vote on community issues to raise priority.
- Receive WebSocket notifications when admins update an issue.

### Admin Experience

- Modern admin dashboard with stats, filters, and bulk actions.
- Manage issue lifecycle, add comments, and update resolution metadata.
- Monitor votes/engagement and review uploaded evidence.
- Search, filter issues by different criterias.

### Technical Highlights

- Supabase Auth handles registration + email confirmation (no custom SMTP required).
- Flask backend exposes REST APIs + Socket.IO for live updates.
- File uploads automatically resized (Pillow) and stored locally (Supabase Storage-ready).
- Rate limiting, JWT protection, and CORS safeguards baked in.
- Fully responsive frontend (desktop → tablet → phone) with consistent favicon branding.

## Architecture

```
┌───────────────┐        Supabase (PostgreSQL + Auth)
│  Frontend     │  --->  - issues, votes, notifications tables
│  (HTML/CSS/JS)│        - auth.users (email confirmation)
└───────▲───────┘        - admin_auth_codes, etc.
        │
        │ WebSocket / REST
        │
┌───────┴───────┐
│  Flask API    │
│  (app.py)     │
│               │
│  - SQLAlchemy models
│  - Socket.IO events
│  - Email sync logic
└───────────────┘
```

## Technology Stack

| Layer          | Tech                                      |
| -------------- | ----------------------------------------- |
| Backend        | Python 3.11+, Flask, Flask-SocketIO, SQLAlchemy |
| Database/Auth  | Supabase PostgreSQL + Supabase Auth       |
| Frontend       | HTML5, CSS3, Vanilla JS                   |
| Real-time      | Socket.IO                                 |
| File handling  | Pillow (image resizing)                   |
| Tooling        | python-dotenv, requests                   |

## Project Structure

```
civicfix/
├── backend/
│   ├── app.py               # Flask entry point
│   ├── auth.py              # Decorators + Supabase sync
│   ├── models.py            # SQLAlchemy models (users, issues, votes, etc.)
│   ├── config.py            # Loads environment variables
│   ├── rwanda data scripts  # migrate_*.py, fix_sequences.py, seed.py
│   ├── test_smtp.py         # Optional SMTP diagnostic
│   ├── test_supabase_connection.py  # Supabase health check
│   ├── requirements.txt
│   └── uploads/             # Citizen-uploaded photos (dev mode)
├── frontend-web/
│   ├── index.html           # Citizen landing page
│   ├── report.html          # Issue submission form
│   ├── login.html / register.html / profile.html
│   ├── admin-dashboard.html # New admin workspace
│   ├── admin-login.html / admin-register.html
│   ├── styles.css           # Global + responsive styles
│   ├── app.js               # Issue feed logic & sockets
│   ├── auth.js              # Supabase auth helpers
│   ├── notifications.js / websocket.js
│   └── icons/civicfix-favicon.jpg
├── README.md
└── CIVICFIX_SYSTEM_DOCUMENTATION.txt  # Extended guide (reference)
```

## Prerequisites

- Python 3.11+ (3.10 works but 3.11 tested)
- Node.js (optional, for alternative static server)
- Supabase account (free tier)
- Git, pip

## Environment Variables

Create `backend/.env`:

```
# Flask / Supabase
FLASK_ENV=development
SECRET_KEY=change_me
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_KEY=<anon-public-key>
SUPABASE_DB_PASSWORD=<database password>  # only if using Supabase DB directly
DATABASE_URL=postgresql://postgres:<password>@db.<project>.supabase.co:5432/postgres
FRONTEND_ORIGIN=http://localhost:5500



Frontend also needs Supabase values in `frontend-web/auth.js`:

```js
const SUPABASE_URL = 'https://<project>.supabase.co';
const SUPABASE_ANON_KEY = '<anon>';
```

## Setup & Installation

1. **Clone the repo**
   ```bash
   git clone https://github.com/<you>/civicfix.git
   cd civicfix
   ```

2. **Backend setup**
   ```bash
   cd backend
   python -m venv venv
   # Windows
     venv\Scripts\activate
   # macOS/Linux
     source venv/bin/activate

   pip install -r requirements.txt
   copy .env.example .env   # or manually create .env with the values above
   ```

3. **Apply migrations / seed (Supabase already has schema)**
   - Run `python app.py` once; SQLAlchemy will create tables if they don’t exist.
   - Optional: `python seed.py` to insert demo users/issues.

4. **Frontend setup**
   ```bash
   cd ../frontend-web
   # Start a simple static server on port 5500
     python -m http.server 5500
   # or
     npx http-server -p 5500
     ```

## Running the App

1. **Backend (new terminal)**
   ```bash
   cd backend
   venv\Scripts\activate  # or source venv/bin/activate
   python app.py
   ```
   Backend listens on `http://localhost:5000`.

2. **Frontend**
   - Open `http://localhost:5500` for citizens.
   - Admin login pages are under `/admin-login.html`, `/admin-register.html`, or `/admin-dashboard.html`.

3. **Create the first admin**
   ```sql
   -- In Supabase SQL editor
   UPDATE public.users SET is_admin = true WHERE email = 'your-email';
   ```
   Or run `seed.py` and choose an admin option.

## Utility Scripts

| Script | Description |
|--------|-------------|
| `seed.py` | Interactive CLI to create sample citizens, issues, admin auth codes. |
| `test_supabase_connection.py` | Ensures Supabase URL/key/database are reachable, lists tables. |
| `test_smtp.py` | Validates Gmail SMTP credentials (if you ever re-enable custom mail). |
| `migrate_*` scripts | Legacy data migration helpers (SQLite → Supabase). Keep for history or delete if not needed. |

## Key Workflows

### Citizen Registration/Login

1. Citizens register via Supabase (email confirmation link is sent automatically).
2. Once email is confirmed, `auth.js` logs in with Supabase and backend syncs `is_email_verified`.
3. Verified citizens can report issues and receive WebSocket notifications.

### Admin Authorization

1. Admins register via `admin-register.html`; they need a valid Authorization Code (seed via CLI).
2. Admin dashboard uses JWT + Supabase metadata to secure endpoints.

### Reporting & Notifications

- Issue data stored in `public.issues`, images saved locally under `backend/uploads/`.
- Socket.IO pushes updates to citizens and admin dashboards when statuses change.

## API Overview

Backend base URL: `http://localhost:5000/api`

| HTTP | Endpoint | Description |
|------|----------|-------------|
| POST | `/auth/send-verification` *(legacy)* | Not used now; Supabase handles email confirmation. |
| POST | `/auth/check-verification` | Sync/verify email status. |
| POST | `/auth/backend-login` | Fallback login when Supabase token already verified. |
| GET  | `/issues` | List issues (filters: status, category, district). |
| POST | `/issues` | Create issue (auth required). |
| GET  | `/issues/<id>` | Issue details + status history, admin comments. |
| POST | `/issues/<id>/vote` | Vote/unvote. |
| GET  | `/notifications` | User notifications feed. |
| PATCH| `/notifications/<id>/read` | Mark as read. |
| GET  | `/admin/dashboard` | Stats, counts (admin only). |
| PATCH| `/admin/issues/<id>/status` | Update status/resolution. |

See `app.py` for WebSocket events and additional endpoints.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Supabase login works but backend says “Please verify email.” | Ensure Supabase email confirmation was completed. Backend auto-syncs `is_email_verified`. |
| Socket.IO connection fails | Confirm backend is running on `http://localhost:5000` and ports are open. |
| Upload errors | Verify `backend/uploads/` exists and Pillow has JPEG support. |
| Supabase “Not allowed” errors | Use the anon key, not service key; confirm RLS policies. |
| SMTP auth fails | Use a Gmail App Password; run `python test_smtp.py`. Remove SMTP vars if using Supabase emails only. |

## Contributing

Contributions are welcome! Please fork, create a feature branch, test thoroughly, and open a pull request.

## License

MIT License. See `LICENSE` for details.
