# SAPNA CARTING - Fleet Management System

[![Deployment](https://img.shields.io/badge/deployed-railway-blue)](https://railway.app)
[![Django](https://img.shields.io/badge/django-5.0-green)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/python-3.12-blue)](https://www.python.org/)

A comprehensive fleet management system for SAPNA CARTING built with Django 5.0, HTMX, and Tailwind CSS.

## 🚀 Live Demo

- **Production URL**: [https://sapna-carting.up.railway.app](https://sapna-carting.up.railway.app) *(update with your URL)*
- **Health Status**: `/health/` endpoint

## Project Description

SAPNA CARTING Fleet Management System is a web-based application designed to manage fleet operations, track vehicles, monitor driver activities, and streamline business operations for the carting company.

## Tech Stack

- **Backend**: Django 5.0.2
- **Frontend**: HTML, Tailwind CSS, HTMX
- **Database**: PostgreSQL (Railway/Supabase)
- **Authentication**: Django Auth with role-based access
- **AI Integration**: Google Gemini API for OCR and insights
- **Error Tracking**: Sentry
- **Static Files**: WhiteNoise
- **Deployment**: Railway (primary) / Render (alternative)

## Prerequisites

- Python 3.12+
- PostgreSQL database (local or Supabase)
- pip or poetry for dependency management

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd sapna-carting
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root:
Copy the contents from `.env.example` and update with your actual values:
```env
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgresql://user:password@host:port/dbname
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=your-email@gmail.com
GEMINI_API_KEY=your-gemini-api-key
SUPABASE_URL=your-supabase-url
SUPABASE_ANON_KEY=your-supabase-anon-key
```

5. Run migrations:
```bash
python manage.py migrate
```

6. Create a superuser:
```bash
python manage.py createsuperuser
```

7. Run the development server:
```bash
python manage.py runserver
```

8. Open your browser and navigate to:
   - Main site: http://127.0.0.1:8000/
   - Admin panel: http://127.0.0.1:8000/admin/

## Project Structure

```
sapna_carting/
├── sapna_carting/       # Main Django project settings
├── fleet/               # Fleet management app
├── operations/          # Operations management app
├── dashboard/           # Dashboard and analytics app
├── settings_app/        # Settings and configuration app
├── templates/           # HTML templates
├── static/              # Static files (CSS, JS, images)
├── media/               # User-uploaded files
└── requirements.txt     # Python dependencies
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DJANGO_SECRET_KEY` | Django secret key for production |
| `DEBUG` | Set to 'False' in production |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hosts |
| `DATABASE_URL` | PostgreSQL database URL |
| `EMAIL_HOST` | SMTP email host |
| `EMAIL_PORT` | SMTP email port |
| `EMAIL_USE_TLS` | Use TLS for email |
| `EMAIL_HOST_USER` | SMTP email username |
| `EMAIL_HOST_PASSWORD` | SMTP email password |
| `DEFAULT_FROM_EMAIL` | Default email address for sending emails |
| `GEMINI_API_KEY` | Google Gemini API key for AI features |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase anonymous key |

## Features

- Vehicle fleet management
- Driver management
- Trip/Operation tracking
- Real-time dashboard with HTMX
- PDF report generation
- AI-powered insights with Gemini
- User authentication and authorization

## 🚢 Deployment

### Quick Deploy to Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/your-template-url)

1. Fork this repository
2. Click the "Deploy on Railway" button above
3. Add your environment variables
4. Deploy!

### Deploy to Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

The `render.yaml` file is included for one-click deployment.

### Manual Deployment

See [MAINTENANCE.md](MAINTENANCE.md) for detailed deployment procedures.

**Quick Start:**
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and link project
railway login
railway link

# Deploy
railway up

# Run migrations
railway run python manage.py migrate

# Create superuser
railway run python manage.py createsuperuser

# Seed initial data
railway run python manage.py seed_initial_data --mode production
```

### Post-Deployment Verification

```bash
# Run verification script
./scripts/verify_deployment.sh https://your-app.up.railway.app

# Or manually check
 curl https://your-app.up.railway.app/health/
```

## 📊 Monitoring & Maintenance

- **Health Check**: `/health/` - Basic system status
- **Detailed Health**: `/health/detailed/` - Component status
- **Readiness Probe**: `/ready/` - Kubernetes-style readiness check
- **Error Tracking**: Sentry integration (configure SENTRY_DSN)

See [MAINTENANCE.md](MAINTENANCE.md) for comprehensive maintenance procedures including:
- Database backups and restores
- Troubleshooting guides
- Emergency procedures
- Maintenance schedules

See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for database migration procedures.

## 🛠️ Management Commands

### Database Operations

```bash
# Backup database
python manage.py backup_database --format json --compress

# Restore database
python manage.py restore_database --backup-file backups/backup_YYYYMMDD_HHMMSS.json.gz

# Optimize database
python manage.py optimize_database --analyze

# Seed data
python manage.py seed_initial_data --mode production  # or --mode demo
```

### Alert Management

```bash
# Check document expiry
python manage.py check_document_expiry

# Check fuel efficiency
python manage.py check_fuel_efficiency

# Check tire costs
python manage.py check_tire_costs
```

## 📁 Project Structure

```
sapna_carting/
├── sapna_carting/       # Main Django project settings
│   ├── settings.py      # Production-ready settings with Sentry
│   ├── urls.py          # Health check endpoints included
│   └── wsgi.py          # WSGI application
├── fleet/               # Fleet management app
│   ├── management/      # Custom management commands
│   │   └── commands/
│   │       ├── seed_initial_data.py
│   │       ├── backup_database.py
│   │       ├── restore_database.py
│   │       └── optimize_database.py
│   ├── models.py        # Core models (Truck, Driver, FuelLog, etc.)
│   ├── views.py         # Main views
│   └── views_alerts.py  # Alert management views
├── operations/          # Operations management app
├── dashboard/           # Dashboard and analytics
├── settings_app/        # System settings
├── reporting/           # Reports and analytics
├── templates/           # HTML templates
├── static/              # Static files (CSS, JS, images)
├── scripts/             # Utility scripts
│   └── verify_deployment.sh
├── Procfile             # Railway deployment configuration
├── railway.json         # Railway-specific settings
├── render.yaml          # Render deployment configuration
├── MAINTENANCE.md       # Maintenance runbook
├── MIGRATION_GUIDE.md   # Database migration guide
└── requirements.txt     # Python dependencies
```

## 🔒 Security

- All secrets stored in environment variables
- Django security settings enabled for production
- HTTPS enforced in production
- Sentry error tracking configured
- Database credentials not stored in code

## 🤝 Contributing

1. Create a new branch for your feature
2. Run tests before committing
3. Follow existing code patterns
4. Update documentation as needed

## 📄 License

Copyright © 2024 SAPNA CARTING. All rights reserved.

---

*For support, contact: [your-email@example.com]*
