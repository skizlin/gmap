# Deploy to server (simple)

You pushed code to GitHub. Now you put that code on the server and restart the app.

---

## Step 1: Open a terminal and connect to the server

In your terminal (PowerShell, CMD, or whatever you use), type:

```
ssh root@YOUR_SERVER
```

Replace `YOUR_SERVER` with your real server address (e.g. an IP or a name). Press Enter. Log in if it asks for a password.

---

## Step 2: Go to the app folder

Type this and press Enter:

```
cd /var/www/gmap
```

(If your app is in a different folder on the server, use that folder instead.)

---

## Step 3: Get the latest code from GitHub

Type this and press Enter:

```
git pull origin main
```

If it says "Already up to date", that's fine — you're already on the latest.  
If it prints any error, copy the full error message and ask for help (the fix depends on the error). Otherwise go to Step 4.

---

## Step 4: Stop the old app

Type these two commands, one after the other (press Enter after each):

```
docker stop gmap
```

```
docker rm gmap
```

---

## Step 5: Build the new app

Type this and press Enter (the dot at the end is important):

```
docker build -t gmap .
```

Wait until it finishes. It can take a minute.

---

## Step 6: Start the app

Copy this whole line, paste it in the terminal, press Enter:

```
docker run -d --name gmap -p 8001:8001 -v /var/www/gmap/backend/data:/app/backend/data --restart unless-stopped gmap
```

---

## Step 7: Check that it's running

Type:

```
docker ps
```

You should see a line with `gmap` in it. That means the app is running.

Open your site in the browser (e.g. https://gmap.nomaths.com) and check that it works.

---

## First time on the server (only once)

If the app has never been on this server:

1. Put the code there: `cd /var/www` then `git clone https://github.com/skizlin/gmap.git gmap` then `cd gmap`.
2. Run the protect script so your server data isn't overwritten later: `chmod +x scripts/server-protect-data.sh` then `./scripts/server-protect-data.sh`.
3. Then do Step 4 through Step 7 above (build and start the app).

---

## What goes in the repo vs per-environment

| In repo (deployed with code) | Per-environment (not in repo; each instance has its own) |
|------------------------------|---------------------------------------------------------|
| `sports.csv`, `sport_feed_mappings.csv`, `feed_sports.csv` | `markets.csv`, `market_type_mappings.csv`, `entity_feed_mappings.csv`, `domain_events.csv`, `event_mappings.csv` |
| `backend/data/markets/`: `market_templates.csv`, `market_groups.csv`, `market_outcomes.csv`, `market_period_type.csv`, `market_score_type.csv` | All other backoffice CSVs (brands, categories, competitions, teams, feeds, etc.) |

- **Market type mappings** (`backend/data/markets/market_type_mappings.csv`): which feed market maps to which domain market. This file is **not** in the repo. Local and server each have their own; the “Available markets” list on the server will not be affected by mappings you did locally.
- **After first deploy with this setup:** On the server, remove the old file so the app uses empty mappings:  
  `rm -f backend/data/markets/market_type_mappings.csv`  
  Then restart the app (Steps 4–7). After that, you can map feed markets to domain markets on the server independently.

## Sports and sport–feed mappings (developer data)

Domain sports (`backend/data/sports.csv`) and sport–feed mappings (`backend/data/sport_feed_mappings.csv`) are **in the repo** so they deploy with the code. You can’t create sports or map feed sports to domain sports in the UI; that’s done by a developer and committed.

- **If you add or change sports or sport–feed mappings on your local machine:** commit `sports.csv` and/or `sport_feed_mappings.csv`, push to GitHub, then on the server run `git pull origin main` and rebuild/restart the app (Steps 3–7). The server will then have the same sports and mappings (e.g. Volleyball for Bet365/Bwin).
- **If the server is missing mappings:** ensure your local `backend/data/sport_feed_mappings.csv` is committed and pushed (it’s no longer gitignored), then pull on the server and redeploy.
