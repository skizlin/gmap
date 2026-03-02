# PTC Global Mapper – Python 3.11
FROM python:3.11-slim

WORKDIR /app

# Copy project (backend, templates, data, etc.)
COPY backend/ ./backend/
COPY designs/ ./designs/

# Install dependencies
RUN pip install --no-cache-dir -r backend/requirements.txt

EXPOSE 8001

# Run the app (bind 0.0.0.0 so Nginx can reach it)
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8001"]
