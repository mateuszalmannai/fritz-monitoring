"""fritz-extras: FRITZ!Box values that fritz_exporter doesn't provide, for Prometheus.

- Devices (TR-064 Hosts, one request for the whole network list): online state, name, connection, link speed.
- System (web UI data.lua, page "ecoStat"/"energy"): CPU temperature, CPU load, RAM, energy use per component.
- Mesh (TR-064 mesh list): the backhaul path from the FRITZ!Box to each repeater, hop by hop. fritz_exporter only
  reports links between two mesh nodes, so a repeater behind powerline adapters (non-mesh nodes) is missing there.

Each source is fetched on its own timer (default: devices every 5 min, system and mesh every 2 min) and cached;
Prometheus can read /metrics as often as it likes without touching the FRITZ!Box.
Python standard library only. Reads FRITZ_HOSTNAME, FRITZ_USERNAME, FRITZ_PASSWORD from fritz.env.
"""
import hashlib
import json
import os
import re
import threading
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def env(key, default=None):
    value = os.environ.get(key, default)
    if value is None:
        raise SystemExit(f"{key} is not set")
    # docker --env-file keeps quotes; compose strips them. Accept both.
    if len(value) > 1 and value[0] == value[-1] and value[0] in "'\"":
        value = value[1:-1]
    return value


HOST = env("FRITZ_HOSTNAME")
USER = env("FRITZ_USERNAME")
PASSWORD = env("FRITZ_PASSWORD")
HOSTS_INTERVAL = int(env("FRITZ_EXTRAS_HOSTS_INTERVAL", "300"))
SYSTEM_INTERVAL = int(env("FRITZ_EXTRAS_SYSTEM_INTERVAL", "120"))
MESH_INTERVAL = int(env("FRITZ_EXTRAS_MESH_INTERVAL", "120"))
PORT = int(env("FRITZ_EXTRAS_PORT", "9788"))
# Optional: comma-separated device names or MAC addresses. If set, only these devices get their own
# series (with name); all devices are still counted. Empty = every device by name.
ALLOWLIST = {x.strip().lower() for x in env("DEVICE_ALLOWLIST", "").split(",") if x.strip()}

TR064 = f"http://{HOST}:49000"
WEB = f"http://{HOST}"
INTERFACES = {"Ethernet": "LAN", "802.11": "Wi-Fi", "HomePlug": "Powerline", "": "other"}
COMPONENTS = {"FRITZ!Box Gesamtsystem": "System", "FRITZ!Box Hauptprozessor": "CPU", "WLAN": "Wi-Fi", "DSL": "DSL",
              "analoge FON-Anschlüsse": "Analog phone ports", "USB-Geräte": "USB"}
RAM_PARTS = ("fixed", "dynamic", "free")  # order of the series in ecoStat "ramusage"

_pw = urllib.request.HTTPPasswordMgrWithDefaultRealm()
_pw.add_password(None, TR064, USER, PASSWORD)
_tr064 = urllib.request.build_opener(urllib.request.HTTPDigestAuthHandler(_pw))

# Per source: latest metric lines, time of last success, duration of the last fetch, last fetch ok.
state = {src: {"lines": [], "success": 0.0, "duration": 0.0, "ok": False} for src in ("hosts", "system", "mesh")}
lock = threading.Lock()


def esc(value):
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def line(metric, value, **labels):
    lbl = ",".join(f'{k}="{esc(v)}"' for k, v in labels.items())
    return f"{metric}{{{lbl}}} {value}" if lbl else f"{metric} {value}"


# ---------------------------------------------------------------- devices (TR-064)
def hosts_file(action, result):
    """Call a Hosts:1 action that returns the path of a file, then download that file."""
    svc = "urn:dslforum-org:service:Hosts:1"
    body = ('<?xml version="1.0"?><s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
            's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"><s:Body>'
            f'<u:{action} xmlns:u="{svc}"/></s:Body></s:Envelope>')
    req = urllib.request.Request(f"{TR064}/upnp/control/hosts", body.encode(),
                                 {"Content-Type": 'text/xml; charset="utf-8"', "SOAPAction": f"{svc}#{action}"})
    path = re.search(rf"<{result}>(.*?)</", _tr064.open(req, timeout=20).read().decode()).group(1)
    return _tr064.open(TR064 + path, timeout=20).read()


def fetch_hosts():
    items = ET.fromstring(hosts_file("X_AVM-DE_GetHostListPath", "NewX_AVM-DE_HostListPath")).findall("Item")

    # Only name + MAC identify a device's series: offline devices report no interface (and sometimes no
    # IP), so those go into a separate info metric for online devices; the online/offline timeline stays one series.
    lines, online = [], {}
    for it in items:
        name, mac = it.findtext("HostName") or "", it.findtext("MACAddress") or ""
        active = it.findtext("Active") == "1"
        iface = INTERFACES.get(it.findtext("InterfaceType") or "", it.findtext("InterfaceType"))
        if active:
            online[iface] = online.get(iface, 0) + 1
        if ALLOWLIST and name.lower() not in ALLOWLIST and mac.lower() not in ALLOWLIST:
            continue
        lines.append(line("fritz_extras_host_active", int(active), name=name, mac=mac))
        if active:
            lines.append(line("fritz_extras_host_info", 1, name=name, mac=mac, ip=it.findtext("IPAddress") or "", interface=iface))
            lines.append(line("fritz_extras_host_speed_mbps", int(it.findtext("X_AVM-DE_Speed") or 0), name=name, mac=mac))
    for iface in ("LAN", "Wi-Fi", "Powerline", "other"):
        lines.append(line("fritz_extras_hosts_online", online.get(iface, 0), interface=iface))
    lines.append(line("fritz_extras_hosts_known", len(items)))
    return lines


# ---------------------------------------------------------------- system (web UI data.lua)
_sid = None


def login():
    url = f"{WEB}/login_sid.lua?version=2"
    challenge = re.search(r"<Challenge>(.*?)<", urllib.request.urlopen(url, timeout=10).read().decode()).group(1)
    if challenge.startswith("2$"):  # PBKDF2 (FRITZ!OS 7.24+)
        _, iter1, salt1, iter2, salt2 = challenge.split("$")
        hash1 = hashlib.pbkdf2_hmac("sha256", PASSWORD.encode(), bytes.fromhex(salt1), int(iter1))
        response = salt2 + "$" + hashlib.pbkdf2_hmac("sha256", hash1, bytes.fromhex(salt2), int(iter2)).hex()
    else:  # MD5 (older FRITZ!OS)
        response = challenge + "-" + hashlib.md5(f"{challenge}-{PASSWORD}".encode("utf-16le")).hexdigest()
    data = urllib.parse.urlencode({"username": USER, "response": response}).encode()
    sid = re.search(r"<SID>(.*?)<", urllib.request.urlopen(url, data, timeout=10).read().decode()).group(1)
    if set(sid) == {"0"}:
        raise RuntimeError("web UI login failed (wrong password, or the user lacks FRITZ!Box settings rights)")
    print("web UI login (new session)", flush=True)
    return sid


def page(name):
    """data.lua page as JSON. Reuses the session (each new login is an entry in the box's event log)."""
    global _sid
    for attempt in (1, 2):
        if _sid is None:
            _sid = login()
        data = urllib.parse.urlencode({"sid": _sid, "page": name, "xhr": "1", "lang": "en", "useajax": "1"}).encode()
        try:
            return json.loads(urllib.request.urlopen(f"{WEB}/data.lua", data, timeout=20).read().decode())["data"]
        except (ValueError, KeyError):  # expired session -> login page instead of JSON
            _sid = None
    raise RuntimeError(f"data.lua page {name} returned no data")


def last(series):
    """Newest value of an ecoStat series (oldest first)."""
    return float(series[-1])


def fetch_system():
    eco = page("ecoStat")
    lines = [line("fritz_extras_cpu_temperature_celsius", last(eco["cputemp"]["series"][0])),
             line("fritz_extras_cpu_load_percent", last(eco["cpuutil"]["series"][0]))]
    for part, series in zip(RAM_PARTS, eco["ramusage"]["series"]):
        lines.append(line("fritz_extras_ram_percent", last(series), type=part))
    for comp in page("energy")["drain"]:
        if "actPerc" in comp:
            lines.append(line("fritz_extras_energy_percent", comp["actPerc"], component=COMPONENTS.get(comp["name"], comp["name"])))
    return lines


# ---------------------------------------------------------------- mesh backhaul (TR-064)
def short_model(node):
    return (node.get("device_model") or "unknown").replace("FRITZ!", "")


def medium(iface):
    name, kind = iface.get("name") or "", iface.get("type") or ""
    if kind == "WLAN":
        band = re.match(r"AP:(\d)G", name)
        return "2.4 GHz" if band and band.group(1) == "2" else f"{band.group(1)} GHz" if band else "Wi-Fi"
    return {"PLC": "Powerline"}.get(kind, kind or "other")


def fetch_mesh():
    """Shortest path of connected links from the mesh master to each repeater (mesh slave), one series per hop.

    A link's rx/tx are seen from its node_1; "down" is the direction towards the repeater.
    Node models only, no device names: they're the same for every FRITZ!Box with this hardware.
    """
    nodes = json.loads(hosts_file("X_AVM-DE_GetMeshListPath", "NewX_AVM-DE_MeshListPath"))["nodes"]
    by_uid = {n["uid"]: n for n in nodes}
    ifaces, links = {}, {}
    for n in nodes:
        for iface in n.get("node_interfaces", []):
            ifaces[iface["uid"]] = iface
            for link in iface.get("node_links", []):
                if link.get("state") == "CONNECTED":
                    links[link["uid"]] = link  # each link is listed under both ends
    neighbours = {}
    for link in links.values():
        neighbours.setdefault(link["node_1_uid"], []).append((link["node_2_uid"], link))
        neighbours.setdefault(link["node_2_uid"], []).append((link["node_1_uid"], link))

    master = next(n["uid"] for n in nodes if n.get("mesh_role") == "master")
    prev, queue = {master: None}, [master]  # breadth-first search: prev[node] = (upstream node, link)
    for uid in queue:
        for other, link in neighbours.get(uid, []):
            if other not in prev:
                prev[other] = (uid, link)
                queue.append(other)

    lines, seen = [], {}
    for n in nodes:
        if n.get("mesh_role") != "slave":
            continue
        repeater = short_model(n)
        seen[repeater] = seen.get(repeater, 0) + 1
        if seen[repeater] > 1:
            repeater += f" #{seen[repeater]}"
        lines.append(line("fritz_extras_mesh_repeater_connected", int(n["uid"] in prev), repeater=repeater))
        path, uid = [], n["uid"]
        while uid in prev and prev[uid]:
            up, link = prev[uid]
            path.insert(0, (up, uid, link))
            uid = up
        for hop, (up, down, link) in enumerate(path, 1):
            up_iface = link["node_interface_1_uid"] if link["node_1_uid"] == up else link["node_interface_2_uid"]
            name = f"{short_model(by_uid[up])} → {short_model(by_uid[down])} ({medium(ifaces.get(up_iface, {}))})"
            rx_is_down = link["node_1_uid"] == down
            for direction, rx in (("down", rx_is_down), ("up", not rx_is_down)):
                key = "rx" if rx else "tx"
                labels = dict(repeater=repeater, hop=hop, link=name, direction=direction)
                lines.append(line("fritz_extras_mesh_backhaul_rate_kbps", link.get(f"cur_data_rate_{key}", 0), **labels))
                lines.append(line("fritz_extras_mesh_backhaul_max_rate_kbps", link.get(f"max_data_rate_{key}", 0), **labels))
    return lines


# ---------------------------------------------------------------- loop + HTTP
def worker(src, fetch, interval):
    while True:
        start = time.time()
        try:
            lines = fetch()
            with lock:
                state[src].update(lines=lines, success=time.time(), ok=True)
        except Exception as exc:  # keep running; the error shows up as fritz_extras_up 0
            print(f"{src}: {type(exc).__name__}: {exc}", flush=True)
            with lock:
                state[src]["ok"] = False
        with lock:
            state[src]["duration"] = time.time() - start
        time.sleep(max(1.0, interval - (time.time() - start)))


HELP = """# HELP fritz_extras_host_active 1 if the device is online now (FRITZ!Box network list).
# TYPE fritz_extras_host_active gauge
# HELP fritz_extras_host_info Online device: IP address and connection type (LAN, Wi-Fi, Powerline, other). Always 1.
# TYPE fritz_extras_host_info gauge
# HELP fritz_extras_host_speed_mbps Link speed of an online device in Mbit/s (LAN port speed or Wi-Fi rate).
# TYPE fritz_extras_host_speed_mbps gauge
# HELP fritz_extras_hosts_online Devices online now, per connection type.
# TYPE fritz_extras_hosts_online gauge
# HELP fritz_extras_hosts_known Devices in the network list, online or not.
# TYPE fritz_extras_hosts_known gauge
# HELP fritz_extras_cpu_temperature_celsius FRITZ!Box CPU temperature.
# TYPE fritz_extras_cpu_temperature_celsius gauge
# HELP fritz_extras_cpu_load_percent FRITZ!Box CPU load.
# TYPE fritz_extras_cpu_load_percent gauge
# HELP fritz_extras_ram_percent FRITZ!Box RAM: fixed (system), dynamic (in use), free.
# TYPE fritz_extras_ram_percent gauge
# HELP fritz_extras_energy_percent Current energy use per component, in percent of that component's maximum.
# TYPE fritz_extras_energy_percent gauge
# HELP fritz_extras_mesh_repeater_connected 1 if the repeater has a connected path to the FRITZ!Box.
# TYPE fritz_extras_mesh_repeater_connected gauge
# HELP fritz_extras_mesh_backhaul_rate_kbps Current rate of each hop between the FRITZ!Box and a repeater, in kbit/s.
# TYPE fritz_extras_mesh_backhaul_rate_kbps gauge
# HELP fritz_extras_mesh_backhaul_max_rate_kbps Maximum rate of each hop between the FRITZ!Box and a repeater, in kbit/s.
# TYPE fritz_extras_mesh_backhaul_max_rate_kbps gauge
# HELP fritz_extras_up 1 if the last fetch of this source succeeded.
# TYPE fritz_extras_up gauge
# HELP fritz_extras_last_success_timestamp_seconds Time of the last successful fetch.
# TYPE fritz_extras_last_success_timestamp_seconds gauge
# HELP fritz_extras_fetch_duration_seconds Duration of the last fetch.
# TYPE fritz_extras_fetch_duration_seconds gauge
"""


def render():
    out = [HELP.rstrip()]
    now = time.time()
    with lock:
        for src, interval in (("hosts", HOSTS_INTERVAL), ("system", SYSTEM_INTERVAL), ("mesh", MESH_INTERVAL)):
            st = state[src]
            # Drop values that are too old rather than reporting stale ones as current.
            if now - st["success"] < 3 * interval:
                out += st["lines"]
            out.append(line("fritz_extras_up", int(st["ok"]), source=src))
            out.append(line("fritz_extras_last_success_timestamp_seconds", round(st["success"]), source=src))
            out.append(line("fritz_extras_fetch_duration_seconds", round(st["duration"], 3), source=src))
    return "\n".join(out) + "\n"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/metrics":
            self.send_error(404)
            return
        body = render().encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # no access log
        pass


if __name__ == "__main__":
    threading.Thread(target=worker, args=("hosts", fetch_hosts, HOSTS_INTERVAL), daemon=True).start()
    threading.Thread(target=worker, args=("system", fetch_system, SYSTEM_INTERVAL), daemon=True).start()
    threading.Thread(target=worker, args=("mesh", fetch_mesh, MESH_INTERVAL), daemon=True).start()
    print(f"fritz-extras on :{PORT}, devices every {HOSTS_INTERVAL}s, system every {SYSTEM_INTERVAL}s, "
          f"mesh every {MESH_INTERVAL}s, "
          f"allow list: {len(ALLOWLIST) or 'off'}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
