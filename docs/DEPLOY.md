# Deploying SANKET

The API and the web app deploy separately. The web app works without the API (it shows "Replay" and
uses `web/public/replay.json`), so deploy the web app even if the API sleeps. Steps marked
(account) need your own account; I could not run them.

## Run it on your own machine first (no account)
1. `make setup data train seed`. You do not need PyTorch: the neural network's files are already in `artifacts/nn/`.
   (`make train-nn` retrains that network and does need PyTorch; `make link-torch` only works in the original build sandbox.)
2. `make serve` starts the API on http://localhost:8000. After `make retrain` promotes a model,
   restart it: the API loads the champion once at start-up.
3. In another terminal: `cd web && npm install` (once), then `VITE_API_URL=http://localhost:8000 make web`.
   Open http://localhost:5173. Without `VITE_API_URL` the page is always in Replay mode (recorded answers).
4. `make replay` rewrites `web/public/replay.json` from the real pipeline.

## 0. Put the code on GitHub (account)
1. Create an empty repository on github.com (no README), for example `sanket`.
2. In the project folder: `git remote add origin https://github.com/<you>/sanket.git && git push -u origin main`
   (skip `remote add` if `git remote -v` already shows it).
3. Open the repository's Actions tab: the `ci` workflow should run and turn green.

## 1. API on Hugging Face Spaces (account)
1. `make space-bundle` writes `dist/space/` (Dockerfile, Space `README.md` with `sdk: docker`, `app_port: 7860`).
2. Create a Space at huggingface.co: SDK Docker, blank template, free CPU.
3. Hugging Face refuses large binary files in plain git. Inside `dist/space` run:
   `git init && git lfs install && git lfs track "*.joblib" "*.onnx" && git add .gitattributes .`
   (or upload with `hf upload <you>/sanket dist/space . --repo-type space`).
4. Commit and push: `git commit -m "SANKET" && git remote add space https://huggingface.co/spaces/<you>/sanket && git push space HEAD:main`.
   When asked for a password use an access token with write rights (or run `hf auth login` once).
5. Wait for the build, then open `https://<you>-sanket.hf.space/api/health`. It must show `"status":"ok"`.
The container seeds a fresh database at every start, so reviews made on the free Space are lost when it restarts.

## 2. Web app on Vercel (account)
1. Import the GitHub repository, root directory `web`, framework Vite (see `web/vercel.json`).
2. Add environment variable `VITE_API_URL` = the Space address from 1.5 (no trailing slash).
3. Deploy. Note the address Vercel gives you, for example `https://sanket.vercel.app`.
4. Back on the Space: Settings, Variables, set `SANKET_CORS_ORIGINS` = that Vercel address (no trailing slash), then restart the Space.
   Preview deployments have other addresses and stay blocked; use the production address.
5. `VITE_API_URL` is baked in when the page is built. If you change it, redeploy on Vercel.

## Alternative: Render (account)
1. New Web Service from the GitHub repository, runtime Docker, the root `Dockerfile`.
2. Render supplies `PORT`; the Dockerfile uses it. Set `SANKET_CORS_ORIGINS` to the Vercel address.
3. Free instances sleep and the database is rebuilt at each start, so reviews vanish on restart.

## Troubleshooting
- Page says Replay: the API is asleep or `VITE_API_URL` is wrong. Open `<API>/api/health`; wait about a minute for a sleeping Space; the page retries every 15 seconds.
- Browser console shows a CORS error: `SANKET_CORS_ORIGINS` does not equal the page address exactly (scheme, no trailing slash). Fix it and restart the Space.
- Replay is empty or old: run `make replay`, commit `web/public/replay.json`, redeploy. If `replay.json` is missing the page cannot show anything offline.
- Space build fails on a big file: the binary was pushed without LFS (step 1.3).
- Changed `VITE_API_URL` and nothing happened: redeploy the web app (step 2.5).
