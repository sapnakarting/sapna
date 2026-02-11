# SAPNA CARTING - Fleet Management System

A comprehensive fleet management system for SAPNA CARTING built with Django 5.0, HTMX, and Tailwind CSS.

## Project Description

SAPNA CARTING Fleet Management System is a web-based application designed to manage fleet operations, track vehicles, monitor driver activities, and streamline business operations for the carting company.

## Tech Stack

- **Backend**: Django 5.0.2
- **Frontend**: HTML, Tailwind CSS, HTMX
- **Database**: PostgreSQL (Supabase)
- **Authentication**: Django Auth
- **AI Integration**: Google Gemini API

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

## License

Copyright © 2024 SAPNA CARTING. All rights reserved.
