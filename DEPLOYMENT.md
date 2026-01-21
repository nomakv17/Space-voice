# SpaceVoice Production Deployment Guide

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        DNS (Cloudflare/Route53)                 │
├─────────────────────────────────────────────────────────────────┤
│  dashboard.spacevoice.ai  →  Vercel (Frontend)                  │
│  api.spacevoice.ai        →  Railway (Backend)                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 1. Backend Deployment (Railway)

### Prerequisites
- Railway account: https://railway.app
- GitHub repository connected

### Steps

1. **Create New Project in Railway**
   - Click "New Project" → "Deploy from GitHub repo"
   - Select the SpaceVoice repository
   - Railway auto-detects the Dockerfile

2. **Add PostgreSQL**
   - Click "New" → "Database" → "PostgreSQL"
   - Railway auto-injects `DATABASE_URL`

3. **Add Redis**
   - Click "New" → "Database" → "Redis"
   - Railway auto-injects `REDIS_URL`

4. **Set Environment Variables**
   Go to your service → "Variables" and add:

   ```
   # Required
   DEBUG=false
   SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
   ADMIN_EMAIL=admin@spacevoice.ai
   ADMIN_PASSWORD=<strong-password>
   PUBLIC_URL=https://api.spacevoice.ai
   FRONTEND_URL=https://dashboard.spacevoice.ai

   # AI Services
   OPENAI_API_KEY=sk-...
   RETELL_API_KEY=key_...

   # Telephony (at least one)
   TELNYX_API_KEY=KEY...
   TELNYX_PUBLIC_KEY=...
   ```

5. **Configure Custom Domain**
   - Go to "Settings" → "Networking" → "Public Networking"
   - Add custom domain: `api.spacevoice.ai`
   - Add the CNAME record to your DNS

6. **Run Database Migrations**
   - Railway runs migrations automatically via Dockerfile
   - Or manually: `railway run alembic upgrade head`

---

## 2. Frontend Deployment (Vercel)

### Prerequisites
- Vercel account: https://vercel.com
- GitHub repository connected

### Steps

1. **Import Project**
   - Click "Add New" → "Project"
   - Import from GitHub
   - Select the SpaceVoice repository
   - Set "Root Directory" to `frontend`

2. **Configure Build Settings**
   - Framework Preset: Next.js (auto-detected)
   - Build Command: `npm run build`
   - Output Directory: `.next`

3. **Set Environment Variables**
   Go to "Settings" → "Environment Variables":

   ```
   NEXT_PUBLIC_API_URL=https://api.spacevoice.ai
   NEXT_PUBLIC_WS_URL=wss://api.spacevoice.ai
   ```

4. **Configure Custom Domain**
   - Go to "Settings" → "Domains"
   - Add: `dashboard.spacevoice.ai`
   - Add the CNAME record to your DNS

---

## 3. DNS Configuration

Add these records to your DNS provider:

| Type  | Name      | Value                          |
|-------|-----------|--------------------------------|
| CNAME | dashboard | cname.vercel-dns.com           |
| CNAME | api       | <your-railway-app>.up.railway.app |

---

## 4. Post-Deployment Checklist

### Security
- [ ] SECRET_KEY changed from default
- [ ] ADMIN_PASSWORD changed from default
- [ ] All API keys rotated (if previously exposed)
- [ ] HTTPS enforced on both domains

### Functionality
- [ ] Backend health check: `curl https://api.spacevoice.ai/health`
- [ ] Frontend loads: `https://dashboard.spacevoice.ai`
- [ ] Admin can login with email
- [ ] Admin can create clients
- [ ] Clients can login with Client ID
- [ ] Onboarding flow works

### Webhooks
- [ ] Update Retell webhook URL to: `https://api.spacevoice.ai/api/v1/retell/webhook`
- [ ] Update Telnyx webhook URL to: `https://api.spacevoice.ai/api/v1/telnyx/webhook`

---

## 5. Monitoring (Recommended)

### Sentry (Error Tracking)
1. Create project at https://sentry.io
2. Add to Railway environment:
   ```
   SENTRY_DSN=https://...@sentry.io/...
   SENTRY_ENVIRONMENT=production
   ```

### Vercel Analytics
- Enable in Vercel dashboard under "Analytics"
- Free tier includes basic metrics

---

## 6. Troubleshooting

### Backend won't start
- Check Railway logs for startup errors
- Verify DATABASE_URL and REDIS_URL are set
- Ensure SECRET_KEY is not default (will fail in production)

### Frontend shows "Internal Server Error"
- Check browser console for API errors
- Verify NEXT_PUBLIC_API_URL is correct
- Check CORS settings in backend

### Login fails
- Verify backend is running: `curl https://api.spacevoice.ai/health`
- Check admin credentials in Railway variables
- Run migrations if user table is empty

---

## Quick Commands

```bash
# Generate secure SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"

# Test backend health
curl https://api.spacevoice.ai/health

# Test API docs
open https://api.spacevoice.ai/docs

# View Railway logs
railway logs

# Run migrations manually
railway run alembic upgrade head
```
