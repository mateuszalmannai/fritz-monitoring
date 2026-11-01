"""Generates grafana/provisioning/dashboards/json/fritzbox.json: every metric the FRITZ!Box 7590 AX delivers.
Style after the user's liked dashboards (12579, 13377, 13848, 17751, 24649): coloured status tiles,
download orange / upload red, line limit as a green line, stacked traffic bars."""
import json, sys

DS = {"type": "prometheus", "uid": "prometheus"}
DOWN, UP, LIMIT, ATTAIN, SPEED = "orange", "red", "green", "dark-green", "blue"
_ids = iter(range(1, 1000))
panels, Y = [], [0]

def tgt(expr, legend="", ref="A", instant=False, fmt=None, interval=None):
    t = {"datasource": DS, "expr": expr, "legendFormat": legend, "refId": ref}
    if instant: t.update(instant=True, range=False)
    else: t.update(range=True, instant=False)
    if fmt: t["format"] = fmt
    if interval: t["interval"] = interval
    return t

def place(p, x, w, h, y=None):
    p["gridPos"] = {"x": x, "y": Y[0] if y is None else y, "w": w, "h": h}
    p["id"] = next(_ids); p["datasource"] = DS
    panels.append(p); return p

def row(title):
    panels.append({"type": "row", "title": title, "collapsed": False, "id": next(_ids),
                   "gridPos": {"x": 0, "y": Y[0], "w": 24, "h": 1}, "panels": []})
    Y[0] += 1

def mapping(*pairs):
    """pairs: (value, text, color)"""
    return [{"type": "value", "options": {str(v): {"text": t, "color": c, "index": i} for i, (v, t, c) in enumerate(pairs)}}]

UPDOWN = mapping((1, "Connected", "green"), (0, "Disconnected", "red"))
YESNO = mapping((1, "Yes", "blue"), (0, "No", "text"))
ONOFF = mapping((1, "Up", "green"), (0, "Down", "red"))

def stat(title, targets, unit="none", color_mode="value", text_mode="auto", mappings=None, color=None,
         graph="none", decimals=None, desc="", calc="lastNotNull", thresholds=None, overrides=None, orient="auto"):
    d = {"unit": unit, "mappings": mappings or [],
         "thresholds": thresholds or {"mode": "absolute", "steps": [{"color": color or "text", "value": None}]}}
    if color: d["color"] = {"mode": "fixed", "fixedColor": color}
    else: d["color"] = {"mode": "thresholds"}
    if decimals is not None: d["decimals"] = decimals
    return {"type": "stat", "title": title, "description": desc, "targets": targets,
            "options": {"reduceOptions": {"calcs": [calc], "fields": "", "values": False}, "colorMode": color_mode,
                        "graphMode": graph, "textMode": text_mode, "justifyMode": "center", "orientation": orient,
                        "wideLayout": True, "showPercentChange": False},
            "fieldConfig": {"defaults": d, "overrides": overrides or []}}

def ts(title, targets, unit="none", desc="", overrides=None, stack=False, bars=False, fill=10, legend_calcs=None,
       minv=None, maxv=None, decimals=None, points="never", draw=None, interp="linear"):
    custom = {"drawStyle": draw or ("bars" if bars else "line"), "lineWidth": 1 if not bars else 1, "fillOpacity": 80 if bars else fill,
              "showPoints": points, "pointSize": 5, "lineInterpolation": interp, "spanNulls": False,
              "stacking": {"mode": "normal" if stack else "none", "group": "A"}, "axisSoftMin": 0}
    d = {"unit": unit, "custom": custom, "color": {"mode": "palette-classic"}}
    if minv is not None: d["min"] = minv
    if maxv is not None: d["max"] = maxv
    if decimals is not None: d["decimals"] = decimals
    lg = {"showLegend": True, "placement": "bottom", "displayMode": "table" if legend_calcs else "list",
          "calcs": legend_calcs or []}
    return {"type": "timeseries", "title": title, "description": desc, "targets": targets,
            "options": {"legend": lg, "tooltip": {"mode": "multi", "sort": "none"}},
            "fieldConfig": {"defaults": d, "overrides": overrides or []}}

def color_ov(name, color, extra=None):
    props = [{"id": "color", "value": {"mode": "fixed", "fixedColor": color}}] + (extra or [])
    return {"matcher": {"id": "byName", "options": name}, "properties": props}

def limit_ov(name, color=LIMIT, dash=False):
    extra = [{"id": "custom.fillOpacity", "value": 0}, {"id": "custom.lineWidth", "value": 2}]
    if dash: extra.append({"id": "custom.lineStyle", "value": {"fill": "dash", "dash": [10, 10]}})
    return color_ov(name, color, extra)

def table(title, targets, organize, overrides=None, desc="", sort=None):
    return {"type": "table", "title": title, "description": desc, "targets": targets,
            "transformations": [{"id": "merge", "options": {}}, {"id": "organize", "options": organize}],
            "options": {"showHeader": True, "cellHeight": "sm", "sortBy": sort or [], "footer": {"show": False}},
            "fieldConfig": {"defaults": {"custom": {"align": "auto", "cellOptions": {"type": "auto"}}},
                            "overrides": overrides or []}}

def col(name, props):
    return {"matcher": {"id": "byName", "options": name}, "properties": props}

# Wi-Fi client metrics only carry client_ip/client_mac. Join the device name from fritz-extras via the MAC;
# clients fritz-extras doesn't name (e.g. DEVICE_ALLOWLIST) fall back to their IP. Labels: name, mac, wifi_name.
def named(metric):
    m = f'label_replace({metric}, "mac", "$1", "client_mac", "(.*)")'
    joined = f'{m} * on (mac) group_left (name) max by (mac, name) (fritz_extras_host_info)'
    fallback = f'label_replace({m}, "name", "$1", "client_ip", "(.*)")'
    return f'max by (name, mac, wifi_name) (({joined}) or on (mac) {fallback})'

# ---------------------------------------------------------------- Status
row("Status")
place(stat("Version", [tgt("fritz_uptime_seconds_total", "{{modelname}} · FRITZ!OS {{softwareversion}}", instant=True)],
           color_mode="background", text_mode="name", color="blue"), 0, 7, 3)
place(stat("Firmware", [tgt("fritz_update_available", "{{newsoftwareversion}}", instant=True)], color_mode="background",
           mappings=mapping((0, "Up to date", "green"), (1, "Update available", "orange")),
           desc="fritz_update_available. The label newsoftwareversion names the new version when one is available."), 7, 4, 3)
place(stat("Internet (PPP)", [tgt("fritz_ppp_connection_state", instant=True)], color_mode="background", mappings=UPDOWN), 11, 4, 3)
place(stat("DSL link", [tgt("fritz_dsl_status", instant=True)], color_mode="background", mappings=UPDOWN), 15, 3, 3)
place(stat("Exporter reaches box", [tgt("fritz_device_reachable", instant=True)], color_mode="background",
           mappings=mapping((1, "Yes", "green"), (0, "No", "red"))), 18, 3, 3)
place(stat("Access type", [tgt("fritz_connection_mode", instant=True)], color_mode="background",
           mappings=mapping((1, "DSL", "blue"), (2, "Mobile fallback", "orange"), (3, "Mobile only", "orange"),
                            (4, "Fibre", "blue"), (5, "Cable", "blue"), (0, "Offline", "red"))), 21, 3, 3)
Y[0] += 3
place(stat("FRITZ!Box uptime", [tgt("fritz_uptime_seconds_total", instant=True)], unit="dtdurations", color="green"), 0, 4, 3)
place(stat("Connection uptime", [tgt("fritz_ppp_connection_uptime_seconds_total", instant=True)], unit="dtdurations", color="green",
           desc="Time since the last reconnect of the internet (PPP) connection."), 4, 4, 3)
place(stat("Last connection error", [tgt("fritz_ppp_connection_state", "{{last_error}}", instant=True)], text_mode="name",
           desc="last_error label of fritz_ppp_connection_state. ERROR_NONE = no error."), 8, 4, 3)
place(stat("Physical link", [tgt("fritz_wan_phys_link_status", instant=True)], color_mode="background", mappings=ONOFF), 12, 3, 3)
place(stat("Known devices", [tgt("fritz_known_devices_count", instant=True)], color="blue",
           desc="All devices in the FRITZ!Box's device list, online or not."), 15, 3, 3)
place(stat("Wi-Fi clients", [tgt("sum(fritz_wifi_associations_count)", instant=True)], color="blue"), 18, 3, 3)
place(stat("Phone numbers", [tgt("fritz_telephony_numbers", instant=True)], color="blue",
           desc="Telephone numbers configured on the FRITZ!Box."), 21, 3, 3)
Y[0] += 3

# ---------------------------------------------------------------- Internet traffic
row("Internet traffic")
RX = 'fritz_wan_datarate_bytes{direction="rx"} * 8'
TX = 'fritz_wan_datarate_bytes{direction="tx"} * 8'
place(stat("Download now", [tgt(RX)], unit="bps", color=DOWN, graph="area", calc="lastNotNull"), 0, 4, 4)
place(stat("Upload now", [tgt(TX)], unit="bps", color=UP, graph="area"), 4, 4, 4)
place(stat("Download, 24 h", [tgt('increase(fritz_wan_data_bytes_total{direction="rx"}[24h])')], unit="decbytes", color=DOWN, graph="area", decimals=1), 8, 4, 4)
place(stat("Upload, 24 h", [tgt('increase(fritz_wan_data_bytes_total{direction="tx"}[24h])')], unit="decbytes", color=UP, graph="area", decimals=1), 12, 4, 4)
place(stat("Download, 30 days", [tgt('increase(fritz_wan_data_bytes_total{direction="rx"}[30d])', instant=True)], unit="decbytes", color=DOWN, decimals=1,
           desc="Only counts what Prometheus has seen (data since 2026-10-10)."), 16, 4, 4)
place(stat("Upload, 30 days", [tgt('increase(fritz_wan_data_bytes_total{direction="tx"}[30d])', instant=True)], unit="decbytes", color=UP, decimals=1), 20, 4, 4)
Y[0] += 4
bw_desc = ("Yellow/red: actual traffic (fritz_wan_datarate_bytes). Green: current DSL sync rate, the real limit. "
           "Dashed: attainable rate of the line. Blue dots: speed tests (every 8 h).")
place(ts("Download bandwidth", [tgt(RX, "Used", "A"), tgt('fritz_dsl_datarate_kbps{direction="rx",type="curr"} * 1000', "Sync rate", "B"),
                                tgt('fritz_wan_max_bitrate_bps{direction="rx"}', "Attainable", "C"),
                                tgt("speedtest_download_bits_per_second", "Speed test", "D")],
         unit="bps", desc=bw_desc, legend_calcs=["mean", "max", "lastNotNull"],
         overrides=[color_ov("Used", DOWN), limit_ov("Sync rate"), limit_ov("Attainable", ATTAIN, dash=True),
                    color_ov("Speed test", SPEED, [{"id": "custom.drawStyle", "value": "points"}, {"id": "custom.pointSize", "value": 9}])]),
      0, 12, 9)
place(ts("Upload bandwidth", [tgt(TX, "Used", "A"), tgt('fritz_dsl_datarate_kbps{direction="tx",type="curr"} * 1000', "Sync rate", "B"),
                              tgt('fritz_wan_max_bitrate_bps{direction="tx"}', "Attainable", "C"),
                              tgt("speedtest_upload_bits_per_second", "Speed test", "D")],
         unit="bps", desc=bw_desc, legend_calcs=["mean", "max", "lastNotNull"],
         overrides=[color_ov("Used", UP), limit_ov("Sync rate"), limit_ov("Attainable", ATTAIN, dash=True),
                    color_ov("Speed test", SPEED, [{"id": "custom.drawStyle", "value": "points"}, {"id": "custom.pointSize", "value": 9}])]),
      12, 12, 9)
Y[0] += 9
traffic_ov = [color_ov("Download", "blue"), color_ov("Upload", "red")]
place(ts("Hourly traffic", [tgt('increase(fritz_wan_data_bytes_total{direction="rx"}[1h])', "Download", "A", interval="1h"),
                            tgt('increase(fritz_wan_data_bytes_total{direction="tx"}[1h])', "Upload", "B", interval="1h")],
         unit="decbytes", bars=True, stack=True, overrides=traffic_ov), 0, 8, 8)
daily = ts("Daily traffic", [tgt('increase(fritz_wan_data_bytes_total{direction="rx"}[1d])', "Download", "A", interval="1d"),
                             tgt('increase(fritz_wan_data_bytes_total{direction="tx"}[1d])', "Upload", "B", interval="1d")],
           unit="decbytes", bars=True, stack=True, overrides=traffic_ov,
           desc="One bar per day, always the last 30 days (independent of the dashboard's time range). Each bar is the 24 h ending at its time stamp.")
daily["timeFrom"] = "30d"
place(daily, 8, 8, 8)
place(ts("WAN packets", [tgt('rate(fritz_wan_data_packets_count_total{direction="rx"}[5m])', "Received", "A"),
                         tgt('rate(fritz_wan_data_packets_count_total{direction="tx"}[5m])', "Sent", "B")],
         unit="pps", overrides=[color_ov("Received", DOWN), color_ov("Sent", UP)], legend_calcs=["mean", "max"]), 16, 8, 8)
Y[0] += 8
TOTAL_1H = 'sum(increase(fritz_wan_data_bytes_total[1h]{}))'
compare = ts("Traffic compared: last 24 h, yesterday, a week ago",
             [tgt(TOTAL_1H.format(""), "Last 24 h", "A", interval="1h"),
              tgt(TOTAL_1H.format(" offset 1d"), "Day before", "B", interval="1h"),
              tgt(TOTAL_1H.format(" offset 7d"), "Same time a week ago", "C", interval="1h")],
             unit="decbytes", fill=0, points="always", legend_calcs=["sum", "max"],
             desc="Download + upload per hour. The other lines are the same hours one day and seven days earlier, "
                  "drawn on top of the last 24 h. Legend 'Total' = traffic in those 24 h.",
             overrides=[color_ov("Last 24 h", "blue", [{"id": "custom.lineWidth", "value": 2}, {"id": "custom.fillOpacity", "value": 15}]),
                        color_ov("Day before", "orange"),
                        color_ov("Same time a week ago", "text", [{"id": "custom.lineStyle", "value": {"fill": "dash", "dash": [10, 10]}}])])
compare["timeFrom"] = "24h"
compare["options"]["legend"]["calcs"] = ["sum", "max"]
place(compare, 0, 24, 10)   # tall enough for the 3-row legend
Y[0] += 10

# ---------------------------------------------------------------- Devices (fritz-extras)
row("Devices")
dev_desc = ("From the FRITZ!Box network list (Home Network → Network), read by fritz-extras every 5 min. "
            "Names are the ones set in the FRITZ!Box. DEVICE_ALLOWLIST in fritz.env limits which devices are named.")
# One row per device. Queries are reduced to the same key labels (name, mac) so "merge" joins them;
# Wi-Fi band and signal (fritz_exporter, FRITZ_WIFI_CLIENT_INFO=true) stay empty for wired devices.
place(table("Devices online now",
            [tgt("max by (name, mac, interface, ip) (fritz_extras_host_info)", ref="A", instant=True, fmt="table"),
             tgt("max by (name, mac) (fritz_extras_host_speed_mbps)", ref="B", instant=True, fmt="table"),
             tgt(named("fritz_wifi_client_signal_strength"), ref="C", instant=True, fmt="table")],
            {"excludeByName": {"Time": True, "Value #A": True},
             "indexByName": {"name": 0, "interface": 1, "wifi_name": 2, "Value #C": 3, "Value #B": 4, "ip": 5, "mac": 6},
             "renameByName": {"name": "Device", "interface": "Connection", "wifi_name": "Band", "Value #C": "Signal",
                              "Value #B": "Link speed", "ip": "IP", "mac": "MAC"}},
            overrides=[col("Link speed", [{"id": "unit", "value": "Mbits"}]),
                       col("Signal", [{"id": "unit", "value": "percent"}, {"id": "min", "value": 0}, {"id": "max", "value": 100},
                                      {"id": "custom.cellOptions", "value": {"type": "gauge", "mode": "basic", "valueDisplayMode": "text"}},
                                      {"id": "color", "value": {"mode": "continuous-RdYlGr"}}]),
                       col("Connection", [{"id": "custom.cellOptions", "value": {"type": "color-text"}},
                                          {"id": "mappings", "value": mapping(("LAN", "LAN", "green"), ("Wi-Fi", "Wi-Fi", "blue"),
                                                                              ("Powerline", "Powerline", "purple"), ("other", "other", "text"))}])],
            sort=[{"displayName": "Device", "desc": False}],
            desc=dev_desc + " Band and signal come from the FRITZ!Box Wi-Fi client list, matched by MAC; phones with private (random) MACs still match, as both sources see the same MAC."),
      0, 24, 17)   # full width, tall enough for ~16 devices without scrolling (peak so far: 15)
Y[0] += 17
place(ts("Devices online by connection", [tgt("fritz_extras_hosts_online", "{{interface}}", "A")],
         stack=True, fill=40, decimals=0, legend_calcs=["min", "max", "lastNotNull"], interp="stepAfter", desc=dev_desc,
         overrides=[color_ov("LAN", "green"), color_ov("Wi-Fi", "blue"), color_ov("Powerline", "purple"), color_ov("other", "text")]),
      0, 24, 10)   # tall enough for the 4-row legend
Y[0] += 10
timeline = {"type": "state-timeline", "title": "Device online history",
            "description": dev_desc + " Green = online, grey = offline, empty = no data yet. Set the time range to 7 days to see daily patterns.",
            "targets": [tgt("fritz_extras_host_active", "{{name}}", "A")],
            "options": {"showValue": "never", "mergeValues": True, "alignValue": "left", "rowHeight": 0.8,
                        "legend": {"showLegend": False}, "tooltip": {"mode": "single", "sort": "none"}},
            "fieldConfig": {"defaults": {"custom": {"fillOpacity": 80, "lineWidth": 0},
                                         # Colours via thresholds (mapping colours / "transparent" render all black here).
                                         "mappings": [{"type": "value", "options": {"1": {"text": "Online", "index": 0},
                                                                                    "0": {"text": "Offline", "index": 1}}}],
                                         "color": {"mode": "thresholds"},
                                         "thresholds": {"mode": "absolute", "steps": [{"color": "#3d3f45", "value": None},
                                                                                      {"color": "green", "value": 1}]}},
                            "overrides": []}}
place(timeline, 0, 24, 18)
Y[0] += 18

# ---------------------------------------------------------------- Wi-Fi and mesh
row("Wi-Fi and mesh")
place(table("Wi-Fi networks",
            [tgt("fritz_wifi_status", ref="A", instant=True, fmt="table"),
             tgt("fritz_wifi_channel", ref="B", instant=True, fmt="table"),
             tgt("fritz_wifi_associations_count", ref="C", instant=True, fmt="table")],
            {"excludeByName": {"Time": True, "__name__": True, "serial": True, "friendly_name": True, "job": True, "instance": True, "wifi_index": True},
             "indexByName": {"wifi_name": 0, "ssid": 1, "standard": 2, "enabled": 3, "Value #A": 4, "Value #B": 5, "Value #C": 6},
             "renameByName": {"wifi_name": "Band", "ssid": "Network name", "standard": "Standard", "enabled": "Enabled",
                              "Value #A": "Status", "Value #B": "Channel", "Value #C": "Clients"}},
            overrides=[col("Status", [{"id": "mappings", "value": mapping((1, "On", "green"), (0, "Off", "text"))},
                                      {"id": "custom.cellOptions", "value": {"type": "color-text"}}]),
                       col("Enabled", [{"id": "mappings", "value": mapping(("1", "Yes", "text"), ("0", "No", "text"))}])],
            desc="fritz_wifi_status, fritz_wifi_channel, fritz_wifi_associations_count per band."), 0, 24, 6)   # own row, no scrolling
Y[0] += 6
place(ts("Wi-Fi clients per band", [tgt("fritz_wifi_associations_count", "{{wifi_name}}", "A")], unit="short", decimals=0,
         legend_calcs=["min", "max", "lastNotNull"], interp="stepAfter",
         overrides=[color_ov("2.4GHz", "yellow"), color_ov("5GHz", "green"), color_ov("Guest", "purple")]), 0, 24, 6)
Y[0] += 6
wifi_client_desc = "Device names come from fritz-extras, matched by MAC (IP if no name is known). The per-device table is under Devices."
place(ts("Client signal strength", [tgt(named("fritz_wifi_client_signal_strength"), "{{name}} ({{wifi_name}})", "A")], unit="percent",
         minv=0, maxv=100, legend_calcs=["min", "mean", "lastNotNull"], desc=wifi_client_desc), 0, 12, 9)
place(ts("Client link speed", [tgt(named("fritz_wifi_client_speed"), "{{name}} ({{wifi_name}})", "A")], unit="Mbits", desc=wifi_client_desc,
         legend_calcs=["min", "mean", "lastNotNull"], interp="stepAfter"), 12, 12, 9)
Y[0] += 9
# Mesh backhaul, two sources:
# - fritz-extras: the whole path FRITZ!Box -> repeater hop by hop, also through non-mesh nodes such as powerline adapters.
# - fritz_exporter: only direct links between two mesh nodes (Wi-Fi backhaul or a plain LAN cable); empty behind powerline.
# Exporter links per band or LAN port (interface AP:2G:0, AP:5G:0, LAN:2, ...): add a readable "band" label, raw interface as fallback.
def band(expr):
    e = f'label_replace({expr}, "band", "$1", "interface", "(.*)")'
    e = f'label_replace({e}, "band", "$1 GHz", "interface", "AP:(5|6)G.*")'
    e = f'label_replace({e}, "band", "LAN port $1", "interface", "LAN:([0-9]+)")'
    return f'label_replace({e}, "band", "2.4 GHz", "interface", "AP:2G.*")'

HOP_NOW = "fritz_extras_mesh_backhaul_rate_kbps * 1000"
HOP_MAX = "max without (direction) (fritz_extras_mesh_backhaul_max_rate_kbps) * 1000"
DIRECT_NOW = band("fritz_mesh_link_current_data_rate_kbps * 1000")
DIRECT_MAX = band("max without (direction) (fritz_mesh_link_max_data_rate_kbps) * 1000")
mesh_desc = ("Backhaul path from the FRITZ!Box to the repeater, read by fritz-extras every 2 min from the mesh overview, "
             "including non-mesh hops such as powerline adapters. \"direct\": fritz_exporter's view, which only knows links "
             "between two mesh nodes (Wi-Fi backhaul or a plain cable), so it is empty while the repeater sits behind powerline.")
place(stat("Mesh link", [tgt("fritz_extras_mesh_repeater_connected", "{{repeater}}", "A", instant=True),
                         tgt(band("fritz_mesh_link_available"), "direct {{band}}", "B", instant=True)],
           color_mode="background", text_mode="value_and_name", mappings=mapping((1, "Connected", "green"), (0, "Disconnected", "red")),
           orient="horizontal", desc=mesh_desc), 0, 6, 4)
place(stat("Mesh link rate", [tgt("min by (repeater, direction) (fritz_extras_mesh_backhaul_rate_kbps) * 1000", "{{direction}}", "A", instant=True),
                              tgt("min by (repeater) (fritz_extras_mesh_backhaul_max_rate_kbps) * 1000", "max", "B", instant=True)],
           unit="bps", text_mode="value_and_name", color="text", decimals=0, orient="horizontal",
           desc="The slowest hop of the backhaul path (the bottleneck), down = towards the repeater. "
                "Powerline: the PHY rate the adapters negotiated; real throughput is roughly half."), 0, 6, 5, y=Y[0] + 4)
max_ov = {"matcher": {"id": "byRegexp", "options": ".* max$"},
          "properties": [{"id": "custom.fillOpacity", "value": 0}, {"id": "custom.lineWidth", "value": 1},
                         {"id": "custom.lineStyle", "value": {"fill": "dash", "dash": [10, 10]}}]}
place(ts("Mesh link rate history", [tgt(HOP_NOW, "{{hop}}. {{link}} {{direction}}", "A"),
                                    tgt(HOP_MAX, "{{hop}}. {{link}} max", "B"),
                                    tgt(DIRECT_NOW, "direct {{band}} {{direction}}", "C"),
                                    tgt(DIRECT_MAX, "direct {{band}} max", "D")],
         unit="bps", legend_calcs=["min", "mean", "lastNotNull"], interp="stepAfter",
         desc="Negotiated rate of each hop between the FRITZ!Box and the repeater (down = towards the repeater). LAN: the Ethernet port speed. "
              "Powerline: the adapters' PHY rate, which varies with the mains; real throughput is roughly half. "
              "Wi-Fi: an idle link drops to a low basic rate. Dashed: the hop's maximum. "
              "Before 2026-10-13 only the exporter's direct links exist (the LAN port speed, not the powerline rate).",
         overrides=[{"matcher": {"id": "byRegexp", "options": ".*Powerline\\) down"}, "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": SPEED}}]},
                    {"matcher": {"id": "byRegexp", "options": ".*Powerline\\) (up|max)"}, "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "purple"}}]},
                    {"matcher": {"id": "byRegexp", "options": ".*\\(LAN\\) .*"}, "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": ATTAIN}}]},
                    color_ov("direct 2.4 GHz rx", DOWN), color_ov("direct 2.4 GHz tx", UP), color_ov("direct 2.4 GHz max", DOWN),
                    color_ov("direct 5 GHz rx", SPEED), color_ov("direct 5 GHz tx", "purple"), color_ov("direct 5 GHz max", SPEED),
                    {"matcher": {"id": "byRegexp", "options": "direct LAN port .* rx"}, "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": LIMIT}}]},
                    {"matcher": {"id": "byRegexp", "options": "direct LAN port .* (tx|max)"}, "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": ATTAIN}}]}, max_ov]),
      6, 18, 9)
Y[0] += 9

# ---------------------------------------------------------------- DSL line
row("DSL line")
place(stat("Sync rate (current)", [tgt('fritz_dsl_datarate_kbps{direction="rx",type="curr"} * 1000', "Down", "A", instant=True),
                                   tgt('fritz_dsl_datarate_kbps{direction="tx",type="curr"} * 1000', "Up", "B", instant=True)],
           unit="bps", text_mode="value_and_name", color=LIMIT, decimals=1,
           desc="fritz_dsl_datarate_kbps{type=\"curr\"}: what the line is synced at (your tariff profile). The real ceiling."), 0, 6, 4)
place(stat("Attainable rate", [tgt('fritz_dsl_datarate_kbps{direction="rx",type="max"} * 1000', "Down", "A", instant=True),
                               tgt('fritz_dsl_datarate_kbps{direction="tx",type="max"} * 1000', "Up", "B", instant=True)],
           unit="bps", text_mode="value_and_name", color="text", decimals=1,
           desc="fritz_dsl_datarate_kbps{type=\"max\"} (same as fritz_wan_max_bitrate_bps): what the line could carry."), 6, 6, 4)
place(stat("Line capacity used", [tgt('100 * fritz_dsl_datarate_kbps{direction="rx",type="curr"} / ignoring(type) fritz_dsl_datarate_kbps{direction="rx",type="max"}', "Down", "A", instant=True),
                                  tgt('100 * fritz_dsl_datarate_kbps{direction="tx",type="curr"} / ignoring(type) fritz_dsl_datarate_kbps{direction="tx",type="max"}', "Up", "B", instant=True)],
           unit="percent", text_mode="value_and_name", color="text", decimals=0,
           desc="Current sync rate as a share of the attainable rate. Well below 100 % means the tariff, not the line, limits the speed."), 12, 4, 4)
place(stat("CRC errors, 24 h", [tgt("increase(fritz_dsl_crc_errors_count_total[24h])", instant=True)], decimals=0,
           thresholds={"mode": "absolute", "steps": [{"color": "green", "value": None}, {"color": "orange", "value": 100}, {"color": "red", "value": 1000}]},
           desc="Uncorrectable errors (fritz_dsl_crc_errors_count_total). They cost retransmissions; a few are normal."), 16, 4, 4)
place(stat("DSL interface enabled", [tgt("fritz_dsl_status_enabled", instant=True)], color_mode="background",
           mappings=mapping((1, "Enabled", "green"), (0, "Disabled", "red"))), 20, 4, 4)
Y[0] += 4
place(ts("Sync rate history", [tgt('fritz_dsl_datarate_kbps{type="curr"} * 1000', "Current {{direction}}", "A"),
                               tgt('fritz_dsl_datarate_kbps{type="max"} * 1000', "Attainable {{direction}}", "B")],
         unit="bps", legend_calcs=["min", "max", "lastNotNull"],
         desc="A change in the current rate means the line resynced.",
         overrides=[color_ov("Current rx", DOWN), color_ov("Current tx", UP),
                    limit_ov("Attainable rx", DOWN, dash=True), limit_ov("Attainable tx", UP, dash=True)]), 0, 12, 8)
place(ts("DSL errors per minute", [tgt("rate(fritz_dsl_fec_errors_count_total[5m]) * 60", "FEC (corrected)", "A"),
                                   tgt("rate(fritz_dsl_crc_errors_count_total[5m]) * 60", "CRC (uncorrectable)", "B")],
         unit="short", legend_calcs=["mean", "max", "lastNotNull"],
         desc="FEC errors are corrected and harmless in large numbers. CRC errors are lost data.",
         overrides=[color_ov("FEC (corrected)", "yellow"), color_ov("CRC (uncorrectable)", "red")]), 12, 12, 8)
Y[0] += 8
place(ts("Line attenuation", [tgt("fritz_dsl_attenuation_dB", "{{direction}}", "A")], unit="dB", legend_calcs=["min", "max", "lastNotNull"],
         desc="Signal loss on the copper line. Lower is better; it depends on the distance to the street cabinet.",
         overrides=[color_ov("rx", DOWN), color_ov("tx", UP)]), 0, 12, 7)
place(ts("Noise margin (SNR)", [tgt("fritz_dsl_noise_margin_dB", "{{direction}}", "A")], unit="dB", legend_calcs=["min", "max", "lastNotNull"],
         desc="Headroom against interference. Above ~6 dB is stable; drops point to interference or resyncs.",
         overrides=[color_ov("rx", DOWN), color_ov("tx", UP)]), 12, 12, 7)
Y[0] += 7

# ---------------------------------------------------------------- Connections and provider
row("Connections and provider")
place(table("WAN connections",
            [tgt("fritz_wan_connection_status", ref="A", instant=True, fmt="table"),
             tgt("fritz_wan_connection_uptime_seconds_total", ref="B", instant=True, fmt="table")],
            {"excludeByName": {"Time": True, "__name__": True, "serial": True, "friendly_name": True, "job": True, "instance": True, "connection": True},
             "indexByName": {"connection_name": 0, "media_type": 1, "stack": 2, "state": 3, "Value #A": 4, "Value #B": 5, "ip_address": 6},
             "renameByName": {"connection_name": "Connection", "media_type": "Medium", "stack": "Stack", "state": "State",
                              "Value #A": "Up", "Value #B": "Uptime", "ip_address": "Address"}},
            overrides=[col("Up", [{"id": "mappings", "value": mapping((1, "Yes", "green"), (0, "No", "text"))},
                                  {"id": "custom.cellOptions", "value": {"type": "color-text"}}]),
                       col("Uptime", [{"id": "unit", "value": "dtdurations"}])],
            desc="fritz_wan_connection_status and _uptime per connection and IP stack. internet2 is the LTE fallback, voip the telephony connection."),
      0, 24, 9)   # full width, 6 connections fit without scrolling
Y[0] += 9
# Stat panels size their text to fit the panel, so the long strings get wide, tall panels.
place(stat("IPv6 prefix", [tgt("fritz_wan_ipv6_prefix_info", "{{prefix}}/{{prefix_length}}", instant=True)], text_mode="name", color="text",
           desc="Delegated IPv6 prefix from the provider (fritz_wan_ipv6_prefix_info)."), 0, 12, 3)
place(stat("Provider management server (TR-069)", [tgt("fritz_tr069_acs_info", "{{acs_host}}", instant=True)], text_mode="name", color="text",
           desc="The provider's auto-configuration server the FRITZ!Box reports to (fritz_tr069_acs_info)."), 12, 12, 3)
Y[0] += 3
place(stat("Remote management", [tgt("fritz_tr069_periodic_inform_enabled", "Periodic inform", "A", instant=True),
                                 tgt("fritz_tr069_upgrades_managed", "Provider manages firmware", "B", instant=True),
                                 tgt("fritz_usp_controller_enabled", "USP controller", "C", instant=True),
                                 tgt("fritz_usp_myfritz_enabled", "MyFRITZ! USP", "D", instant=True)],
           text_mode="value_and_name", mappings=YESNO, orient="vertical",   # the four values side by side
           desc="TR-069 and USP: whether the provider or MyFRITZ! can manage the box remotely."), 0, 18, 4)
place(stat("Inform interval", [tgt("fritz_tr069_periodic_inform_interval_seconds", instant=True)], unit="dtdurations", color="text",
           desc="How often the FRITZ!Box contacts the provider's TR-069 server."), 18, 6, 4)
Y[0] += 4

# ---------------------------------------------------------------- System (fritz-extras)
row("FRITZ!Box system")
ext_desc = "From fritz-extras (our add-on, fritz-extras/fritz_extras.py), which reads the FRITZ!Box web UI every 2 min."
RAM_USED = 'sum(fritz_extras_ram_percent{type=~"fixed|dynamic"})'
place(stat("CPU temperature", [tgt("fritz_extras_cpu_temperature_celsius")], unit="celsius", graph="area", decimals=0,
           thresholds={"mode": "absolute", "steps": [{"color": "green", "value": None}, {"color": "orange", "value": 85}, {"color": "red", "value": 95}]},
           desc=ext_desc + " 60-80 °C is normal for a FRITZ!Box."), 0, 4, 5)
place(stat("CPU load", [tgt("fritz_extras_cpu_load_percent")], unit="percent", graph="area", decimals=0,
           thresholds={"mode": "absolute", "steps": [{"color": "green", "value": None}, {"color": "orange", "value": 70}, {"color": "red", "value": 90}]},
           desc=ext_desc), 4, 4, 5)
place(stat("RAM in use", [tgt(RAM_USED)], unit="percent", graph="area", decimals=0,
           thresholds={"mode": "absolute", "steps": [{"color": "green", "value": None}, {"color": "orange", "value": 80}, {"color": "red", "value": 90}]},
           desc=ext_desc + " Fixed (system) + dynamic memory."), 8, 4, 5)
place(stat("Devices online", [tgt("sum(fritz_extras_hosts_online)", "Online", "A"), tgt("fritz_extras_hosts_known", "Known", "B")],
           text_mode="value_and_name", color="blue", graph="none", decimals=0, orient="horizontal",
           desc="From the FRITZ!Box network list, every 5 min (fritz-extras)."), 12, 4, 5)
place(stat("fritz-extras", [tgt('fritz_extras_up{source="system"}', "System values", "A", instant=True),
                            tgt('fritz_extras_up{source="hosts"}', "Device list", "B", instant=True),
                            tgt('fritz_extras_up{source="mesh"}', "Mesh path", "D", instant=True),
                            tgt('up{job="fritz-extras"}', "Add-on reachable", "C", instant=True)],
           color_mode="background", text_mode="value_and_name", mappings=mapping((1, "OK", "green"), (0, "Failing", "red")),
           orient="horizontal", desc="Whether the add-on's last fetch worked. Errors: docker compose logs fritz-extras"), 16, 8, 5)
Y[0] += 5
place(ts("CPU temperature and load", [tgt("fritz_extras_cpu_temperature_celsius", "Temperature", "A"),
                                      tgt("fritz_extras_cpu_load_percent", "Load", "B")],
         unit="celsius", legend_calcs=["min", "mean", "max", "lastNotNull"], desc=ext_desc,
         overrides=[color_ov("Temperature", "red"),
                    color_ov("Load", "blue", [{"id": "unit", "value": "percent"}, {"id": "custom.axisPlacement", "value": "right"},
                                              {"id": "min", "value": 0}, {"id": "max", "value": 100}])]), 0, 12, 8)
place(ts("RAM", [tgt('fritz_extras_ram_percent{type="fixed"}', "Fixed (system)", "A"),
                 tgt('fritz_extras_ram_percent{type="dynamic"}', "Dynamic", "B"),
                 tgt('fritz_extras_ram_percent{type="free"}', "Free", "C")],
         unit="percent", stack=True, fill=60, minv=0, maxv=100, legend_calcs=["mean", "lastNotNull"], desc=ext_desc,
         overrides=[color_ov("Fixed (system)", "purple"), color_ov("Dynamic", "orange"), color_ov("Free", "green")]), 12, 6, 8)
place(ts("Energy use per component", [tgt("fritz_extras_energy_percent", "{{component}}", "A")],
         unit="percent", minv=0, maxv=100, legend_calcs=["lastNotNull"], interp="stepAfter",
         desc="Current energy use of each part, in percent of that part's maximum (the FRITZ!Box shows no watts). "
              "From the web UI page System → Energy Monitor."), 18, 6, 8)
Y[0] += 8

# ---------------------------------------------------------------- LAN and exporter
row("LAN and exporter")
zero_desc = "Your FRITZ!Box reports 0 for this counter (FRITZ!OS doesn't fill it on this model)."
place(stat("LAN interface", [tgt("fritz_lan_status", "Status", "A", instant=True), tgt("fritz_lan_status_enabled", "Enabled", "B", instant=True)],
           color_mode="background", text_mode="value_and_name", mappings=mapping((1, "Up", "green"), (0, "Down", "red"))), 0, 6, 4)
place(stat("LAN traffic", [tgt('rate(fritz_lan_data_bytes_total{direction="rx"}[5m]) * 8', "rx", "A"),
                           tgt('rate(fritz_lan_data_bytes_total{direction="tx"}[5m]) * 8', "tx", "B")],
           unit="bps", text_mode="value_and_name", color="text", desc=zero_desc), 6, 4, 4)
place(stat("LAN packets", [tgt('rate(fritz_lan_packet_count_total{direction="rx"}[5m])', "rx", "A"),
                           tgt('rate(fritz_lan_packet_count_total{direction="tx"}[5m])', "tx", "B")],
           unit="pps", text_mode="value_and_name", color="text", desc=zero_desc), 10, 4, 4)
place(stat("Wi-Fi packets", [tgt('sum by (direction) (rate(fritz_wifi_packets_count_total[5m]))', "{{direction}}", "A")],
           unit="pps", text_mode="value_and_name", color="text", desc=zero_desc), 14, 4, 4)
place(stat("Exporter scrapes, 24 h", [tgt("increase(fritz_scrapes_total[24h])", "Done", "A", instant=True),
                                      tgt("increase(fritz_scrapes_failed_total[24h])", "Failed", "B", instant=True),
                                      tgt("increase(fritz_scrapes_timeouts_total[24h])", "Timed out", "C", instant=True)],
           text_mode="value_and_name", decimals=0, color="text", orient="horizontal",
           overrides=[{"matcher": {"id": "byName", "options": n}, "properties": [{"id": "thresholds", "value": {"mode": "absolute", "steps": [{"color": "green", "value": None}, {"color": "red", "value": 1}]}}, {"id": "color", "value": {"mode": "thresholds"}}]} for n in ("Failed", "Timed out")]),
      18, 6, 4)
Y[0] += 4
place(ts("FRITZ!Box scrape duration", [tgt('scrape_duration_seconds{job="fritz-exporter"}', "Scrape", "A")], unit="s",
         legend_calcs=["mean", "max", "lastNotNull"],
         desc="How long one read-out of the FRITZ!Box takes. The Prometheus timeout is 30 s."), 0, 12, 6)
place(ts("fritz-extras fetch duration", [tgt("fritz_extras_fetch_duration_seconds", "{{source}}", "A")], unit="s",
         legend_calcs=["mean", "max", "lastNotNull"], interp="stepAfter",
         desc="How long the add-on's last fetch took: hosts = device list (every 5 min), system = web UI values (every 2 min)."),
      12, 8, 6)
place(stat("fritz-extras last success", [tgt("time() - fritz_extras_last_success_timestamp_seconds", "{{source}}", "A", instant=True)],
           unit="s", text_mode="value_and_name", decimals=0, orient="horizontal",
           thresholds={"mode": "absolute", "steps": [{"color": "green", "value": None}, {"color": "orange", "value": 700}, {"color": "red", "value": 1000}]},
           desc="Seconds since the last successful fetch per source. Values older than 3 intervals are dropped."),
      20, 4, 6)
Y[0] += 6

dash = {"uid": "cornholio-fritzbox", "title": "FRITZ!Box", "tags": ["cornholio", "fritzbox"],
        "description": "Every metric the FRITZ!Box 7590 AX delivers via fritz_exporter and fritz-extras. Provisioned from grafana/provisioning/dashboards/json/fritzbox.json.",
        "timezone": "browser", "editable": False, "graphTooltip": 1, "schemaVersion": 41, "version": 1,
        "refresh": "1m", "time": {"from": "now-24h", "to": "now"}, "templating": {"list": []},
        "annotations": {"list": []},
        "links": [{"title": "Speedtest", "type": "link", "url": "/d/cornholio-speedtest", "icon": "dashboard"}],
        "panels": panels}
OUT = sys.argv[1] if len(sys.argv) > 1 else "grafana/provisioning/dashboards/json/fritzbox.json"
json.dump(dash, open(OUT, "w"), indent=2, ensure_ascii=False); open(OUT, "a").write("\n")
exprs = [t["expr"] for p in panels for t in p.get("targets", [])]
if len(sys.argv) > 2: open(sys.argv[2], "w").write("\n".join(exprs) + "\n")
print(len([p for p in panels if p["type"] != "row"]), "panels,", len(exprs), "queries")
