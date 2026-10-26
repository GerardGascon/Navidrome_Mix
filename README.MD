# Navidrome Mix Generator

Automatically generates Daily and Weekly playlists in Navidrome using several mix-generation modes.

## Overview

This application generates four types of mixes:

* **Discovery** — prioritizes tracks that have never or rarely been played.
* **Personal Radio** — favors familiar and starred tracks.
* **Deep Library** — strongly favors rarely/never-played tracks.
* **Balanced** — combines discovery, familiarity, favorites, and randomness.

Each mix contains the number of tracks configured by `PLAYLIST_SIZE`.

The playlists are persistent. Running the generator again updates the existing playlist rather than creating a new dated playlist.

## Directory

The application lives at:

```text
/DATA/Applications/Navidrome_Mix/
```

Expected files:

```text
Navidrome_Mix/
├── daily_mix.py
├── history.json
├── .env
├── .gitignore
└── README.md
```

`.env` contains the Navidrome credentials and configuration.

`data/history.json` stores track and playlist history so recently generated tracks can be avoided.

---

# Configuration

## `.env`

The application uses environment variables for configuration.

Example:

```text
NAVIDROME_URL=http://127.0.0.1:4533
NAVIDROME_USER=YOUR_NAVIDROME_USERNAME
NAVIDROME_PASSWORD=YOUR_NAVIDROME_PASSWORD

PLAYLIST_SIZE=80
MAX_PER_ARTIST=2
MAX_PER_ALBUM=2

AVOID_GENERATED_DAYS=30
POOL_SIZE=3000

DAILY_PLAYLIST_PREFIX=Daily Mix
WEEKLY_PLAYLIST_PREFIX=Weekly Mix
KEEP_PLAYLIST_DAYS=30
```

Keep the `.env` file private:

```bash
chmod 600 /DATA/Applications/Navidrome_Mix/.env
```

Do not commit `.env` to Git.

The `.gitignore` file should contain:

```text
.env
```

---

# Running Manually

The Python script accepts two arguments:

```text
daily_mix.py <frequency> <mode>
```

## Frequencies

```text
daily
weekly
```

## Modes

```text
discovery
radio
deep
balanced
```

Examples:

```bash
cd /DATA/Applications/Navidrome_Mix

python3 daily_mix.py daily discovery
python3 daily_mix.py daily radio
python3 daily_mix.py daily deep
python3 daily_mix.py daily balanced
```

Weekly:

```bash
python3 daily_mix.py weekly discovery
python3 daily_mix.py weekly radio
python3 daily_mix.py weekly deep
python3 daily_mix.py weekly balanced
```

## Loading `.env` manually

When running the script directly from the shell, load the `.env` file first:

```bash
cd /DATA/Applications/Navidrome_Mix

set -a
source .env
set +a
```

Then run the script:

```bash
python3 daily_mix.py daily balanced
```

The `set -a` / `set +a` commands export the variables from `.env` so Python can access them through `os.environ`.

---

# Generated Playlists

The application maintains persistent playlists.

Daily:

```text
Daily Mix — Discovery
Daily Mix — Personal Radio
Daily Mix — Deep Library
Daily Mix — Balanced
```

Weekly:

```text
Weekly Mix — Discovery
Weekly Mix — Personal Radio
Weekly Mix — Deep Library
Weekly Mix — Balanced
```

Running the generator again finds the existing playlist and updates its contents.

It does **not** create a new playlist every day.

---

# Track History

The application stores generated track information in:

```text
history.json
```

The history is used to reduce the chance that recently generated tracks appear again.

The default configuration is:

```text
AVOID_GENERATED_DAYS=30
```

This means tracks generated within the previous 30 days are strongly discouraged.

The history file should normally be left alone.

If it becomes corrupted, the script will warn and start with a fresh history.

---

# Systemd Automation

The application uses systemd services and timers.

Expected systemd files:

```text
/etc/systemd/system/navidrome-daily-mix.service
/etc/systemd/system/navidrome-daily-mix.timer

/etc/systemd/system/navidrome-weekly-mix.service
/etc/systemd/system/navidrome-weekly-mix.timer
```

The services run the Python script.

The timers determine when the services run.

---

# Daily Service

The daily service runs all four daily modes:

```text
daily discovery
daily radio
daily deep
daily balanced
```

Service:

```text
navidrome-daily-mix.service
```

The service uses:

```ini
User=YOUR_USERNAME
WorkingDirectory=/DATA/Applications/Navidrome_Mix
EnvironmentFile=/DATA/Applications/Navidrome_Mix/.env
```

This means systemd automatically loads the `.env` file.

No `source .env` is necessary when systemd runs the application.

---

# Weekly Service

The weekly service runs:

```text
weekly discovery
weekly radio
weekly deep
weekly balanced
```

Service:

```text
navidrome-weekly-mix.service
```

It also loads:

```text
/DATA/Applications/Navidrome_Mix/.env
```

through systemd's `EnvironmentFile` option.

---

# Scheduling

The schedule is controlled by the `.timer` files.

## Daily

Edit:

```bash
sudo nano /etc/systemd/system/navidrome-daily-mix.timer
```

Example:

```ini
[Unit]
Description=Run Navidrome Daily Mix Generator

[Timer]
OnCalendar=*-*-* 03:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

The above runs every day at **03:00**.

To change the time, modify:

```text
OnCalendar=*-*-* HH:MM:SS
```

For example, 06:00:

```ini
OnCalendar=*-*-* 06:00:00
```

---

## Weekly

Edit:

```bash
sudo nano /etc/systemd/system/navidrome-weekly-mix.timer
```

Example:

```ini
[Unit]
Description=Run Navidrome Weekly Mix Generator

[Timer]
OnCalendar=Mon *-*-* 03:30:00
Persistent=true

[Install]
WantedBy=timers.target
```

This runs every Monday at 03:30.

For Monday at 06:30:

```ini
OnCalendar=Mon *-*-* 06:30:00
```

---

# After Changing a Timer

Whenever a `.timer` file is modified:

```bash
sudo systemctl daemon-reload
```

Then restart the timer:

```bash
sudo systemctl restart navidrome-daily-mix.timer
sudo systemctl restart navidrome-weekly-mix.timer
```

Check the schedule:

```bash
systemctl list-timers --all | grep navidrome
```

The output shows the next scheduled run.

---

# Enabling Automation

Enable the timers so they start automatically after reboot:

```bash
sudo systemctl enable --now navidrome-daily-mix.timer
sudo systemctl enable --now navidrome-weekly-mix.timer
```

Check:

```bash
systemctl list-timers --all | grep navidrome
```

Both timers should appear.

---

# Testing

It is possible to run the services manually without waiting for their scheduled time.

## Test Daily

```bash
sudo systemctl start navidrome-daily-mix.service
```

Then:

```bash
sudo systemctl status navidrome-daily-mix.service
```

A successful `Type=oneshot` service normally ends with:

```text
Active: inactive (dead)
```

This is normal.

Look for:

```text
Deactivated successfully.
Finished navidrome-daily-mix.service
```

and successful playlist messages such as:

```text
SUCCESS: Daily Mix — Balanced
```

## Test Weekly

```bash
sudo systemctl start navidrome-weekly-mix.service
```

Then:

```bash
sudo systemctl status navidrome-weekly-mix.service
```

---

# Logs

systemd stores the Python output in the journal.

View the daily log:

```bash
sudo journalctl -u navidrome-daily-mix.service --no-pager
```

View only recent entries:

```bash
sudo journalctl -u navidrome-daily-mix.service -n 200 --no-pager
```

Follow the log live:

```bash
sudo journalctl -u navidrome-daily-mix.service -f
```

Weekly:

```bash
sudo journalctl -u navidrome-weekly-mix.service --no-pager
```

Look specifically for successful generations:

```bash
sudo journalctl -u navidrome-daily-mix.service --no-pager | grep "SUCCESS"
```

Expected output:

```text
SUCCESS: Daily Mix — Discovery
SUCCESS: Daily Mix — Personal Radio
SUCCESS: Daily Mix — Deep Library
SUCCESS: Daily Mix — Balanced
```

---

# Checking Service Status

Daily:

```bash
sudo systemctl status navidrome-daily-mix.service
```

Daily timer:

```bash
sudo systemctl status navidrome-daily-mix.timer
```

Weekly:

```bash
sudo systemctl status navidrome-weekly-mix.service
```

Weekly timer:

```bash
sudo systemctl status navidrome-weekly-mix.timer
```

---

# Troubleshooting

## `KeyError: 'NAVIDROME_USER'`

Example:

```text
KeyError: 'NAVIDROME_USER'
```

This means the environment variables aren't available to Python.

When running manually:

```bash
set -a
source .env
set +a
```

Then retry.

When running through systemd, verify the service contains:

```ini
EnvironmentFile=/DATA/Applications/Navidrome_Mix/.env
```

---

## Check the `.env` file

```bash
ls -la /DATA/Applications/Navidrome_Mix/
```

The `.env` file should exist.

Expected permissions:

```text
-rw------- ... .env
```

---

## Systemd cannot find Python

Check:

```bash
which python3
```

The systemd service currently expects:

```text
/usr/bin/python3
```

Verify:

```bash
ls -l /usr/bin/python3
```

If Python is installed somewhere else, update the `ExecStart` paths in the service files.

---

## Navidrome connection failure

Verify Navidrome is running and listening on the configured URL.

The default configuration is:

```text
http://127.0.0.1:4533
```

Check the `.env`:

```bash
grep NAVIDROME_URL /DATA/Applications/Navidrome_Mix/.env
```

Do not print the password.

Then inspect the systemd log:

```bash
sudo journalctl -u navidrome-daily-mix.service -n 200 --no-pager
```

---

# Updating the Python Script

After changing `src/daily_mix.py`, no systemd daemon reload is normally required.

The next service execution will use the updated Python file.

You can immediately test it with:

```bash
sudo systemctl start navidrome-daily-mix.service
```

If the systemd service definition itself changes, run:

```bash
sudo systemctl daemon-reload
```

---

# Updating the Schedule

If you change:

```text
navidrome-daily-mix.timer
```

or:

```text
navidrome-weekly-mix.timer
```

run:

```bash
sudo systemctl daemon-reload
```

Then:

```bash
sudo systemctl restart navidrome-daily-mix.timer
sudo systemctl restart navidrome-weekly-mix.timer
```

Verify:

```bash
systemctl list-timers --all | grep navidrome
```

---

# Persistent Timers

Both timers use:

```ini
Persistent=true
```

This means systemd remembers the scheduled execution.

If the server is powered off when a scheduled run should have happened, systemd can run the missed job when the server comes back online.

---

# Useful Commands

## Run a daily mix manually

```bash
cd /DATA/Applications/Navidrome_Mix

set -a
source .env
set +a

python3 daily_mix.py daily balanced
```

## Run all daily mixes

```bash
python3 daily_mix.py daily discovery
python3 daily_mix.py daily radio
python3 daily_mix.py daily deep
python3 daily_mix.py daily balanced
```

## Run all weekly mixes

```bash
python3 daily_mix.py weekly discovery
python3 daily_mix.py weekly radio
python3 daily_mix.py weekly deep
python3 daily_mix.py weekly balanced
```

## Run the systemd daily job now

```bash
sudo systemctl start navidrome-daily-mix.service
```

## Run the systemd weekly job now

```bash
sudo systemctl start navidrome-weekly-mix.service
```

## View scheduled jobs

```bash
systemctl list-timers --all | grep navidrome
```

## View daily logs

```bash
sudo journalctl -u navidrome-daily-mix.service -n 200 --no-pager
```

## View weekly logs

```bash
sudo journalctl -u navidrome-weekly-mix.service -n 200 --no-pager
```

## Reload systemd after configuration changes

```bash
sudo systemctl daemon-reload
```

---

# Current Architecture

```text
                    ┌─────────────────────────┐
                    │       systemd timer     │
                    └────────────┬────────────┘
                                 │
                    scheduled execution
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │     systemd service     │
                    └────────────┬────────────┘
                                 │
                         loads .env
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │      daily_mix.py       │
                    └────────────┬────────────┘
                                 │
                     Navidrome REST API
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │       Navidrome        │
                    │                         │
                    │ Daily Mix playlists     │
                    │ Weekly Mix playlists    │
                    └─────────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │       history.json      │
                    │                         │
                    │ Generated track history │
                    └─────────────────────────┘
```

## Summary

The system is designed around two layers:

**Python**

Handles:

* Selecting songs
* Scoring songs
* Artist/album diversity
* Favorite tracks
* Recent-generation avoidance
* Creating/updating Navidrome playlists
* Maintaining `data/history.json`

**systemd**

Handles:

* Scheduling
* Automatic startup
* Loading `.env`
* Running the Python script
* Logging
* Missed scheduled executions
* Service status

The Python application does not need to know anything about the schedule. systemd controls when it runs.
