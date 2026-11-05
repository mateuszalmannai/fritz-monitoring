# FRITZ!Box monitoring stack

Docker Compose stack that monitors a FRITZ!Box: **fritz_exporter → Prometheus → Grafana**, plus **Pi-hole** as the LAN's DNS ad blocker.
Our own add-on **fritz-extras** (`fritz-extras/fritz_extras.py`) adds online devices by name, CPU temperature/load, RAM, energy use and the mesh backhaul path (repeater behind powerline, which fritz_exporter can't see).
Prometheus also scrapes **node_exporter** (the Pi's own health), **blackbox_exporter** (ping/DNS/HTTP probes), **pihole-exporter** (Pi-hole statistics) and **speedtest-exporter** (Ookla speed test every 8 h).
**Diun** sends weekly image-update notifications; a systemd timer runs nightly restic backups to the Synology.
Planned extensions are tracked in `ROADMAP.md`.
Target host: Raspberry Pi 4 Model B `cornholio` (board rev 1.4, 8 GB RAM, 4 cores; 192.168.178.27, fixed in the FRITZ!Box, user `pi`, passwordless sudo), 64-bit Raspberry Pi OS (Debian 13 trixie), booting from an external USB SSD (case A).

## Working from the Mac
Claude Code usually runs on the Mac in `~/scripts/fritz-monitoring` and reaches the Pi with `ssh cornholio` (Secretive key, see `REINSTALL-PI.md`). The project lives at `~/fritz-monitoring` on the Pi.
- Deploy: `rsync -a --exclude '*.env' --exclude .claude --exclude .git ./ cornholio:fritz-monitoring/`. The real `*.env` files exist only on the Pi (mode 600); never overwrite them.
- After rsyncing `prometheus.yml` or `blackbox.yml`, restart the container (`docker compose restart prometheus`): rsync replaces the file, and the bind mount keeps the old inode.
- `docker compose exec` inside `ssh ... '...'` or a heredoc swallows stdin; append `</dev/null` (or use `-T`).
- If `ssh cornholio` fails with "Permission denied (publickey)", the Secretive agent is unavailable (e.g. Mac locked); ask the user rather than adding other keys.

## Files
- `docker-compose.yml`: all services, named volumes, log rotation
- `fritz.env.example`: template for FRITZ!Box credentials (used by fritz-exporter and fritz-extras) and `DEVICE_ALLOWLIST`. Copy to `fritz.env` (git-ignored)
- `fritz-extras/fritz_extras.py`: the add-on (Python stdlib only, runs in `python:3.13-alpine`, script mounted read-only). Fetches on its own timers, serves cached values on :9788.
- `pihole.env.example`: template for the Pi-hole web password. Copy to `pihole.env` (git-ignored)
- `pihole-exporter.env.example`: template for the Pi-hole *app password* used by pihole-exporter. Copy to `pihole-exporter.env` (git-ignored)
- `grafana.env.example`: template for the ntfy topic (`NTFY_TOPIC`) used by alert notifications and Diun. Copy to `grafana.env` (git-ignored)
- `prometheus/prometheus.yml`: scrape config (60s interval, 30s timeout for the FRITZ!Box), incl. node, Pi-hole, speedtest (8h interval, 100s timeout) and blackbox probe targets
- `blackbox/blackbox.yml`: blackbox probe modules (icmp, dns_example, http_2xx)
- `grafana/provisioning/datasources/prometheus.yml`: auto-provisions the Prometheus data source (uid `prometheus`)
- `backup/`: `backup.sh` (restic to the Synology; writes `cornholio_backup_*` metrics incl. repository size and snapshot count via the node_exporter textfile collector), systemd `cornholio-backup.service` + `.timer` (installed to `/etc/systemd/system/`)
- `grafana/provisioning/alerting/`: alert rules, ntfy contact point and notification policy. Edit these files, not the Grafana UI (provisioned items are read-only there). Avoid `$` in their templates: Grafana expands `$VARS` from the environment and doesn't unescape `$$` in annotations, so use `.Values.A.Value` / `.Labels.job`, not `$values` / `$labels`.
- `grafana/provisioning/dashboards/`: provider + `json/*.json` dashboards (folder `cornholio`, read-only in the UI): `cornholio.json` (backups, scrape targets, fritz-extras, Pi), `fritzbox.json` (all 45 FRITZ!Box metrics plus the `fritz_extras_*` metrics) and `speedtest.json` (queries use `last_over_time(...[8h30m])` because of the 8h scrape interval).
- `grafana/generators/`: `cornholio.py`, `fritzbox.py`, `speedtest.py` generate those JSON files. Edit the generator, not the JSON, then rerun it. The FRITZ!Box dashboard must keep showing every metric the box delivers (check against `FRITZ-METRICS.md` and the fritz-extras table in the README).
- `README.md`: manual setup steps for humans (keep it in sync when changing the stack)
- `ROADMAP.md`: extensions, done / decided against
- `FRITZ-METRICS.md`: metrics with values on this FRITZ!Box, pitfalls (rx/tx, curr vs. max sync rate), translation of other exporters' metric names. Never add label values like IPs, Wi-Fi names or the serial.
- `BREAK-GLASS.md`: switching the LAN's DNS back to the FRITZ!Box when the Pi is down, and back again
- `break-glass/fritz-dns`: Mac-side helper for it (Python stdlib; `check`, `open`, `mac-fritz`, `mac-reset`). FRITZ!OS 8.25 has no TR-064 setter for the LAN DNS server (only `GetDNSServers`), so the switch itself stays manual in the web UI. On `PATH` as `fritz-dns` via a relative symlink `~/bin/fritz-dns` (not synced; created per Mac): renaming or moving the script breaks it.
- `REINSTALL-PI.md`: reinstalling the Pi OS on the SSD, SSH access, bootloader recovery
- `.claude/commands/setup.md`: the `/setup` command

## Decisions already made (don't change without asking)
- Exporter: `pdreker/fritz_exporter:3`. Its v3 default listen address is 127.0.0.1, so `FRITZ_LISTEN_ADDRESS=0.0.0.0` is required inside Docker.
- Published ports: Grafana 3000, Pi-hole DNS 53 (tcp/udp) and Pi-hole web UI 8080. Prometheus and the exporters stay on the internal compose network.
- node_exporter runs with `network_mode: host` (to see eth0) but listens only on docker0 `172.17.0.1:9100`, not the LAN. Prometheus reaches it as `host.docker.internal` (`extra_hosts: host-gateway`).
- Pi-hole: image pinned to a release tag (`pihole/pihole:YYYY.MM.N`), upstream DNS is the FRITZ!Box (192.168.178.1). Clients get the Pi as DNS server via the FRITZ!Box DHCP setting "Local DNS server"; the FRITZ!Box itself must never use Pi-hole as its upstream (loop).
- Pi-hole blocklist (since 2026-11-05): **HaGeZi Multi PRO** only (`hagezi/dns-blocklists/main/adblock/pro.txt`); StevenBlack stays in the list table but disabled. Lists live in `gravity.db` in the `pihole-data` volume, not in the repo. If a site breaks, allowlist the domain rather than switching lists. Cache size stays at 10 000 (0 evictions) and query history at 91 days; Unbound stays rejected (see `docs/pihole-tuning.md`).
- `FRITZ_WIFI_CLIENT_INFO=true` (since 2026-10-11): per-client Wi-Fi signal/speed, labels `client_ip`, `client_mac`, `wifi_name`; no device names. Scrape ~7 s.
- FRITZ!Box dashboards: **13983** (general) and **17751** (DSL line quality, PPP, Wi-Fi), both tested by the user. `FRITZ_HOST_INFO` stays false: only 17751's per-device panels need it, and it's slow (20+ s per scrape instead of ~5 s) and loads the router. If enabling it, raise `scrape_timeout` to ~45s.
- Speedtest: each scrape of `speedtest-exporter` runs a real test (~250 MB), so its job has `scrape_interval: 8h` (4h until 2026-10-12; the user found 3 tests a day enough). Don't shorten it much, and don't curl its `/metrics` casually.
- fritz-extras (since 2026-10-11): devices via TR-064 `X_AVM-DE_GetHostListPath` every 5 min, system values via web UI `data.lua` (`ecoStat`, `energy`) every 2 min, reusing one login session (each login is an event-log entry on the box). The user chose to name **all** devices (presence history for 365 days); `DEVICE_ALLOWLIST` in `fritz.env` can restrict it. Device series are keyed by `name` + `mac` only; IP and interface live in `fritz_extras_host_info`, because offline devices lose them. Never print device names, IPs or MACs in chat or docs.
- Prometheus retention: 365d or 5GB, whichever comes first.
- Updates are manual: Docker images and OS packages (`unattended-upgrades` isn't installed; offered 2026-11-05, not decided). Only Pi-hole's gravity updates itself (cron in the container, Sundays 04:29). Diun (`crazymax/diun:4`) only notifies (ntfy, Mondays 09:00). Every service carries `diun.watch_repo`/`diun.include_tags` labels; when adding a service, add matching labels (`$$` for a literal `$` in compose). Pi-hole uses `diun.sort_tags: reverse` because its date tags (`2026.09.0`) aren't valid semver.
- Backups: restic over SFTP to `sftp:backup-nas:/backup/cornholio` (host alias in `/root/.ssh/config`, key `/root/.ssh/backup_ed25519`, DSM user `cornholio-backup` restricted to the `backup` share). Repository password in `/etc/restic/password` (root only; the user also keeps it in their password manager).
- All persistent data must live on the SSD, never the SD card. Either the Pi boots from the SSD, or Docker's `data-root` is `/mnt/ssd/docker` with a systemd `RequiresMountsFor=/mnt/ssd` drop-in (see README step 2B).

## Rules
- Never print, log or commit the contents of `fritz.env`, `pihole.env`, `grafana.env` (the ntfy topic is a secret), `pihole-exporter.env`, `/etc/restic/password` or any password.
- FRITZ!OS passwords are limited to 32 characters. Longer ones cause 401 errors.
- Ask before: formatting/partitioning disks, editing `/etc/fstab`, changing `/etc/docker/daemon.json`, or stopping Docker.
- After changes, verify (see below) rather than assuming success.

## Verify
```bash
docker compose ps                                     # all "running", pihole "healthy"
docker compose logs --tail=50 fritz-exporter          # no 401 / connection errors
docker compose exec prometheus wget -qO- http://fritz-exporter:9787/metrics | grep -c '^fritz_'   # > 0
docker compose exec prometheus wget -qO- http://fritz-extras:9788/metrics | grep '^fritz_extras_up'   # all three 1
docker compose exec prometheus wget -qO- 'http://localhost:9090/api/v1/targets' | grep -o '"health":"[a-z]*"'  # all "up" (speedtest may be "unknown" for up to 8 h after a Prometheus restart)
docker info --format '{{.DockerRootDir}}'             # on the SSD
dig +short @<pi-ip> example.com                       # Pi-hole answers (run from another LAN host)
```
Troubleshooting: a 401 means wrong credentials or a missing user permission. "Connection refused" from the exporter usually means "Allow access for applications" is off on the FRITZ!Box (Home Network → Network → Network Settings).
