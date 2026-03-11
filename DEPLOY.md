# Deploying PTC Global Mapper

## RBAC data (admins and roles) – not in the repo

The following files are **not** committed to the repo and are **not** overwritten on deploy:

- `backend/data/rbac/users.csv`
- `backend/data/rbac/roles.csv`
- `backend/data/rbac/user_roles.csv`
- `backend/data/rbac/user_brands.csv`
- `backend/data/rbac/role_permissions.csv`
- `backend/data/rbac/rbac_audit_log.csv`

**Initial deployment:** On first run the app creates these files with the correct headers (structure from `backend/config.py`) and **no rows**. Create your first admins and roles in the UI after deploy.

**Future deployments:** `git pull` and rebuild do **not** overwrite these files (they are in `.gitignore`). Each environment (local, server) keeps its own admins and roles.

**Schema changes:** If the CSV structure (columns) is changed in code (`RBAC_*_FIELDS` in `config.py`), existing server files keep their data; new columns are not auto-added. For major schema changes you may need to migrate or recreate the files on the server (back up first).

---

## Line-by-line deploy (Docker, gmap.nomaths.com)

SSH into the server, then run these in order (adjust path if yours is not `/var/www/gmap`).

**First-time setup (clone + build + run once):**

1. `cd /var/www`
2. `git clone https://github.com/skizlin/gmap.git gmap`
3. `cd gmap`
4. `git pull origin main`
5. `docker build -t gmap .`
6. `docker run -d --name gmap -p 8001:8001 -v /var/www/gmap/backend/data:/app/backend/data --restart unless-stopped gmap`
7. `docker ps`
8. `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/`  
   (expect `200`)

**Every deploy after code changes:**

1. `cd /var/www/gmap`
2. `git pull origin main`
3. `docker build -t gmap .`
4. `docker rm -f gmap`
5. `docker run -d --name gmap -p 8001:8001 -v /var/www/gmap/backend/data:/app/backend/data --restart unless-stopped gmap`
6. `docker ps`  
   (optional: `docker logs gmap` to confirm no errors)

**Useful one-liners:**

- View logs: `docker logs gmap`
- Stop: `docker stop gmap`
- Start again: `docker start gmap`

---

## CSV as "database"

Using CSV files under `backend/data/` is **fine for deployment** in these cases:

- **Internal tool** or small team
- **Low concurrency** (few people editing at the same time)
- **Read-heavy** (lots of viewing/filtering, occasional config changes)

The app reads CSVs on demand; no separate database process is needed. Just deploy the whole project (including the `backend/data/` folder) so the CSVs are on the server. If you later need multi-user concurrent writes or much higher traffic, you can switch to SQLite or Postgres and keep the same API.

---

## Docker (Python 3.11 – recommended when the host has Docker)

Uses the repo’s `Dockerfile`. No need to install Python 3.11 on the host.

**1. On the server – clone (if not already) and build:**

```bash
cd /var/www/gmap
git pull origin main
docker build -t gmap .
```

**2. Run the container** (mount `backend/data` so CSV changes persist):

```bash
docker run -d \
  --name gmap \
  -p 8001:8001 \
  -v /var/www/gmap/backend/data:/app/backend/data \
  --restart unless-stopped \
  gmap
```

- **-d** = run in background  
- **-p 8001:8001** = host port 8001 → app in container  
- **-v ...** = host `backend/data` mounted so edits/writes stay on disk  
- **--restart unless-stopped** = start again after reboot  

**3. Check it’s running:**

```bash
docker ps
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/
```

**4. Nginx** – same as below: proxy `gmap.nomaths.com` to `http://127.0.0.1:8001`.

**Useful commands:**

```bash
docker logs gmap          # view logs
docker stop gmap          # stop
docker start gmap         # start again
docker rm -f gmap         # remove container (data in /var/www/gmap/backend/data is safe)
# Then run the `docker run` again to recreate.
```

**After code changes (including RBAC):** On the server run:

```bash
cd /var/www/gmap
git pull origin main
docker build -t gmap .
docker rm -f gmap
# Then run the same docker run -v ... command again (see above).
```

RBAC CSV files under `backend/data/rbac/` are not in the repo; the app creates them with headers only on first run. Existing server data in those files is **not** overwritten by `git pull`.

---

## Option A: Deploy on a cloud VM (VPS)

Good for: full control, internal or public access, low cost.

**1. Get a small Linux server** (e.g. DigitalOcean Droplet, Hetzner, Linode) with Ubuntu 22.04.

**2. On the server, install Python 3.10+ and clone your repo:**

```bash
sudo apt update && sudo apt install -y python3 python3-pip python3-venv git
git clone https://github.com/YOUR_USERNAME/PTC-Global-Mapper.git
cd PTC-Global-Mapper
```

**3. Create a virtualenv and install dependencies:**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
```

**4. Run the app so it accepts external connections:**

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

- `0.0.0.0` = listen on all interfaces (so others can reach it).
- To keep it running after you disconnect, use a process manager (see below).

**5. Open in browser:** `http://YOUR_SERVER_IP:8000` (e.g. `http://192.168.1.10:8000` or your cloud IP).

**6. (Optional) Run as a service with systemd**

Create `/etc/systemd/system/ptc-mapper.service`:

```ini
[Unit]
Description=PTC Global Mapper
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/PTC-Global-Mapper
ExecStart=/home/ubuntu/PTC-Global-Mapper/venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ptc-mapper
sudo systemctl start ptc-mapper
```

**7. (Optional) HTTPS and a domain**

Put Nginx (or Caddy) in front of the app, get a certificate (e.g. Let’s Encrypt), and proxy to `http://127.0.0.1:8000`. Then users use `https://your-domain.com`.

---

## Option B: Deploy on a PaaS (Railway, Render, Fly.io)

Good for: minimal setup, automatic HTTPS, good for small teams.

**Railway / Render / Fly.io** all support “run a Python app”:

1. Connect your GitHub repo.
2. Set **build command** to: `pip install -r backend/requirements.txt` (or leave default if it detects `requirements.txt`).
3. Set **start command** to: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`  
   (PaaS often sets `PORT`; use that if present, otherwise `--port 8000`.)
4. Ensure the **root** of the repo is the project root (so `backend/` and `backend/data/` are included).

The CSVs in `backend/data/` are part of the deployed image. Edits there are lost on redeploy unless you use a persistent volume (Railway/Render/Fly all support this). For read-only or rarely changed data, deploying CSVs as-is is fine.

---

## Summary

| Step | Action |
|------|--------|
| 1 | Push your code to Git (you already did the first commit). |
| 2 | Deploy the **whole project** (including `backend/data/`) to a server or PaaS. |
| 3 | Run: `uvicorn backend.main:app --host 0.0.0.0 --port 8000` (or `--port $PORT` on PaaS). |
| 4 | Share the URL (e.g. `http://YOUR_IP:8000` or `https://your-app.up.railway.app`). |

Using CSV is not a blocker; just keep `backend/data/` in the deployment and you’re good to go for typical internal/small-team use.

---

## gmap.nomaths.com (Hetzner)

Subdomain: **gmap.nomaths.com**. App runs on port **8001** (so it doesn't clash with other projects).

**1. On the server – clone, venv, install:**

```bash
cd /var/www   # or your preferred path
git clone https://github.com/YOUR_USERNAME/PTC-Global-Mapper.git
cd PTC-Global-Mapper
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
```

**2. Test run (then Ctrl+C):**

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8001
```

**3. Systemd service** – create `/etc/systemd/system/ptc-mapper.service`:

```ini
[Unit]
Description=PTC Global Mapper (gmap.nomaths.com)
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/PTC-Global-Mapper
Environment="PATH=/var/www/PTC-Global-Mapper/venv/bin"
ExecStart=/var/www/PTC-Global-Mapper/venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8001
Restart=always

[Install]
WantedBy=multi-user.target
```

Adjust `User` and `WorkingDirectory` if your path is different. Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ptc-mapper
sudo systemctl start ptc-mapper
```

**4. Nginx** – create `/etc/nginx/sites-available/gmap-nomaths`:

```nginx
server {
    listen 80;
    server_name gmap.nomaths.com;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable and reload:

```bash
sudo ln -s /etc/nginx/sites-available/gmap-nomaths /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

**5. HTTPS:**

```bash
sudo certbot --nginx -d gmap.nomaths.com
```

Then use **https://gmap.nomaths.com** (Certbot will redirect HTTP to HTTPS).
