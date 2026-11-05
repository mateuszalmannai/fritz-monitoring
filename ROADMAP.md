# Roadmap: what else runs on cornholio

Extensions in line with the existing stack (fritz_exporter → Prometheus → Grafana, Pi-hole).
Tick items off as they're done; add the date.

## Done
- [x] FRITZ!Box monitoring: fritz_exporter, Prometheus, Grafana, dashboard 13983 (2026-10-10)
- [x] Pi-hole as LAN DNS, upstream FRITZ!Box (2026-10-10)
- [x] Pi-hole tuning review (2026-11-05): blocklist switched from StevenBlack to HaGeZi Multi PRO
      (77k → 222k domains). Cache size, serve-stale and query history (91 days) left as they are;
      see `docs/pihole-tuning.md` for the measurements.

## Next
- [x] **node_exporter**: health of the Pi itself (CPU temperature, load, RAM, SSD usage, network).
      Grafana dashboard 1860 (Node Exporter Full). (2026-10-10)
- [x] **blackbox_exporter**: internet quality from inside the LAN: ping latency/packet loss to the
      FRITZ!Box and the internet, DNS response time through Pi-hole, HTTP checks.
      Grafana dashboard 7587 (Prometheus Blackbox Exporter). (2026-10-10)
- [x] **Alerts via Grafana alerting** (built in, no extra container) → push via ntfy.sh. Rules: internet
      down, FRITZ!Box unreachable, Pi-hole DNS down, monitoring target down, SSD > 80 %, CPU > 75 °C
      (plus "Backup overdue", added with the backups).
      Provisioned from `grafana/provisioning/alerting/`. (2026-10-10)

## Later
- [x] **Pi-hole metrics in Grafana**: `ekofr/pihole-exporter:v1.2.0` (Pi-hole v6 support since v1.0),
      logs in with a Pi-hole app password from `pihole-exporter.env`. Grafana dashboard 10176. (2026-10-10)
- [x] **Backups**: nightly restic (03:30) over SFTP to the Synology share `backup` (dedicated DSM user
      `cornholio-backup`, no access to other shares). Volumes, Pi-hole Teleporter export, project incl.
      env files. Keeps 7 daily / 4 weekly / 12 monthly. Alert "Backup overdue" after 36 h. Test restore
      passed. (2026-10-10)
- [x] **Diun**: weekly check (Mon 09:00) for new image versions → ntfy (low priority). Moving tags
      report new digests, `diun.include_tags` labels report new tags. Doesn't update anything. (2026-10-10)
- [x] **Speedtest exporter**: `miguelndecarvalho/speedtest-exporter:v3.5.4` (Ookla CLI), one test per
      Prometheus scrape, every 4 h (scrape_timeout 100 s). Grafana dashboard 13665. (2026-10-10) Every 8 h since 2026-10-12
      (readings hardly vary).
- [x] **Bespoke FRITZ!Box dashboard** (`grafana/generators/fritzbox.py` → `json/fritzbox.json`): all 45 metrics
      of the 7590 AX, styled after the liked dashboards 12579, 13377, 13848, 17751, 24649. Based on the
      survey of all 17 FRITZ!Box dashboards on grafana.com (`FRITZ-METRICS.md`). (2026-10-11)
- [x] `FRITZ_WIFI_CLIENT_INFO=true`: per-client Wi-Fi signal and link speed, scrape ~7 s (2026-10-11)
- [x] **fritz-extras** add-on (`fritz-extras/fritz_extras.py`): online devices by name (TR-064 host list, every
      5 min, all devices named, optional `DEVICE_ALLOWLIST`), CPU temperature/load, RAM and energy use (web UI
      `data.lua`, every 2 min). Dashboard sections "FRITZ!Box system" and "Devices". (2026-10-11)
- [x] **cornholio dashboard** (`grafana/generators/cornholio.py`): backups (incl. new metrics for repository
      size, snapshot count, backed-up data, new data per run from `backup.sh`), scrape targets, fritz-extras,
      Pi basics. (2026-10-12)

All planned items are done. New ideas go into a new section here.

## Open follow-ups
- [x] Own **Speedtest** dashboard, provisioned (`grafana/provisioning/dashboards/json/speedtest.json`),
      with the DSL sync rate as reference. Replaces 13665, whose plain queries stay empty at a 4-h
      interval. (2026-10-10)
- [ ] Review the speed tests after a few days, including night-time values. First test (2026-10-10,
      evening): 58.7 / 21.4 Mbit/s vs. current DSL sync 63.7 / 23.4 (~92 %, normal). The line could
      sync at ~133 / 52 (`type="max"`), so the tariff/profile is the limit, not the line.

## Decided against
- **Unbound** (recursive DNS): conflicts with "FRITZ!Box as Pi-hole upstream", little gain. Rechecked
  2026-11-05: uncached answers via the FRITZ!Box take ~11 ms, recursion would take 50–150 ms.
- **Bigger Pi-hole cache** (2026-11-05): 10 000 entries, 0 evictions; larger sizes slow lookups.
- **365-day Pi-hole query history** (2026-11-05): Prometheus already keeps a year of aggregate stats;
  a year of per-device domain history isn't worth the privacy cost. Stays at 91 days.
- **cAdvisor** (per-container metrics): too heavy on a Pi for what it shows.
- **Watchtower** (automatic updates): conflicts with pinned image versions.
- **Powerline throughput test** (iperf3, 2026-10-13): the only device at the far adapter is a Raspberry Pi 2 (100 Mbit/s Ethernet), which would cap every result at ~94 Mbit/s. The mesh panels keep the powerline PHY rate. Worth it only with a gigabit device there.
