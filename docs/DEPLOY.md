# Deploy to server

## 1. Push to GitHub (done from your machine)

```bash
git add -A
git commit -m "Your message"
git push origin main
```

## 2. On the server

### Option A: Manual deploy (VPS / VM)

```bash
# Clone (first time) or pull
cd /path/to/app
git pull origin main

# Use a virtualenv if you have one
# source venv/bin/activate   # Linux/Mac
# .\venv\Scripts\activate   # Windows

# Install/update dependencies
pip install -r backend/requirements.txt

# Run the app (adjust host/port as needed)
# From project root so backend package is found:
python -m backend.main
# Or with uvicorn directly:
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### Option B: Using a process manager (e.g. systemd on Linux)

Create a service file so the app restarts on reboot:

```ini
# /etc/systemd/system/ptc-gmap.service
[Unit]
Description=PTC Global Mapper
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/PTC Global Mapper - Cursor
ExecStart=/path/to/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ptc-gmap
sudo systemctl restart ptc-gmap
```

### Option C: Docker (if you add a Dockerfile later)

Build and run the image, or use docker-compose for app + reverse proxy.

---

**Note:** If your server is behind nginx or Apache, configure a reverse proxy to forward requests to `http://127.0.0.1:8000`.
