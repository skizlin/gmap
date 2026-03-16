# Deploy to server (simple)

You pushed code to GitHub. Now you put that code on the server and restart the app.

---

## Every time you deploy (step-by-step)

Do these steps **in order**, every time you want to put your latest code on the server.

### 1. Connect to the server

Open a terminal (PowerShell, CMD, etc.) and run:

```bash
ssh root@YOUR_SERVER
```

Replace `YOUR_SERVER` with your server address (e.g. IP or hostname). Log in when prompted.

---

### 2. Go to the app folder

```bash
cd /var/www/gmap
```

---

### 3. Pull the latest code from GitHub

```bash
git pull origin main
```

- If it says **"Already up to date"** — you have the latest; continue to step 4.
- If it shows an **error** — copy the full message and get help; do not continue until it’s fixed.
- If it **updates files** — good; continue to step 4.

**If pull says "Your local changes to ... market_type_mappings.csv would be overwritten":**  
That file is per-environment (not in the repo). Keep the server’s copy and allow the pull by running:

```bash
git rm --cached backend/data/markets/market_type_mappings.csv
mv backend/data/markets/market_type_mappings.csv backend/data/markets/market_type_mappings.csv.bak
git pull origin main
rm -f backend/data/markets/market_type_mappings.csv.bak
```

Do not restore the .bak file. Then continue from step 4 (stop the app, build, start). The move aside/restore is needed so the pull can apply the “file removed from repo” change without deleting your server’s copy.

---

### 4. Stop the running app

Run these two commands, one after the other:

```bash
docker stop gmap
```

```bash
docker rm gmap
```

(If you see "No such container", that’s OK — it just means the container wasn’t running.)

---

### 5. Build the new image

```bash
docker build -t gmap .
```

Wait until it finishes (can take a minute). Do not skip the dot at the end.

---

### 6. Start the app

```bash
docker run -d --name gmap -p 8001:8001 -v /var/www/gmap/backend/data:/app/backend/data --restart unless-stopped gmap
```

This starts the container in the background with your data folder mounted.

---

### 7. Check that it’s running

```bash
docker ps
```

You should see a row with `gmap`. Then open your site in the browser (e.g. https://gmap.nomaths.com) and confirm it works.

---

**That’s it.** Repeat steps 1–7 whenever you deploy.

---

## First time on the server (only once)

If the app has never been on this server:

1. Put the code there: `cd /var/www` then `git clone https://github.com/skizlin/gmap.git gmap` then `cd gmap`.
2. Run the protect script so your server data isn't overwritten later: `chmod +x scripts/server-protect-data.sh` then `./scripts/server-protect-data.sh`.
3. Then do steps 4–7 from **Every time you deploy** above (build and start the app).

---

## One-time: start with empty market mappings on server

If "Available markets" on the server still only shows markets that are unmapped on your **local** machine, the server is still using a mappings file that has your local data. To give the server its **own** list (empty so every feed market is available to map), remove the file and restart:

```bash
cd /var/www/gmap
rm -f backend/data/markets/market_type_mappings.csv
docker stop gmap
docker rm gmap
docker build -t gmap .
docker run -d --name gmap -p 8001:8001 -v /var/www/gmap/backend/data:/app/backend/data --restart unless-stopped gmap
```

After that, the server has no mappings; "Available markets" will show all feed markets. When you save a mapping on the server, the app will create a new `market_type_mappings.csv` there.

---

## What goes in the repo vs per-environment

| In repo (deployed with code) | Per-environment (not in repo; each instance has its own) |
|------------------------------|---------------------------------------------------------|
| `sports.csv`, `sport_feed_mappings.csv`, `feed_sports.csv` | `markets.csv`, `market_type_mappings.csv`, `entity_feed_mappings.csv`, `domain_events.csv`, `event_mappings.csv` |
| `backend/data/markets/`: `market_templates.csv`, `market_groups.csv`, `market_outcomes.csv`, `market_period_type.csv`, `market_score_type.csv` | All other backoffice CSVs (brands, categories, competitions, teams, feeds, etc.) |

- **Market type mappings** (`backend/data/markets/market_type_mappings.csv`): which feed market maps to which domain market. This file is **not** in the repo. Local and server each have their own; the “Available markets” list on the server will not be affected by mappings you did locally. To start the server with empty mappings, see **One-time: start with empty market mappings on server** above.

---

## Sports and sport–feed mappings (developer data)

Domain sports (`backend/data/sports.csv`) and sport–feed mappings (`backend/data/sport_feed_mappings.csv`) are **in the repo** so they deploy with the code. You can’t create sports or map feed sports to domain sports in the UI; that’s done by a developer and committed.

- **If you add or change sports or sport–feed mappings on your local machine:** commit `sports.csv` and/or `sport_feed_mappings.csv`, push to GitHub, then on the server run `git pull origin main` and rebuild/restart the app (Steps 3–7). The server will then have the same sports and mappings (e.g. Volleyball for Bet365/Bwin).
- **If the server is missing mappings:** ensure your local `backend/data/sport_feed_mappings.csv` is committed and pushed (it’s no longer gitignored), then pull on the server and redeploy.
