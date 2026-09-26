# Deploying AutoML

Backend: all 4 engines merged into one Docker image (`Dockerfile` + `start.sh`),
fronted by a reverse-proxy gateway (`gateway/`) so it ships as **one** hosted
service instead of four. Frontend: a static Vite build. See `gateway/main.py`'s
docstring for why the four engines are merged this way instead of literally
importing all four into one Python process.

Everything below marked **(you)** needs a browser and your own account — I
can't click through OAuth/account-creation flows. Everything else is already
done and verified locally.

## What's already prepared

- `Dockerfile` + `start.sh` — builds and runs all 4 engines + the gateway in
  one container. Built and smoke-tested locally (see below).
- `gateway/` — the reverse proxy. Tested against all 4 engines' real routes,
  including binary file downloads (Person 3's `/export`) and multipart file
  uploads (Person 1's `/upload`).
- `render.yaml` — a Render Blueprint that deploys the Dockerfile as-is.
- `frontend/.env.production.example` — the 4 env var values the frontend needs
  once the backend has a real URL. No frontend code changes required.

## Step 1 — Push to GitHub (you)

Everything needs to be on GitHub for both Render and Vercel to build from.
If you haven't already: `git add`, commit, and `git push` this repo (ask me to
do the commit/push part if you want — that one I *can* do, it's the account
linking on Render/Vercel's side that needs you).

## Step 2 — Deploy the backend on Render (you)

1. Go to [render.com](https://render.com) and sign up / log in (GitHub login is easiest).
2. **New +** → **Blueprint**.
3. Connect your GitHub account if prompted, then select this repo.
4. Render will detect `render.yaml` automatically and show one service:
   `automl-backend`, using the Dockerfile. Click **Apply**.
5. First build takes a while (installing pandas/numpy/scikit-learn/lightgbm for
   all 4 engines) — expect 5-10 minutes. Watch the build logs.
6. Once live, Render gives you a URL like `https://automl-backend-xxxx.onrender.com`.
   **Copy this URL** — you'll need it in Step 3.
7. Test it: open `https://automl-backend-xxxx.onrender.com/health` in a
   browser. You should see `{"status":"ok","service":"gateway",...}`.

**Free-tier note:** Render's free web services spin down after 15 minutes of
inactivity and take ~30-60s to wake up on the next request. The first request
after idle time will be slow (or briefly time out) — that's the platform, not
a bug. If that's a problem for a live demo, wake it up (hit `/health`) a
minute before you present.

## Step 3 — Deploy the frontend on Vercel (you)

1. Go to [vercel.com](https://vercel.com) and sign up / log in (GitHub login again).
2. **Add New** → **Project** → import this repo.
3. Vercel should auto-detect Vite. Set the **Root Directory** to `frontend`
   (important — the repo root isn't the frontend app).
4. Before deploying, add these **Environment Variables** (Project Settings →
   Environment Variables), using the Render URL from Step 2:

   | Name | Value |
   |---|---|
   | `VITE_PERSON1_API_URL` | `https://automl-backend-xxxx.onrender.com/person1` |
   | `VITE_PERSON2_API_URL` | `https://automl-backend-xxxx.onrender.com/person2` |
   | `VITE_PERSON3_API_URL` | `https://automl-backend-xxxx.onrender.com/person3` |
   | `VITE_PERSON4_API_URL` | `https://automl-backend-xxxx.onrender.com/person4` |
   | `VITE_MOCK_PERSON3` | `false` |
   | `VITE_MOCK_PERSON4` | `false` |

5. Deploy. Vercel gives you a URL like `https://your-project.vercel.app`.

## Step 4 — Lock down CORS (you, optional but recommended)

Right now the backend's `ALLOWED_ORIGINS` is set to `*` (anyone can call it).
Once you have your real Vercel URL:

1. Render dashboard → `automl-backend` → **Environment**.
2. Set `ALLOWED_ORIGINS` to your Vercel URL (e.g.
   `https://your-project.vercel.app`), no trailing slash.
3. Save — Render redeploys automatically.

## Step 5 — Test the real thing

Open your Vercel URL and run the full flow: Upload → Analyze → Suggest →
Apply & Export → Validation → Recommend. Expect the first request after any
idle period to be slow (Render free-tier cold start, see Step 2's note).

## Known limitations of this setup

- **Ephemeral storage.** Render's free tier doesn't persist disk across
  restarts/redeploys. Mid-session data (uploaded datasets, job results)
  survives fine while the container is running, but a redeploy or a
  long-enough idle-then-restart cycle clears it. Fine for a live demo, not for
  long-term storage.
- **Single container, no auto-scaling.** All 4 engines share one small
  container's CPU/RAM. Person 4's real cross-validation benchmarking (already
  slow locally on large datasets, see earlier notes) will be slower here, not
  faster.
- **No process supervisor.** If one of the 4 engines crashes inside the
  container, `start.sh` doesn't restart it automatically — only a full
  container restart would. Acceptable for a demo; would need `supervisord` or
  similar for anything more serious.
