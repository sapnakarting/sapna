# SAPNA CARTING - Maintenance Runbook

This document contains comprehensive procedures for maintaining and troubleshooting the SAPNA CARTING Fleet Management System in production.

## Table of Contents

1. [Deployment Procedures](#deployment-procedures)
2. [Database Management](#database-management)
3. [Monitoring](#monitoring)
4. [Troubleshooting Guide](#troubleshooting-guide)
5. [Common Tasks](#common-tasks)
6. [Emergency Procedures](#emergency-procedures)
7. [Maintenance Schedule](#maintenance-schedule)

---

## Deployment Procedures

### Initial Deployment (Railway)

1. **Prerequisites**
   - GitHub repository connected to Railway
   - PostgreSQL database provisioned on Railway
   - Environment variables configured (see below)

2. **Environment Variables**
   ```bash
   DJANGO_SECRET_KEY=<generate-strong-key>
   DEBUG=False
   ALLOWED_HOSTS=<your-railway-app-url>
   DATABASE_URL=<provided-by-railway>
   SENTRY_DSN=<your-sentry-dsn>
   GEMINI_API_KEY=<your-gemini-api-key>
   EMAIL_HOST_USER=<smtp-email>
   EMAIL_HOST_PASSWORD=<smtp-password>
   ```

3. **Deploy**
   - Push code to main branch
   - Railway automatically builds and deploys
   - Migration runs automatically via Procfile

4. **Post-Deployment Setup**
   ```bash
   # Create superuser
   railway run python manage.py createsuperuser
   
   # Seed initial data
   railway run python manage.py seed_initial_data --mode production
   ```

### Updating the Application

1. **Pre-deployment Checklist**
   - [ ] All tests passing
   - [ ] Database migrations created if needed
   - [ ] Backup database before major changes
   - [ ] Update CHANGELOG.md

2. **Deploy Update**
   ```bash
   git push origin main
   ```

3. **Verify Deployment**
   ```bash
   # Check health endpoint
   curl https://your-app.railway.app/health/
   
   # Check detailed health
   curl https://your-app.railway.app/health/detailed/
   ```

### Environment Variable Management

**Railway Dashboard:**
1. Go to your project dashboard
2. Click on Variables tab
3. Add/Update variables
4. Redeploy automatically triggered

**Via CLI:**
```bash
railway variables set KEY=value
```

### Rollback Procedures

1. **Quick Rollback (Railway)**
   - Go to Railway dashboard
   - Select previous deployment
   - Click "Redeploy"

2. **Database Rollback**
   ```bash
   # Restore from backup
   railway run python manage.py restore_database --backup-file backups/backup_YYYYMMDD_HHMMSS.json
   ```

---

## Database Management

### Running Backups

**Manual Backup:**
```bash
# JSON format (recommended)
railway run python manage.py backup_database --format json --compress

# SQL format (PostgreSQL only)
railway run python manage.py backup_database --format sql --compress

# Specific models only
python manage.py backup_database --models fleet.Truck fleet.Driver
```

**Automated Backups (Render):**
- Already configured in `render.yaml` as cron job
- Runs daily at 2 AM UTC
- Backups stored in `/backups/` directory

### Restoring from Backup

**Prerequisites:**
- Ensure backup file is accessible
- Verify backup integrity
- Notify users of maintenance window

**Restore Process:**
```bash
# Preview what will be restored
python manage.py restore_database --backup-file backups/backup_YYYYMMDD_HHMMSS.json.gz --dry-run

# Full restore (with confirmation)
python manage.py restore_database --backup-file backups/backup_YYYYMMDD_HHMMSS.json.gz

# No confirmation prompt
python manage.py restore_database --backup-file backups/backup_YYYYMMDD_HHMMSS.json.gz --no-input
```

⚠️ **WARNING:** Restore will replace ALL existing data unless using `--append` flag.

### Running Migrations

**Standard Migration:**
```bash
# Run pending migrations
python manage.py migrate

# Check migration status
python manage.py showmigrations

# Dry run (show SQL without executing)
python manage.py migrate --plan
```

**Production Migration:**
```bash
# Backup first
python manage.py backup_database --format json --compress

# Run migrations
python manage.py migrate

# Verify
python manage.py showmigrations
```

### Database Optimization

**Analyze and suggest indexes:**
```bash
python manage.py optimize_database --analyze
```

**Create migration for indexes:**
```bash
python manage.py optimize_database --create-migration
# Then: python manage.py makemigrations --empty fleet
# Copy output to the new migration file
```

**Run VACUUM ANALYZE (PostgreSQL):**
```bash
python manage.py optimize_database --vacuum
```

### Seeding Data

**Production Mode:**
```bash
python manage.py seed_initial_data --mode production
```
- Creates system settings
- Creates essential admin user
- Creates diesel price entries

**Demo Mode:**
```bash
python manage.py seed_initial_data --mode demo
```
- Creates sample trucks, drivers, tires
- Creates sample logs and trips
- Creates demo users

**With Data Reset:**
```bash
python manage.py seed_initial_data --mode demo --clear
```

---

## Monitoring

### Health Check Endpoints

| Endpoint | Purpose | Expected Response |
|----------|---------|-------------------|
| `/health/` | Basic health check | `{"status": "healthy"}` |
| `/health/detailed/` | Component status | Full system status |
| `/ready/` | Readiness probe | `{"ready": true}` |

**Check Health:**
```bash
curl https://your-app.railway.app/health/
curl https://your-app.railway.app/health/detailed/
```

### Sentry Error Tracking

**Dashboard:** https://sentry.io/organizations/YOUR_ORG/projects/sapna-carting/

**Key Metrics to Monitor:**
- Error rate (should be < 0.1%)
- Performance issues
- Database slow queries
- External API failures (Gemini)

**Alert Configuration:**
- Critical errors: Email + Slack
- Performance degradation: Email
- New error types: Email digest

### Railway Dashboard Monitoring

**Key Metrics:**
- Request latency (target: < 200ms p95)
- Error rate (target: < 0.5%)
- CPU usage (scale if > 70%)
- Memory usage (scale if > 80%)
- Database connections

### Logs

**Railway Logs:**
```bash
railway logs
```

**Filter by Service:**
```bash
railway logs --service web
```

**Follow Logs:**
```bash
railway logs --follow
```

---

## Troubleshooting Guide

### Application Won't Start

**Symptoms:** 502/503 errors, deployment fails

**Checklist:**
1. Check logs: `railway logs`
2. Verify environment variables are set
3. Check database connectivity: `/health/detailed/`
4. Verify migrations ran: `python manage.py showmigrations`
5. Check static files collected

**Common Fixes:**
```bash
# Collect static files
python manage.py collectstatic --noinput

# Run migrations manually
python manage.py migrate

# Restart service
railway up
```

### Database Connection Issues

**Symptoms:** 500 errors, timeout on DB operations

**Diagnosis:**
```bash
# Check DB connection
python manage.py dbshell
# Or: SELECT 1;
```

**Solutions:**
- Verify DATABASE_URL is correct
- Check if database is running (Railway dashboard)
- Restart database service
- Check connection limits

### Static Files Not Loading

**Symptoms:** CSS/JS 404 errors, unstyled pages

**Fix:**
```bash
# Collect static files
python manage.py collectstatic --noinput --clear

# Verify WhiteNoise is in MIDDLEWARE (after SecurityMiddleware)
```

### SSL/HTTPS Issues

**Symptoms:** Mixed content warnings, insecure connection

**Fix:**
- Ensure `SECURE_SSL_REDIRECT = True` in production
- Check `ALLOWED_HOSTS` includes your domain
- Verify `SECURE_PROXY_SSL_HEADER` is set

### High Memory Usage

**Symptoms:** Application restarts frequently, slow response

**Solutions:**
1. Check for memory leaks in code
2. Reduce gunicorn workers: `--workers 2` in Procfile
3. Upgrade Railway plan
4. Optimize database queries (add indexes)

### Slow API Responses

**Diagnosis:**
```bash
# Enable Django Debug Toolbar in dev
# Check Sentry for slow transactions
# Review database query logs
```

**Solutions:**
- Add database indexes (see `optimize_database` command)
- Use `select_related()` / `prefetch_related()`
- Cache frequently accessed data
- Optimize Gemini API calls

---

## Common Tasks

### Creating a Superuser

```bash
railway run python manage.py createsuperuser
```

Or programmatically:
```bash
railway run python manage.py shell -c "
from django.contrib.auth.models import User
User.objects.create_superuser('admin', 'admin@example.com', 'securepassword')
"
```

### Managing Static Files

**Collect Static:**
```bash
python manage.py collectstatic --noinput
```

**Clear and Rebuild:**
```bash
python manage.py collectstatic --noinput --clear
```

### Running Management Commands

```bash
# Via Railway CLI
railway run python manage.py <command>

# Examples
railway run python manage.py check
railway run python manage.py shell
railway run python manage.py dbshell
```

### Database Console Access

```bash
# Open PostgreSQL console
railway run python manage.py dbshell

# Or via psql (if available locally)
railway connect postgres
```

### Checking Application Version

```bash
# Via health endpoint
curl https://your-app.railway.app/health/

# Via Railway dashboard
railway status
```

---

## Emergency Procedures

### Application is Down

**Immediate Actions:**
1. Check Railway status page: https://railway.app/status
2. Check application logs: `railway logs --follow`
3. Check health endpoint response
4. Verify database is accessible

**Recovery Steps:**
1. Restart service: `railway up`
2. If DB issue: Restart database service
3. If persistent: Rollback to last known good deployment

### Database Corruption

**Symptoms:** Data integrity errors, foreign key violations

**Recovery:**
1. Stop application writes
2. Assess extent of corruption
3. Restore from most recent clean backup:
   ```bash
   python manage.py restore_database --backup-file <latest-good-backup>
   ```
4. Verify data integrity
5. Restart application

### Security Incident Response

**If Compromised:**
1. Rotate all secrets immediately
   - DJANGO_SECRET_KEY
   - Database credentials
   - API keys (Gemini, Email)
2. Force password reset for all users
3. Review access logs for suspicious activity
4. Check for unauthorized data access
5. Notify affected parties if PII exposed

**Force Password Reset:**
```bash
python manage.py shell -c "
from django.contrib.auth.models import User
for user in User.objects.all():
    user.set_unusable_password()
    user.save()
"
```

### Rollback to Previous Version

**Via Railway Dashboard:**
1. Go to Deployments
2. Find last known good deployment
3. Click "Redeploy"

**Via CLI:**
```bash
# List deployments
railway deployments

# Redeploy specific version
railway redeploy <deployment-id>
```

---

## Maintenance Schedule

### Daily
- [ ] Check Sentry for new errors
- [ ] Review application logs for warnings
- [ ] Monitor disk space usage
- [ ] Verify backup job ran (if automated)

### Weekly
- [ ] Review performance metrics
- [ ] Check error rates and trends
- [ ] Review and triage Sentry issues
- [ ] Update dependencies if security patches available

### Monthly
- [ ] Test database restore procedure
- [ ] Review and rotate access keys
- [ ] Analyze slow queries and optimize
- [ ] Review user access and permissions
- [ ] Check SSL certificate expiration

### Quarterly
- [ ] Full security audit
- [ ] Disaster recovery drill
- [ ] Performance optimization review
- [ ] Documentation update
- [ ] Cost analysis and optimization

---

## Quick Reference

### Important URLs

| Service | URL |
|---------|-----|
| Production App | https://your-app.up.railway.app |
| Railway Dashboard | https://railway.app/project/PROJECT_ID |
| Sentry | https://sentry.io/organizations/ORG/projects/sapna-carting |
| Database | Via Railway Dashboard |

### Emergency Contacts

- **Primary:** [Your Name] - [Email] - [Phone]
- **Secondary:** [Backup Contact]
- **Railway Support:** https://railway.app/help

### Useful Commands

```bash
# Health check
curl https://your-app.up.railway.app/health/

# Create backup
python manage.py backup_database --format json --compress

# View logs
railway logs --follow

# SSH into container
railway run bash

# Database shell
railway run python manage.py dbshell
```

---

*Last Updated: February 2024*
*Document Owner: DevOps Team*