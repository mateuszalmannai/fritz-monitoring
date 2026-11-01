#!/bin/bash
# Nightly restic backup of the stack to the Synology (run as root by cornholio-backup.timer).
#
# Backs up: the Docker volumes (Grafana, Prometheus, Pi-hole), a Pi-hole Teleporter export and
# this project folder including the env files (the repository is encrypted).
# Grafana and Prometheus are stopped for the duration of the copy so their databases are
# consistent; Pi-hole keeps running so DNS never goes down.
#
# Results:
#   - node_exporter textfile metrics cornholio_backup_* (last success, duration, repository size,
#     snapshot count, size of the backed-up data, new data per run); Grafana alerts when the last
#     success is older than 36 h, the "cornholio" dashboard shows them
#   - ntfy push notification on failure
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
export RESTIC_REPOSITORY="sftp:backup-nas:/backup/cornholio"   # host alias in /root/.ssh/config
export RESTIC_PASSWORD_FILE=/etc/restic/password
export RESTIC_CACHE_DIR=/var/cache/restic
STAGING=/var/backups/cornholio
TEXTFILE_DIR=/var/lib/node_exporter/textfile
COMPOSE=(docker compose --project-directory "$PROJECT_DIR")

notify_failure() {
    local topic
    topic=$(sed -n 's/^NTFY_TOPIC=//p' "$PROJECT_DIR/grafana.env" 2>/dev/null || true)
    [ -n "$topic" ] || return 0
    curl -fsS -m 15 -H "Title: Backup failed on cornholio" -H "Tags: warning" \
        -d "restic backup failed (exit $1). Check: journalctl -u cornholio-backup" \
        "https://ntfy.sh/$topic" >/dev/null || true
}

# Repository size, snapshot count and the latest snapshot's sizes, as metric lines.
# Read-only (--no-lock), < 1 s each. Prints nothing if restic or the JSON fails: these
# values are nice to have and must never fail the backup.
repo_metrics() {
    python3 - <<'PY' || true
import json, subprocess
def restic(*args):
    out = subprocess.run(["restic", *args, "--json", "--no-lock"], capture_output=True, text=True, check=True).stdout
    return json.loads(out.strip().splitlines()[-1])
try:
    stats = restic("stats", "--mode", "raw-data")
    snaps = restic("snapshots", "--tag", "cornholio", "--host", "cornholio")
    summary = max(snaps, key=lambda s: s["time"]).get("summary", {})
except Exception:
    raise SystemExit(0)
metrics = [
    ("repository_size_bytes", "Size of the restic repository on the NAS (deduplicated, compressed).", stats.get("total_size")),
    ("snapshots", "Number of snapshots kept in the repository.", len(snaps)),
    ("source_size_bytes", "Size of the data in the latest snapshot (what a full restore brings back).", summary.get("total_bytes_processed")),
    ("data_added_bytes", "New data the latest run stored in the repository (compressed).", summary.get("data_added_packed", summary.get("data_added"))),
]
for name, help_text, value in metrics:
    if value is not None:
        print(f"# HELP cornholio_backup_{name} {help_text}\n# TYPE cornholio_backup_{name} gauge\ncornholio_backup_{name} {value}")
PY
}

write_metric() {
    local duration=$SECONDS extra
    extra=$(repo_metrics)
    mkdir -p "$TEXTFILE_DIR"
    # Write to a temp file and rename, so node_exporter never reads a half-written file.
    cat > "$TEXTFILE_DIR/backup.prom.$$" <<EOF
# HELP cornholio_backup_last_success_timestamp_seconds Time of the last successful restic backup.
# TYPE cornholio_backup_last_success_timestamp_seconds gauge
cornholio_backup_last_success_timestamp_seconds $(date +%s)
# HELP cornholio_backup_duration_seconds Duration of the last successful backup run.
# TYPE cornholio_backup_duration_seconds gauge
cornholio_backup_duration_seconds $duration
$extra
EOF
    mv "$TEXTFILE_DIR/backup.prom.$$" "$TEXTFILE_DIR/backup.prom"
}

stopped=()
cleanup() {
    local rc=$?
    # Always bring stopped services back, even if the backup failed.
    if [ ${#stopped[@]} -gt 0 ]; then
        "${COMPOSE[@]}" start "${stopped[@]}" || rc=1
    fi
    [ $rc -eq 0 ] || notify_failure $rc
    exit $rc
}
trap cleanup EXIT

volume_path() { docker volume inspect -f '{{.Mountpoint}}' "fritz-monitoring_$1"; }

# Create the repository on the first run.
restic cat config >/dev/null 2>&1 || restic init

# Pi-hole Teleporter export (settings, lists, groups) as an easy-to-restore ZIP.
rm -rf "$STAGING" && mkdir -p "$STAGING"
zip=$(docker exec -w /tmp pihole pihole-FTL --teleporter | tail -1)
docker cp "pihole:/tmp/$zip" "$STAGING/pihole-teleporter.zip"
docker exec pihole rm -f "/tmp/$zip"

echo "Stopping grafana and prometheus for a consistent copy"
stopped=(grafana prometheus)
"${COMPOSE[@]}" stop "${stopped[@]}"

restic backup --tag cornholio --host cornholio \
    "$(volume_path grafana-data)" \
    "$(volume_path prometheus-data)" \
    "$(volume_path pihole-data)" \
    "$STAGING" \
    "$PROJECT_DIR"

"${COMPOSE[@]}" start "${stopped[@]}"
stopped=()

# Retention: 7 daily, 4 weekly, 12 monthly snapshots.
restic forget --tag cornholio --host cornholio \
    --keep-daily 7 --keep-weekly 4 --keep-monthly 12 --prune

# Sundays: verify the repository structure and read back 5 % of the data.
if [ "$(date +%u)" = 7 ]; then
    restic check --read-data-subset=5%
fi

write_metric
echo "Backup finished in ${SECONDS}s"
