"""Generates grafana/provisioning/dashboards/json/speedtest.json (speed tests every 8 h vs. DSL sync rate)."""
import json, sys
DS = {"type": "prometheus", "uid": "prometheus"}
W = "[8h30m]"   # one test every 8 h; a bit of slack for scrape jitter
LAST = "[1d]"   # stats: latest test, even if one run was missed
pid = iter(range(1, 100))

def t(expr, legend, ref="A"):
    return {"datasource": DS, "expr": expr, "legendFormat": legend, "refId": ref, "range": True}

def stat(title, expr, unit, x, w=4, decimals=1, thresholds=None, desc=""):
    return {"id": next(pid), "type": "stat", "title": title, "description": desc, "datasource": DS,
            "gridPos": {"h": 4, "w": w, "x": x, "y": 0},
            "targets": [dict(t(expr, ""), instant=True, range=False)],
            "options": {"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
                        "colorMode": "value", "graphMode": "none", "textMode": "value"},
            "fieldConfig": {"defaults": {"unit": unit, "decimals": decimals,
                "thresholds": thresholds or {"mode": "absolute", "steps": [{"color": "text", "value": None}]}},
                "overrides": []}}

def ts(title, targets, unit, y, desc="", overrides=None, minv=0):
    return {"id": next(pid), "type": "timeseries", "title": title, "description": desc, "datasource": DS,
            "gridPos": {"h": 9, "w": 24, "x": 0, "y": y},
            "targets": targets,
            "options": {"legend": {"displayMode": "list", "placement": "bottom", "showLegend": True},
                        "tooltip": {"mode": "multi", "sort": "none"}},
            "fieldConfig": {"defaults": {"unit": unit, "min": minv, "decimals": 1,
                "custom": {"drawStyle": "line", "lineInterpolation": "stepAfter", "lineWidth": 2,
                           "fillOpacity": 10, "showPoints": "auto", "pointSize": 6, "spanNulls": False}},
                "overrides": overrides or []}}

def dashed(name, color):
    return {"matcher": {"id": "byName", "options": name}, "properties": [
        {"id": "custom.lineStyle", "value": {"dash": [10, 10], "fill": "dash"}},
        {"id": "custom.fillOpacity", "value": 0},
        {"id": "color", "value": {"mode": "fixed", "fixedColor": color}}]}

pct_steps = {"mode": "absolute", "steps": [{"color": "red", "value": None},
             {"color": "orange", "value": 70}, {"color": "green", "value": 85}]}
dl = "speedtest_download_bits_per_second"; ul = "speedtest_upload_bits_per_second"
sync_rx = 'max(fritz_dsl_datarate_kbps{direction="rx",type="curr"}) * 1000'
sync_tx = 'max(fritz_dsl_datarate_kbps{direction="tx",type="curr"}) * 1000'

panels = [
    stat("Download", f"last_over_time({dl}{LAST})", "bps", 0),
    stat("Upload", f"last_over_time({ul}{LAST})", "bps", 4),
    stat("Download vs. sync", f"100 * last_over_time({dl}{LAST}) / scalar({sync_rx})", "percent", 8, decimals=0,
         thresholds=pct_steps, desc="Last download test as a share of the FRITZ!Box's current DSL sync rate. ~90-95 % is normal (protocol overhead)."),
    stat("Upload vs. sync", f"100 * last_over_time({ul}{LAST}) / scalar({sync_tx})", "percent", 12, decimals=0,
         thresholds=pct_steps, desc="Last upload test as a share of the current DSL sync rate."),
    stat("Ping / jitter", f"last_over_time(speedtest_ping_latency_milliseconds{LAST})", "ms", 16),
    stat("Last test", f"time() - max_over_time(timestamp(speedtest_up)[1d:5m])", "s", 20, decimals=0,
         thresholds={"mode": "absolute", "steps": [{"color": "green", "value": None}, {"color": "red", "value": 9 * 3600}]},
         desc="Time since the last test. Red if more than 9 h ago (tests run every 8 h). Empty: no test in the last 24 h."),
    ts("Download", [t(f"last_over_time({dl}{W})", "Speed test", "A"), t(sync_rx, "DSL sync rate", "B")], "bps", 4,
       desc="Each step is one test (every 8 h). Dashed: the FRITZ!Box's current sync rate, the ceiling.",
       overrides=[dashed("DSL sync rate", "text")]),
    ts("Upload", [t(f"last_over_time({ul}{W})", "Speed test", "A"), t(sync_tx, "DSL sync rate", "B")], "bps", 13,
       overrides=[dashed("DSL sync rate", "text")]),
    ts("Ping and jitter", [t(f"last_over_time(speedtest_ping_latency_milliseconds{W})", "Ping", "A"),
                           t(f"last_over_time(speedtest_jitter_latency_milliseconds{W})", "Jitter", "B")], "ms", 22),
    ts("Test result", [t(f"last_over_time(speedtest_up{W})", "1 = OK, 0 = failed", "A")], "none", 31,
       desc="speedtest_up of each test. 0 means the test failed (no server reached, timeout)."),
]
panels[4]["targets"].append(dict(t(f"last_over_time(speedtest_jitter_latency_milliseconds{LAST})", "", "B"), instant=True, range=False))
panels[4]["options"]["textMode"] = "value"
panels[-1]["gridPos"]["h"] = 5
panels[-1]["fieldConfig"]["defaults"].update({"max": 1, "decimals": 0})

dash = {"uid": "cornholio-speedtest", "title": "Speedtest", "tags": ["cornholio", "speedtest"],
        "description": "Ookla speed tests every 8 h, compared with the FRITZ!Box DSL sync rate.",
        "timezone": "browser", "editable": False, "graphTooltip": 1, "schemaVersion": 41, "version": 1,
        "refresh": "5m", "time": {"from": "now-7d", "to": "now"}, "templating": {"list": []},
        "annotations": {"list": []}, "links": [], "panels": panels}
OUT = sys.argv[1] if len(sys.argv) > 1 else "grafana/provisioning/dashboards/json/speedtest.json"
json.dump(dash, open(OUT, "w"), indent=2); open(OUT, "a").write("\n")
print(sum(len(p["targets"]) for p in panels), "queries")
