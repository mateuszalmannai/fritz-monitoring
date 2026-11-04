# Break glass: the Pi is down and the LAN has no DNS

Every client gets cornholio (Pi-hole, `192.168.178.27`) as its only DNS server from the FRITZ!Box
DHCP. The FRITZ!Box has just one "Local DNS server" field, so there's no fallback: if the Pi is down,
names stop resolving on every device. This procedure points the LAN back to the FRITZ!Box's own DNS
(`192.168.178.1`) in a few minutes. Pi-hole's ad blocking is off until you switch back.

Monitoring and alerts run on the same Pi, so no push notification will tell you. You notice it
because websites stop loading while the Wi-Fi and the internet line look fine.

## Prepare now, not during the outage
- Make sure you can log in to the FRITZ!Box UI: know the admin password (password manager), and
  check you can open it by IP, `http://192.168.178.1`.
- Keep a copy of this page that doesn't need the LAN, e.g. on your phone.

## 1. Confirm it's the Pi (1 minute)
From a Mac in the LAN:
```bash
ping -c 3 192.168.178.27                     # Pi reachable at all?
dig +short @192.168.178.27 example.com       # Pi-hole answers? (empty / timeout = broken)
dig +short @192.168.178.1  example.com       # FRITZ!Box DNS answers? (should print an IP)
```
If the first two fail and the third works, continue. If the third fails too, the problem is the
FRITZ!Box or the internet line, not the Pi; this procedure won't help.

Before breaking glass, a quick restart may be enough if the Pi still answers ping:
`ssh cornholio 'cd fritz-monitoring && docker compose up -d pihole'`. If the Pi doesn't answer at
all, power-cycle it once and wait 2 minutes. If DNS is still dead after that, continue.

## 2. Switch the LAN's DNS to the FRITZ!Box (2 minutes)
1. Open **`http://192.168.178.1`** (the IP, not `fritz.box`: that name needs working DNS). Works
   from a phone browser on the home Wi-Fi too.
2. **Home Network → Network → Network Settings → IPv4 Settings** (German UI: Heimnetz → Netzwerk →
   Netzwerkeinstellungen → IPv4-Einstellungen).
3. **Local DNS server** (Lokaler DNS-Server): change `192.168.178.27` to **`192.168.178.1`**.
4. **Apply**. If the box asks for a confirmation (button press on the box or a FRITZ!Fon), confirm.
5. If IPv6 is enabled in the LAN and you set the Pi under **IPv6 Settings** as well, change it there
   too.

Don't touch Internet → Account Information → DNS Server; that's the box's own upstream and stays as is.

## 3. Get devices onto the new DNS server
Devices only learn the new server when their DHCP lease renews (FRITZ!Box default: up to 10 days),
so renew the ones that matter now:
- **Mac:** System Settings → Network → connection → Details → TCP/IP → **Renew DHCP Lease**.
- **iPhone / Android:** turn Wi-Fi off and on.
- **Anything else:** reconnect to the Wi-Fi, replug the cable, or reboot it.

Check on a Mac: `scutil --dns | grep nameserver` should show `192.168.178.1`.

**Fast path for a single Mac** (before or instead of step 2, e.g. to look something up):
```bash
sudo networksetup -setdnsservers Wi-Fi 192.168.178.1     # use "Ethernet" etc. for other services
sudo networksetup -setdnsservers Wi-Fi Empty             # undo later: back to DHCP-provided DNS
```

## 4. Switch back once the Pi is healthy
1. Verify Pi-hole works: `dig +short @192.168.178.27 example.com` prints an IP, and
   `ssh cornholio 'cd fritz-monitoring && docker compose ps'` shows `pihole` as healthy.
2. In the FRITZ!Box UI, set **Local DNS server** back to **`192.168.178.27`** (and IPv6, if you
   changed it).
3. Renew leases as in step 3 (or let them renew on their own).
4. If you used the Mac fast path, run the `Empty` command to undo it.
5. Check: `scutil --dns | grep nameserver` shows `192.168.178.27`; ads are blocked again.
