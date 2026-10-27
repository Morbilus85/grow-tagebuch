#!/usr/bin/with-contenv sh
cd /app/backend
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8099 --proxy-headers --forwarded-allow-ips="*" --log-level warning
