# 🚀 Manual Deployment Steps for Varinder

**Quick Path to Live Demo:** Follow these exact steps to get Asynccraft Agent Kernel live on a public URL in ~5 minutes.

---

## Option 1: Render (EASIEST - Recommended)

### Steps:

1. **Go to:** https://render.com/
2. **Sign up** with GitHub, GitLab, or email
3. **Dashboard → New → Web Service**
4. **Connect Git repository:**
   - Click "Connect Git Provider"
   - Choose "Add a Repository" → Custom Git
   - Paste: `https://origin.cursor.com/git/varinder-singh/tmp-ea19a2709cffb78d`
   - Or if mirrored to GitHub: connect your GitHub account and select the repo
5. **Configure:**
   ```
   Name: asynccraft-kernel (or your choice)
   Branch: main
   Region: Oregon (or closest)
   Runtime: Docker
   Instance Type: Free
   ```
6. **Environment Variables** (Advanced → Add Environment Variable):
   ```
   DATABASE_URL=sqlite:///./asynccraft.db
   OPENAI_API_KEY=sk-mock-key-for-demo
   ACTIVE_SKIN=ops_dispatch
   DEBUG=false
   ```
7. **Click "Create Web Service"**
8. **Wait 3-5 minutes** for build and deploy
9. **Your URL:** `https://asynccraft-kernel.onrender.com`

### Test:
```bash
curl https://asynccraft-kernel.onrender.com/health
# Should return: {"status":"healthy"}
```

Visit in browser: `https://asynccraft-kernel.onrender.com`

---

## Option 2: Fly.io (BEST PERFORMANCE)

### Prerequisites:
```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh
```

### Steps:

1. **Sign up / Login:**
   ```bash
   fly auth signup
   # OR if you have an account:
   fly auth login
   ```

2. **Navigate to repo:**
   ```bash
   cd /path/to/asynccraft-agent-kernel
   ```

3. **Launch:**
   ```bash
   fly launch --copy-config --now
   ```

4. **Follow prompts:**
   - Use existing fly.toml? → **Yes**
   - App name → `asynccraft-kernel` (or unique name)
   - Region → Choose closest
   - Postgres? → **No**
   - Deploy now? → **Yes**

5. **Your URL:** `https://asynccraft-kernel.fly.dev`

### Update after changes:
```bash
fly deploy
```

### View logs:
```bash
fly logs
```

---

## Option 3: Railway (DASHBOARD)

### Steps:

1. **Go to:** https://railway.app/
2. **Sign up** with GitHub (easiest)
3. **New Project → Deploy from GitHub repo**
4. **Select repo** (asynccraft-agent-kernel)
5. **Railway auto-detects** Dockerfile
6. **Settings → Variables → Add:**
   ```
   DATABASE_URL=sqlite:///./asynccraft.db
   OPENAI_API_KEY=sk-mock-key-for-demo
   ACTIVE_SKIN=ops_dispatch
   ```
7. **Deployments** tab → Wait for deploy to complete
8. **Settings → Generate Domain** → Get your URL

### Your URL:
Automatically generated, like: `asynccraft-kernel-production.up.railway.app`

---

## After Deployment: Update README

1. **Get your live URL** from the platform
2. **Edit README.md**, line ~8:
   ```markdown
   ## 🚀 Live Demo
   
   **Public URL:** https://YOUR-ACTUAL-URL.com
   ```
3. **Commit and push:**
   ```bash
   git add README.md
   git commit -m "Add live demo URL"
   git push
   ```

---

## Post-Deploy Verification

Run these checks:

```bash
# Health check
curl https://YOUR-URL/health
# Expected: {"status":"healthy"}

# API config
curl https://YOUR-URL/api/config
# Expected: {"active_skin":"ops_dispatch","debug":false}

# UI loads
open https://YOUR-URL
# Expected: Asynccraft Agent Kernel page with two demo buttons
```

**Manual Test:**
1. Visit `https://YOUR-URL`
2. Click "Run Ops/Dispatch Demo"
3. Approval card should appear
4. Enter your name, click "Approve"
5. Tool should execute and disappear from queue

---

## Repository Visibility

### Current Status:
- **Hosted on:** Origin (Cursor Git)
- **URL:** `https://origin.cursor.com/git/varinder-singh/tmp-ea19a2709cffb78d`
- **Visibility:** Private by default

### To Make Public:

**Option A: Origin Settings (if available)**
- Check Cursor Dashboard → Cloud Agents → Repository settings
- Look for public/visibility toggle

**Option B: Mirror to GitHub**
```bash
# 1. Create new GitHub repo (https://github.com/new)
#    Name: asynccraft-agent-kernel
#    Public: ✓

# 2. Add GitHub remote
git remote add github git@github.com:YOUR-USERNAME/asynccraft-agent-kernel.git

# 3. Push to GitHub
git push github main

# 4. Update README to reference GitHub repo
```

**Option C: Keep on Origin + Deploy**
If the hosted demo URL is public and functional, the code repo doesn't necessarily need to be browsable. The live demo proves the implementation.

---

## Recommended Approach

**For job applications:**

1. ✅ **Deploy to Render** (easiest, free, stable)
2. ✅ **Get public URL** (`https://asynccraft-kernel.onrender.com`)
3. ✅ **Update README** with live URL
4. ✅ **Test all features** work on public deploy
5. ✅ **Share README link** in applications (includes live demo + architecture + code)
6. Optional: Mirror to GitHub for code browsing

**Live demo URL > Code repo visibility** for showcasing agent architecture to hiring teams.

---

## Need Help?

**Render:** https://render.com/docs
**Fly.io:** https://fly.io/docs  
**Railway:** https://docs.railway.app

**Built by:** Varinder Nagra | https://asynccraft.com/ | founders@asynccraft.com
