# Deployment Guide: Asynccraft Agent Kernel

This guide provides step-by-step instructions to deploy the Asynccraft Agent Kernel demo to a public HTTPS URL.

---

## Quick Deploy Options

### Option 1: Render (Recommended - Easiest)

**Time:** ~5 minutes | **Cost:** Free tier | **No CLI required**

1. **Create Render account** (if needed): https://render.com/
2. **Connect repository:**
   - Dashboard → New → Web Service
   - Connect Git provider → Origin/Custom Git
   - Paste repo URL: `https://origin.cursor.com/git/varinder-singh/tmp-ea19a2709cffb78d`
3. **Configure service:**
   - Name: `asynccraft-kernel` (or your choice)
   - Branch: `main`
   - Root directory: leave blank
   - Runtime: `Docker`
   - Region: Choose closest
   - Instance type: `Free`
4. **Environment variables** (auto-loaded from `render.yaml` if detected, or set manually):
   ```
   DATABASE_URL=sqlite:///./asynccraft.db
   OPENAI_API_KEY=sk-mock-key-for-demo
   ACTIVE_SKIN=ops_dispatch
   DEBUG=false
   ```
5. **Deploy!** Render will build and deploy automatically.
6. **Your URL:** `https://asynccraft-kernel.onrender.com` (or custom name)

**Health check:** Visit `https://YOUR-APP.onrender.com/health`

---

### Option 2: Fly.io

**Time:** ~10 minutes | **Cost:** Free tier | **Requires CLI**

1. **Install Fly CLI:** https://fly.io/docs/hands-on/install-flyctl/
2. **Sign up / Log in:**
   ```bash
   fly auth signup
   # or
   fly auth login
   ```
3. **Deploy from repo:**
   ```bash
   cd /path/to/asynccraft-agent-kernel
   fly launch --copy-config --now
   ```
4. **Follow prompts:**
   - Use existing `fly.toml`? **Yes**
   - App name: `asynccraft-kernel` (or choose unique name)
   - Region: Choose closest
   - Postgres? **No** (using SQLite)
5. **Your URL:** `https://asynccraft-kernel.fly.dev`

**Update later:**
```bash
fly deploy
```

**View logs:**
```bash
fly logs
```

---

### Option 3: Railway

**Time:** ~5 minutes | **Cost:** Free trial | **Dashboard or CLI**

#### Via Dashboard:
1. **Create Railway account:** https://railway.app/
2. **New Project → Deploy from repo**
3. **Connect repo:** Paste Git URL or connect GitHub
4. **Railway auto-detects** `Dockerfile` and `railway.json`
5. **Add environment variables** (Settings → Variables):
   ```
   DATABASE_URL=sqlite:///./asynccraft.db
   OPENAI_API_KEY=sk-mock-key-for-demo
   ACTIVE_SKIN=ops_dispatch
   ```
6. **Deploy** automatically triggers
7. **Your URL:** Generated (e.g., `https://asynccraft-kernel.up.railway.app`)

#### Via CLI:
```bash
npm install -g @railway/cli
railway login
cd /path/to/asynccraft-agent-kernel
railway init
railway up
railway open
```

---

## Post-Deployment Checklist

✅ Health check returns 200: `curl https://YOUR-URL/health`
✅ UI loads: Visit `https://YOUR-URL/`
✅ Demo buttons work: "Run Ops/Dispatch Demo" and "Run Deal Flow Demo"
✅ HITL approval flow: Click demo → Approval card appears → Approve/Reject works

---

## Making the Repo Public (Optional)

### Origin Repository

The repo is currently hosted on Origin (Cursor's Git hosting):
```
https://origin.cursor.com/git/varinder-singh/tmp-ea19a2709cffb78d
```

**To make it browsable:**
- Check Cursor Dashboard → Cloud Agents → Repository settings
- Look for visibility/access controls
- Origin may not support public browse URLs by default

**Alternative:** Mirror to GitHub for public visibility:
```bash
# Create GitHub repo first (https://github.com/new)
git remote add github https://github.com/YOUR-USERNAME/asynccraft-agent-kernel.git
git push github main
```

Then deploy from GitHub URL instead.

---

## Troubleshooting

### Build fails with "no such table"
Database migrations not run. Ensure start command includes:
```bash
alembic upgrade head && uvicorn asynccraft.main:app --host 0.0.0.0 --port 8000
```

### Health check fails
- Verify port matches service config (8000)
- Check logs for startup errors
- Ensure `DATABASE_URL` is set

### UI loads but demos don't work
- Check logs for tool registration errors
- Verify all environment variables are set
- May need to restart after first migration run

### Free tier sleeps after inactivity
- **Render:** Spins down after 15 min, cold start ~30s
- **Fly.io:** Configurable auto-stop (set in `fly.toml`)
- **Railway:** Trial includes some uptime, then usage-based

---

## Redeploy After Changes

### Render
- Auto-deploys on `git push` to `main`
- Or: Dashboard → Manual Deploy → Deploy Latest Commit

### Fly.io
```bash
fly deploy
```

### Railway
- Auto-deploys on push
- Or: Dashboard → Manual Deploy

---

## Cost Estimate

All platforms offer free tiers sufficient for a demo portfolio site:

| Platform | Free Tier | Notes |
|----------|-----------|-------|
| **Render** | 750 hours/month | Sleeps after 15 min inactivity |
| **Fly.io** | 3 shared-cpu VMs | Auto-stop when idle |
| **Railway** | $5 trial credit | Usage-based after |

**Recommendation:** Start with **Render** (easiest, no CLI) or **Fly.io** (best performance).

---

## Support

- Render: https://render.com/docs
- Fly.io: https://fly.io/docs
- Railway: https://docs.railway.app

Built by **Varinder Nagra** | https://asynccraft.com/
