# Deploying SANKET

The API and the web app deploy separately. The web app works without the API (it falls back to
`web/public/replay.json` and says "Replay"), so deploy the web app even if the API sleeps.

## 1. API on Hugging Face Spaces (needs your Hugging Face account)
1. `make space-bundle` writes `dist/space/` (Dockerfile, Space `README.md` with `sdk: docker`, `app_port: 7860`).
2. On huggingface.co create a new Space, SDK Docker, blank, free CPU. Needs your account.
3. Push the folder: `cd dist/space && git init && git remote add space https://huggingface.co/spaces/<you>/sanket && git add . && git commit -m "SANKET" && git push space HEAD:main` (needs your access token).
4. In the Space settings add variable `SANKET_CORS_ORIGINS` = your Vercel address (no trailing slash).
5. Check `https://<you>-sanket.hf.space/api/health` returns `{"status":"ok",...}`.
The container seeds a fresh database on every start, so a free Space that sleeps comes back with demo data.

## 2. Web app on Vercel (needs your Vercel account)
1. Import the repository, root directory `web`, framework Vite (see `web/vercel.json`).
2. Environment variable `VITE_API_URL` = the Space address from step 1.5.
3. Deploy. If the API is asleep the page shows Replay mode and retries every 15 seconds.

## Alternative: Render (needs your Render account)
Create a Web Service from the repository using the root `Dockerfile`; set `PORT` is provided by Render,
and set `SANKET_CORS_ORIGINS`. Free instances sleep and are slow to wake; the seed runs at each start.

## No account needed
`make setup link-torch data train seed serve` then `make web` runs everything on your machine.
`make replay` regenerates `web/public/replay.json` from the real pipeline.
