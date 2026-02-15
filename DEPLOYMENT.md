# Deployment Guide

Complete guide for deploying SAPNA CARTING Fleet Management System to production.

## Supported Platforms

- **Railway** (Recommended) - Easy deployment, automatic SSL, PostgreSQL included
- **Render** - Alternative platform with free tier

---

## Pre-Deployment Checklist

- [ ] Code committed to GitHub
- [ ] All tests passing
- [ ] Environment variables documented
- [ ] Database migrations created (`python manage.py makemigrations`)
- [ ] Static files collected locally to test
- [ ] README updated with deployment URL

---

## Option 1: Railway Deployment (Recommended)

### Step 1: Create Railway Account

1. Sign up at [railway.app](https://railway.app)
2. Connect your GitHub account

### Step 2: Create New Project

1. Click "New Project"
2. Select "Deploy from GitHub repo"
3. Choose your repository

### Step 3: Add PostgreSQL Database

1. Click "New" → "Database" → "Add PostgreSQL"
2. Railway automatically adds `DATABASE_URL` to your environment

### Step 4: Configure Environment Variables

In Railway dashboard, add these variables:

| Variable | Value | Required |
|----------|-------|----------|
| `DJANGO_SECRET_KEY` | Generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` | ✅ |
| `DEBUG` | `False` | ✅ |
| `ALLOWED_HOSTS` | `your-app-name.up.railway.app` (auto-filled) | ✅ |
| `GEMINI_API_KEY` | Your Google Gemini API key | Optional |
| `SENTRY_DSN` | Your Sentry DSN | Recommended |
| `EMAIL_HOST_USER` | SMTP email | Optional |
| `EMAIL_HOST_PASSWORD` | SMTP password | Optional |

### Step 5: Deploy

1. Railway automatically deploys on push to main branch
2. Check the "Deployments" tab for status

### Step 6: Post-Deployment Setup

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link to project
railway link

# Run migrations
railway run python manage.py migrate

# Create superuser
railway run python manage.py createsuperuser

# Seed production data
railway run python manage.py seed_initial_data --mode production
```

### Step 7: Verify Deployment

```bash
# Run verification script
./scripts/verify_deployment.sh https://your-app.up.railway.app

# Or check manually
curl https://your-app.up.railway.app/health/
```

### Step 8: Custom Domain (Optional)

1. Go to Railway dashboard → Settings → Domains
2. Click "Generate Domain" or "Custom Domain"
3. Update DNS with provided CNAME
4. Add domain to `ALLOWED_HOSTS` environment variable

---

## Option 2: Render Deployment

### Step 1: Create Render Account

1. Sign up at [render.com](https://render.com)
2. Connect your GitHub account

### Step 2: Deploy Using render.yaml

The `render.yaml` blueprint is already included in the repository:

1. Click "New" → "Blueprint"
2. Connect your repository
3. Render automatically creates:
   - Web service
   - PostgreSQL database
   - Cron job for backups

### Step 3: Configure Environment

Render automatically sets:
- `DATABASE_URL`
- `SECRET_KEY`
- `DEBUG=False`

Add optional variables in dashboard:
- `GEMINI_API_KEY`
- `SENTRY_DSN`
- Email settings

### Step 4: Deploy

Render automatically deploys on push to main branch.

### Step 5: Post-Deployment

```bash
# Via Render Shell
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_initial_data --mode production
```

---

## Environment Variables Reference

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DJANGO_SECRET_KEY` | Django secret key | `django-insecure-...` |
| `DEBUG` | Debug mode | `False` |
| `ALLOWED_HOSTS` | Comma-separated hosts | `app.up.railway.app` |
| `DATABASE_URL` | PostgreSQL URL | `postgresql://...` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google Gemini API | - |
| `SENTRY_DSN` | Sentry error tracking | - |
| `SENTRY_ENVIRONMENT` | Sentry environment | `production` |
| `EMAIL_HOST` | SMTP host | `smtp.gmail.com` |
| `EMAIL_PORT` | SMTP port | `587` |
| `EMAIL_USE_TLS` | Use TLS | `True` |
| `EMAIL_HOST_USER` | SMTP username | - |
| `EMAIL_HOST_PASSWORD` | SMTP password | - |
| `SECURE_SSL_REDIRECT` | Force HTTPS | `True` (prod) |
| `SECURE_HSTS_SECONDS` | HSTS max-age | `31536000` |

---

## SSL/HTTPS Configuration

Both Railway and Render provide automatic SSL certificates:

### Railway
- SSL is automatic for `*.up.railway.app`
- Custom domains get free SSL via Let's Encrypt

### Render
- SSL is automatic for all domains
- No configuration needed

### Django Security Settings

Production settings automatically enable:
- `SECURE_SSL_REDIRECT=True`
- `SECURE_HSTS_SECONDS=31536000`
- `SESSION_COOKIE_SECURE=True`
- `CSRF_COOKIE_SECURE=True`

---

## Troubleshooting

### Build Fails

```bash
# Check build logs in Railway/Render dashboard
# Common issues:
# - Missing requirements in requirements.txt
# - Python version mismatch
# - Static files collection errors
```

### Database Connection Errors

1. Verify `DATABASE_URL` is set
2. Check PostgreSQL service is running
3. Test connection:
   ```bash
   railway run python manage.py dbshell
   ```

### Static Files Not Loading

```bash
# Collect static files manually
railway run python manage.py collectstatic --noinput

# Check WhiteNoise configuration in settings.py
```

### 500 Errors

1. Check Sentry for error details
2. Check application logs:
   ```bash
   railway logs --follow
   ```
3. Verify environment variables

---

## Updating the Application

### Standard Update

1. Push changes to GitHub main branch
2. Railway/Render automatically deploy
3. Monitor deployment status
4. Verify with health check endpoint

### Database Migration Update

```bash
# After deployment, run migrations
railway run python manage.py migrate

# Or use release phase (automatic via Procfile)
```

### Rollback

**Railway:**
1. Dashboard → Deployments
2. Find previous deployment
3. Click "Redeploy"

**Render:**
1. Dashboard → Manual Deploy
2. Select previous commit

---

## Monitoring Setup

### Sentry Integration

1. Create project at [sentry.io](https://sentry.io)
2. Copy DSN from project settings
3. Add `SENTRY_DSN` environment variable
4. Errors automatically tracked

### Health Checks

| Endpoint | Purpose |
|----------|---------|
| `/health/` | Basic health status |
| `/health/detailed/` | Component status |
| `/ready/` | Readiness probe |

### Railway Monitoring

Dashboard shows:
- Request latency
- Error rate
- CPU/memory usage
- Database metrics

---

## Production Checklist

Before considering deployment complete:

- [ ] Application accessible via HTTPS
- [ ] Health check endpoint returns 200
- [ ] Database migrations applied
- [ ] Superuser created
- [ ] Static files serving correctly
- [ ] Error tracking configured (Sentry)
- [ ] Environment variables set correctly
- [ ] `DEBUG=False` in production
- [ ] `ALLOWED_HOSTS` includes production domain
- [ ] Backup strategy configured
- [ ] Documentation updated
- [ ] Team notified of deployment

---

## Post-Deployment Verification

Run the verification script:

```bash
./scripts/verify_deployment.sh https://your-app.up.railway.app
```

Expected output:
```
========================================
SAPNA CARTING Deployment Verification
========================================
Testing URL: https://your-app.up.railway.app

1. Basic Connectivity Tests
----------------------------
Testing Health check endpoint... ✓ PASS (HTTP 200)
Testing Readiness probe... ✓ PASS (HTTP 200)
Testing Detailed health check... ✓ PASS (HTTP 200)

2. Application Endpoints
------------------------
...

========================================
Verification Summary
========================================
Passed: X
Failed: 0

✓ All checks passed! Deployment looks good.
```

---

## Cost Estimates

### Railway
- **Starter Plan**: $5/month minimum
- **Postgres**: Included in usage
- **Estimated**: $10-25/month for small production load

### Render
- **Free Tier**: Available with limitations
- **Starter Plan**: $7/month
- **Estimated**: $15-30/month for production

---

## Support & Resources

- **Railway Docs**: https://docs.railway.app
- **Render Docs**: https://render.com/docs
- **Django Deployment**: https://docs.djangoproject.com/en/5.0/howto/deployment/
- **Project Maintenance**: See [MAINTENANCE.md](MAINTENANCE.md)

---

*Last Updated: February 2024*