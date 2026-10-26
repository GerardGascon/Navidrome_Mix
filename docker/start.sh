#!/bin/sh
echo "[setup] Initializing cron jobs..."

echo "$MIX_UPDATE_SCHEDULE cd /opt/navidrome-mix && python daily_mix.py >> /proc/1/fd/1 2>&1" > /etc/crontabs/root
chmod 600 /etc/crontabs/root
echo "[setup] Registered MIX_UPDATE_SCHEDULE job: $MIX_UPDATE_SCHEDULE"

if [ "$EXECUTE_ON_START" = "true" ]; then
  echo "[setup] Executing startup task..."
  cd /opt/navidrome-mix && python daily_mix.py --force
fi

echo "[setup] Starting cron..."
crond -f