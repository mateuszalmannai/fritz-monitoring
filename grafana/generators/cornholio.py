"""Generates grafana/provisioning/dashboards/json/cornholio.json: health of the stack itself.
Backups (cornholio_backup_* from backup/backup.sh via the node_exporter textfile collector),
monitoring targets, fritz-extras, and the Pi's key values (same queries as the alert rules)."""
import json, sys

DS = {"type": "prometheus", "uid": "prometheus"}
_ids = iter(range(1, 1000))
panels, Y = [], [0]
H = 3600

def tgt(expr, legend="", ref="A", instant=False):
    t = {"datasource": DS, "expr": expr, "legendFormat": legend, "refId": ref}
    t.update(instant=True, range=False) if instant else t.update(range=True, instant=False)
    return t

def place(p, x, w, h):
    p.update(id=next(_ids), datasource=DS, gridPos={"x": x, "y": Y[0], "w": w, "h": h})
    panels.append(p)

def row(title):
    panels.append({"type": "row", "title": title, "collapsed": False, "id": next(_ids),
                   "gridPos": {"x": 0, "y": Y[0], "w": 24, "h": 1}, "panels": []})
    Y[0] += 1

def steps(*pairs):
    """pairs: (from_value, color); the first value is the base (None)."""
    return {"mode": "absolute", "steps": [{"color": c, "value": v} for v, c in pairs]}

def mapping(*pairs):
    return [{"type": "value", "options": {str(v): {"text": t, "color": c, "index": i} for i, (v, t, c) in enumerate(pairs)}}]

def stat(title, targets, unit="none", thresholds=None, desc="", decimals=None, mappings=None,
         color_mode="value", text_mode="auto", orient="auto"):
    d = {"unit": unit, "mappings": mappings or [], "color": {"mode": "thresholds"},
         "thresholds": thresholds or steps((None, "text"))}
    if decimals is not None: d["decimals"] = decimals
    return {"type": "stat", "title": title, "description": desc, "targets": targets,
            "options": {"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
                        "colorMode": color_mode, "graphMode": "none", "textMode": text_mode, "justifyMode": "center",
                        "orientation": orient, "wideLayout": True, "showPercentChange": False},
            "fieldConfig": {"defaults": d, "overrides": []}}

def ts(title, targets, unit="none", desc="", overrides=None, thresholds=None, interp="stepAfter", fill=10, minv=0):
    custom = {"drawStyle": "line", "lineWidth": 2, "fillOpacity": fill, "showPoints": "never", "lineInterpolation": interp,
              "spanNulls": False, "axisSoftMin": minv,
              "thresholdsStyle": {"mode": "line+area" if thresholds else "off"}}
    d = {"unit": unit, "custom": custom, "color": {"mode": "palette-classic"}}
    if thresholds: d["thresholds"] = thresholds
    return {"type": "timeseries", "title": title, "description": desc, "targets": targets,
            "options": {"legend": {"showLegend": True, "placement": "bottom", "displayMode": "table", "calcs": ["lastNotNull"]},
                        "tooltip": {"mode": "multi", "sort": "none"}},
            "fieldConfig": {"defaults": d, "overrides": overrides or []}}

def right_axis(name, unit, color):
    return {"matcher": {"id": "byName", "options": name}, "properties": [
        {"id": "unit", "value": unit}, {"id": "custom.axisPlacement", "value": "right"},
        {"id": "color", "value": {"mode": "fixed", "fixedColor": color}}]}

def color(name, c):
    return {"matcher": {"id": "byName", "options": name}, "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": c}}]}

# ---------------------------------------------------------------- Backups
row("Backups")
AGE = "time() - cornholio_backup_last_success_timestamp_seconds"
age_steps = steps((None, "green"), (26 * H, "orange"), (36 * H, "red"))
bk = "Written by backup/backup.sh after each successful run (nightly 03:30, restic to the Synology). "
place(stat("Last successful backup", [tgt(AGE, instant=True)], "dtdurations", age_steps, decimals=1,
           desc=bk + "Time since then. Orange after 26 h (last night's run missing), red after 36 h (the 'Backup overdue' alert fires)."), 0, 4, 4)
place(stat("Duration", [tgt("cornholio_backup_duration_seconds", instant=True)], "s",
           desc=bk + "Includes stopping and starting Grafana and Prometheus; on Sundays also the repository check."), 4, 4, 4)
place(stat("Snapshots", [tgt("cornholio_backup_snapshots", instant=True)], decimals=0,
           desc=bk + "Snapshots kept: 7 daily, 4 weekly, 12 monthly, so up to ~23 once the backups are a year old."), 8, 4, 4)
place(stat("Repository size (NAS)", [tgt("cornholio_backup_repository_size_bytes", instant=True)], "bytes", decimals=1,
           desc=bk + "Space all snapshots take on the Synology (deduplicated and compressed)."), 12, 4, 4)
place(stat("Backed-up data", [tgt("cornholio_backup_source_size_bytes", instant=True)], "bytes", decimals=1,
           desc=bk + "Size of the latest snapshot: what a full restore brings back."), 16, 4, 4)
place(stat("New data, last run", [tgt("cornholio_backup_data_added_bytes", instant=True)], "bytes", decimals=1,
           desc=bk + "What the latest run actually added to the repository (compressed); restic only stores changes."), 20, 4, 4)
Y[0] += 4
place(ts("Time since last successful backup", [tgt(AGE, "Since last backup")], "s", interp="linear",
         thresholds=steps((None, "transparent"), (36 * H, "red")),
         desc="Rises until each backup, then drops to 0: one tooth per successful run. Red area: the 36 h alert limit."), 0, 12, 8)
place(ts("Backup size", [tgt("cornholio_backup_repository_size_bytes", "Repository on the NAS", "A"),
                         tgt("cornholio_backup_source_size_bytes", "Backed-up data (latest snapshot)", "B")], "bytes",
         desc=bk + "The repository grows slowly while snapshots accumulate, then levels off as old ones are pruned.",
         overrides=[color("Repository on the NAS", "blue"), color("Backed-up data (latest snapshot)", "green")]), 12, 12, 8)
Y[0] += 8
place(ts("Per run: duration and new data", [tgt("cornholio_backup_duration_seconds", "Duration", "A"),
                                            tgt("cornholio_backup_data_added_bytes", "New data", "B")], "s", desc=bk,
         overrides=[color("Duration", "orange"), right_axis("New data", "bytes", "purple")]), 0, 24, 7)
Y[0] += 7

# ---------------------------------------------------------------- Monitoring
row("Monitoring")
UPMAP = mapping((1, "Up", "green"), (0, "Down", "red"))
place(stat("Scrape targets", [tgt('up{job!="speedtest"}', "{{job}} {{instance}}", "A", instant=True),
                              tgt('last_over_time(up{job="speedtest"}[8h30m])', "speedtest (last test)", "B", instant=True)],
           mappings=UPMAP, color_mode="background", text_mode="value_and_name",
           thresholds=steps((None, "red"), (1, "green")),
           desc="Whether Prometheus could read each target at its last scrape (up). The speed test is read only every 8 h."), 0, 18, 8)
place(stat("fritz-extras", [tgt("fritz_extras_up", "{{source}}", "A", instant=True)],
           mappings=mapping((1, "OK", "green"), (0, "Failing", "red")), color_mode="background", text_mode="value_and_name",
           thresholds=steps((None, "red"), (1, "green")), orient="horizontal",
           desc="Whether the add-on's last fetch of each source worked (hosts = device list, system = CPU/RAM/energy)."), 18, 6, 8)
Y[0] += 8

# ---------------------------------------------------------------- Pi
row("Raspberry Pi")
pi = "Same queries as the alert rules. Full details: dashboard 1860 (Node Exporter Full)."
place(stat("CPU temperature", [tgt("max(node_thermal_zone_temp)", instant=True)], "celsius",
           steps((None, "green"), (65, "orange"), (75, "red")), decimals=0, desc=pi + " Alert at 75 °C."), 0, 5, 4)
place(stat("SSD used", [tgt('100 * (1 - node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})', instant=True)],
           "percent", steps((None, "green"), (70, "orange"), (80, "red")), decimals=0, desc=pi + " Alert at 80 %."), 5, 5, 4)
place(stat("RAM used", [tgt("100 * (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)", instant=True)],
           "percent", steps((None, "green"), (80, "orange"), (90, "red")), decimals=0, desc=pi), 10, 5, 4)
place(stat("Load (1 min)", [tgt("node_load1", instant=True)], decimals=2,
           thresholds=steps((None, "green"), (3, "orange"), (4, "red")), desc=pi + " 4 cores: up to ~4 is busy but fine."), 15, 4, 4)
place(stat("Uptime", [tgt("time() - node_boot_time_seconds", instant=True)], "dtdurations", decimals=1, desc=pi), 19, 5, 4)
Y[0] += 4

dash = {"uid": "cornholio-stack", "title": "cornholio", "tags": ["cornholio"],
        "description": "Health of the monitoring stack itself: backups, scrape targets, fritz-extras, the Pi.",
        "timezone": "browser", "editable": False, "graphTooltip": 1, "schemaVersion": 41, "version": 1,
        "refresh": "1m", "time": {"from": "now-7d", "to": "now"}, "templating": {"list": []},
        "annotations": {"list": []},
        "links": [{"title": "FRITZ!Box", "type": "link", "url": "/d/cornholio-fritzbox", "icon": "dashboard"},
                  {"title": "Speedtest", "type": "link", "url": "/d/cornholio-speedtest", "icon": "dashboard"}],
        "panels": panels}
OUT = sys.argv[1] if len(sys.argv) > 1 else "grafana/provisioning/dashboards/json/cornholio.json"
json.dump(dash, open(OUT, "w"), indent=2); open(OUT, "a").write("\n")
print(len(panels), "panels,", sum(len(p.get("targets", [])) for p in panels), "queries")
