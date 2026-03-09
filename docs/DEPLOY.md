# Deploy to server

## 1. Push to GitHub (from your machine)

```bash
git add -A
git commit -m "Your message"
git push origin main
```

---

## 2. Deploy on Hetzner (Docker)

SSH to the server, then run:

```bash
ssh root@23.88.106.222
cd /var/www/gmap

# Stash server data so git pull doesn’t overwrite it
# sports.csv and sport_feed_mappings.csv are never stashed — always from git (local)
git stash push -m "server data" -- \
  backend/data/competitions.csv \
  backend/data/domain_events.csv \
  backend/data/entity_feed_mappings.csv \
  backend/data/event_mappings.csv \
  backend/data/teams.csv \
  backend/data/categories.csv

git pull origin main

# Restore server data
git stash pop

# Rebuild and run container
docker stop gmap
docker rm gmap
docker build -t gmap .
docker run -d --name gmap -p 8001:8001 \
  -v /var/www/gmap/backend/data:/app/backend/data \
  --restart unless-stopped \
  gmap

docker ps
```

**Optional:** If you also keep server-specific changes in `margin_templates.csv`, `margin_template_competitions.csv`, or `translations.csv`, add them to the `git stash push` list so they aren’t overwritten by `git pull`.

---

## Other options

### Manual run (no Docker)

```bash
cd /var/www/gmap
git pull origin main
pip install -r backend/requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8001
```

### systemd

Use a unit file that runs `uvicorn backend.main:app --host 0.0.0.0 --port 8001` from the project directory (see earlier version of this doc if needed).

---

**Note:** With Docker, the app listens on port **8001**. Point nginx or your reverse proxy at `http://127.0.0.1:8001`.
