---
description: Guided setup of the monitoring stack (FRITZ!Box, Pi-hole, alerts, backups) on the Raspberry Pi
---
Set up this project on the Raspberry Pi, following CLAUDE.md and README.md. Work step by step and confirm each before moving on. Never print the env files or `/etc/restic/password`, and don't ask me to paste passwords into the chat.

1. **Host check:** confirm whether we're on the Pi or reach it via `ssh cornholio` (see CLAUDE.md → Working from the Mac). Check `uname -m` is `aarch64`, the OS version, passwordless sudo (`sudo -n true`), whether Docker + compose plugin are installed, and where the root filesystem and the SSD are mounted (`lsblk -f`, `findmnt /`).
2. **Fresh install or restore?** Ask whether this is a first setup or a reinstall with backups on the Synology. For a restore, follow README → Backups → "After a full reinstall" instead of creating new env files and volumes in steps 5–7 (Docker must be installed first).
3. **Storage:** decide whether the Pi boots from the SSD (case A) or the SD card (case B). For case B, show me the exact fstab line, daemon.json and systemd drop-in you'd apply, and wait for my OK before changing anything.
4. **Docker:** install it via get.docker.com if missing (ask first), and add my user to the `docker` group.
5. **Project and credentials:** copy the project to `~/fritz-monitoring` on the Pi (rsync, without `*.env` and `.claude`). Create each missing env file from its `.example` with mode 600 (README step 4):
   - `fritz.env`: I fill it in myself. Remind me of the FRITZ!Box steps: monitoring user with "FRITZ!Box Settings" permission, password max. 32 characters, "Allow access for applications". `DEVICE_ALLOWLIST` (fritz-extras) stays empty unless I want only some devices named.
   - `pihole.env`: I set the Pi-hole web password myself.
   - `grafana.env`: generate a random `NTFY_TOPIC` without printing it; I read it on the Pi for the ntfy app.
   - `pihole-exporter.env`: needs a Pi-hole *app password*, which only exists after Pi-hole's first start (step 7).
6. **Grafana password:** remind me that `admin` / `change-me-on-first-login` must be changed at the first login.
7. **Start:** `docker compose up -d`. Then have me create the Pi-hole app password and fill in `pihole-exporter.env`, and run `docker compose up -d pihole-exporter`. Run every check in CLAUDE.md → Verify and report the results.
8. **LAN DNS and notifications:** remind me to set the Pi's IP as "Local DNS server" in the FRITZ!Box (never as its upstream DNS), and to subscribe to the ntfy topic. Send a test via Grafana → Alerting → Contact points → ntfy, and `docker compose exec diun diun notif test`.
9. **Backups:** if the Synology side isn't set up yet, walk me through README → Backups → Setup. Install and enable `cornholio-backup.timer`, run one backup (`sudo systemctl start cornholio-backup`) and check that the `cornholio_backup_last_success_timestamp_seconds` metric is present. Remind me to keep the restic password in my password manager.
10. **Finish:** tell me the URLs (Grafana `http://<pi-ip>:3000`, Pi-hole `http://<pi-ip>:8080/admin`) and the dashboards to import (README → Using it: 13983, 17751, 1860, 7587, 10176); the cornholio, FRITZ!Box and Speedtest dashboards are provisioned automatically (folder cornholio).

$ARGUMENTS
