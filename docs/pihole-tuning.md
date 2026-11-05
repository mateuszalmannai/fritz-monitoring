# Pi-hole tuning plan (cornholio)

Revised version of an external tuning guide, adapted to this stack: Pi-hole v6 runs **in Docker**
(`pihole/pihole:2026.09.0`) and forwards to the FRITZ!Box. Measured on 2026-11-05.

## Starting point

| Measurement | Value |
|---|---|
| Cached answer (`dig` inside the container) | 0 ms |
| Uncached answer (forwarded to the FRITZ!Box) | ~11 ms |
| blackbox DNS probe `pihole:53`, 7-day avg / p95 | 1.4 ms / 4.9 ms |
| Cache: size / insertions / **evictions** | 10 000 / 283 955 / **0** |
| Blocklists | 1 (StevenBlack hosts), 76 737 domains |
| Regex filters | none (1 exact allow entry) |
| Query database | 44 MB for ~26 days, `maxDBdays` 91 |

DNS is already fast. The cache has never evicted anything, so it isn't too small.

## What we take from the guide, and what we don't

| Guide step | Decision | Why |
|---|---|---|
| Cache size 100 000 | **No** | 0 evictions. Pi-hole's docs warn that lookups get slower above ~10 000 entries. |
| `dns.cache.optimizer 3600` | Already set | It's the default. |
| Query logging on | Already set | |
| `maxDBdays 365` | **Optional** (decide) | ~600 MB a year on the SSD. Gives a longer history; doesn't make DNS faster. |
| One large blocklist (HaGeZi / OISD) | **Optional** (decide) | Better blocking, not speed. Larger lists cost nothing at query time. |
| Regex review | Nothing to do | No regex filters. |
| **Unbound** | **No** | Already rejected in `ROADMAP.md`. It makes uncached lookups *slower* (50–150 ms recursive vs ~11 ms via the FRITZ!Box), skips the FRITZ!Box's upstream/DoT settings, and the guide's `127.0.0.1#5335` doesn't work from inside the Pi-hole container. |
| Weekly gravity update | Already the case | The image's own cron. |

The guide's commands also don't fit as written: there's no `pihole-FTL` systemd unit, `dig` isn't on
the host (use it inside the container, or from the Mac), `/etc/pihole/gravity.db` doesn't exist on the
host (it's in the `pihole-data` volume; host `sqlite3` is installed, but editing the live database from
outside the container is best avoided), and settings changed with `pihole-FTL --config` are overridden
by the `FTLCONF_*` variables in `docker-compose.yml`. Settings belong in `docker-compose.yml`; lists go through the web UI.

## Decisions (2026-11-05)

1. **Blocklist:** HaGeZi **Pro** added, StevenBlack disabled (not deleted). Done the same day:
   222 452 domains, gravity rebuilt without errors, cached 0 ms / uncached 0–3 ms afterwards.
2. **Query history:** stays at 91 days, so step 2 below was skipped.

## Steps (only for what was chosen)

All commands run from the Mac in `~/scripts/fritz-monitoring` unless noted.

### 1. Backup
The nightly restic run already includes a Teleporter export. For a fresh one right before the change:

```bash
ssh cornholio 'sudo systemctl start cornholio-backup.service && systemctl status --no-pager cornholio-backup.service | tail -3'
```

### 2. Query history (if 365 days)
Add to the `pihole` service environment in `docker-compose.yml`:

```yaml
      # Keep one year of query history (~600 MB on the SSD), same as Prometheus.
      FTLCONF_database_maxDBdays: "365"
```

Deploy and recreate:

```bash
rsync -a --exclude '*.env' --exclude .claude --exclude .git ./ cornholio:fritz-monitoring/
ssh cornholio 'cd ~/fritz-monitoring && docker compose up -d pihole'
```

**Verify:** `docker compose exec -T pihole pihole-FTL --config database.maxDBdays </dev/null` → `365`, container `healthy`.

### 3. Blocklist (if changing)
In the web UI (`http://192.168.178.27:8080/admin` → Lists):
1. Add the chosen list:
   - HaGeZi Pro: `https://raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/pro.txt`
   - HaGeZi Pro++: `https://raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/pro.plus.txt`
   - OISD Big: `https://big.oisd.nl`
2. Disable (don't delete) StevenBlack.
3. Tools → Update Gravity (or `docker compose exec -T pihole pihole -g </dev/null` on the Pi).

The list lives in `gravity.db` in the `pihole-data` volume, so it's covered by the backup. Leave the
existing allow entry alone.

**Verify:** gravity update without errors; "Domains on lists" changed on the dashboard; `dig +short
@192.168.178.27 example.com` from the Mac answers; a few everyday sites still work.

**Rollback:** re-enable StevenBlack, disable the new list, update gravity. If sites break, allowlist the
blocked domain from the Query Log first instead of switching lists.

### 4. Measure again
```bash
ssh cornholio 'cd ~/fritz-monitoring && docker compose exec -T pihole sh -c "for i in 1 2; do for d in example.com github.com wikipedia.org reddit.com bbc.co.uk; do dig @127.0.0.1 \$d | grep \"Query time\"; done; done; dig +short chaos txt evictions.bind @127.0.0.1" </dev/null'
```
Expect the same as before (0 ms cached, ~11 ms uncached, 0 evictions). The Grafana blackbox panel for
`pihole:53` shows the long-term picture.

### 5. Docs
- `README.md`: note the blocklist and history setting in the Pi-hole section.
- `ROADMAP.md`: record the result under "done" / "decided against" (cache size, Unbound confirmed).
