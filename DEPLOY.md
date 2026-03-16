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
