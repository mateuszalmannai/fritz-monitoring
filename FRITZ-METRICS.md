# FRITZ!Box metrics reference

What `pdreker/fritz_exporter` delivers on cornholio's FRITZ!Box 7590 AX (DSL), and how metrics used by other
exporters' Grafana dashboards map to it. Basis for the bespoke FRITZ!Box dashboard. Collected 2026-10-11 with
`FRITZ_HOST_INFO=false` and `FRITZ_WIFI_CLIENT_INFO=true`; personal label values (IPs, IPv6 prefix, Wi-Fi names, serial) are left out.

Pitfalls:
- `rx` = download, `tx` = upload.
- `fritz_dsl_datarate_kbps{type="curr"}` is the current sync rate (the real ceiling, ~64/23 Mbit/s);
  `type="max"` and `fritz_wan_max_bitrate_bps` are the attainable rate (~133/52), not what the tariff gives.
- Mesh links: one series per link, `type` WLAN (interface `AP:2G:0`/`AP:5G:0`) or LAN (`LAN:<port>`, rate = Ethernet port speed).
  Only links between two mesh nodes: since 2026-10-13 the repeater sits behind FRITZ!Powerline 1220E adapters (non-mesh nodes
  in the mesh overview), so `fritz_mesh_*` is empty. The backhaul path comes from fritz-extras (`fritz_extras_mesh_*`).
- `fritz_lan_*` and `fritz_wifi_packets_count_total` are always 0 on this box.
- Online devices, CPU temperature/load, RAM and energy come from our add-on fritz-extras (`fritz_extras_*`, see README).
- Per-device metrics (`fritz_host_*`) need `FRITZ_HOST_INFO=true` (slow, off). `fritz_wifi_client_*` need
  `FRITZ_WIFI_CLIENT_INFO=true` (on); clients are identified by IP/MAC only, phones often use private MACs.

## Metrics with values

| Metric | Type | Series | Label keys | Meaning |
|---|---|---|---|---|
| `fritz_connection_mode` | gauge | 1 | `access_type` | Connection mode: 1=DSL, 2=Mobile fallback, 3=Mobile-only, 4=Fiber, 5=Cable, 0=offline/unknown |
| `fritz_device_reachable` | gauge | 1 | – | Fritz device reachability (1=reachable, 0=unreachable) |
| `fritz_dsl_attenuation_dB` | gauge | 2 | `direction` | Line attenuation in dB |
| `fritz_dsl_crc_errors_count_total` | counter | 1 | – | Number of CRC Errors (always 0) |
| `fritz_dsl_datarate_kbps` | gauge | 4 | `direction`, `type` | DSL datarate in kbps |
| `fritz_dsl_fec_errors_count_total` | counter | 1 | – | Number of Forward Error Correction Errors |
| `fritz_dsl_noise_margin_dB` | gauge | 2 | `direction` | Noise Margin in dB |
| `fritz_dsl_status` | gauge | 1 | – | DSL status |
| `fritz_dsl_status_enabled` | gauge | 1 | – | DSL enabled |
| `fritz_known_devices_count` | gauge | 1 | – | Number of devices in hosts table |
| `fritz_lan_data_bytes_total` | counter | 2 | `direction` | LAN bytes received (always 0) |
| `fritz_lan_packet_count_total` | counter | 2 | `direction` | LAN packets transmitted (always 0) |
| `fritz_lan_status` | gauge | 1 | – | LAN Interface status |
| `fritz_lan_status_enabled` | gauge | 1 | – | LAN Interface enabled |
| `fritz_mesh_link_available` | gauge | 1 | `interface`, `node`, `peer`, `type` | Mesh backhaul link state (1=connected, 0=otherwise) |
| `fritz_mesh_link_current_data_rate_kbps` | gauge | 2 | `direction`, `interface`, `node`, `peer`, `type` | Current data rate of a mesh backhaul link in kbit/s |
| `fritz_mesh_link_max_data_rate_kbps` | gauge | 2 | `direction`, `interface`, `node`, `peer`, `type` | Maximum data rate of a mesh backhaul link in kbit/s |
| `fritz_ppp_connection_state` | gauge | 1 | `last_error` | PPP connection state |
| `fritz_ppp_connection_uptime_seconds_total` | counter | 1 | – | PPP connection uptime |
| `fritz_scrapes_failed_total` | counter | 1 | – | Scrapes aborted by an unexpected error during collection. (always 0) |
| `fritz_scrapes_timeouts_total` | counter | 1 | – | Scrapes skipped because a previous scrape was still in progress when the collector lock deadline was reached. (always 0) |
| `fritz_scrapes_total` | counter | 1 | – | Total number of completed scrape cycles per Fritz device. |
| `fritz_telephony_numbers` | gauge | 1 | – | Number of telephone numbers configured on the device |
| `fritz_tr069_acs_info` | gauge | 1 | `acs_host` | TR-069 management server host name (always 1 if present) |
| `fritz_tr069_periodic_inform_enabled` | gauge | 1 | – | Whether the device periodically informs the TR-069 management server |
| `fritz_tr069_periodic_inform_interval_seconds` | gauge | 1 | – | Interval of the periodic TR-069 inform |
| `fritz_tr069_upgrades_managed` | gauge | 1 | – | Whether firmware upgrades are managed by the TR-069 management server |
| `fritz_update_available` | gauge | 1 | `newsoftwareversion` | FritzBox update available |
| `fritz_uptime_seconds_total` | counter | 1 | `modelname`, `softwareversion` | FritzBox uptime, system info in labels |
| `fritz_usp_controller_enabled` | gauge | 1 | `index` | Whether a USP controller is enabled |
| `fritz_usp_myfritz_enabled` | gauge | 1 | – | Whether the MyFRITZ USP controller is enabled |
| `fritz_wan_connection_status` | gauge | 6 | `connection`, `connection_name`, `ip_address`, `media_type`, `stack`, `state` | Per-stack connection state of a WAN connection (1 when connected, 0 otherwise; state in label) |
| `fritz_wan_connection_uptime_seconds_total` | counter | 2 | `connection`, `connection_name`, `ip_address`, `media_type`, `stack` | Per-stack uptime of a WAN connection in seconds (resets on reconnect) |
| `fritz_wan_data_bytes_total` | counter | 2 | `direction` | WAN data in bytes |
| `fritz_wan_data_packets_count_total` | counter | 2 | `direction` | WAN data in packets |
| `fritz_wan_datarate_bytes` | gauge | 2 | `direction` | Current WAN data rate in bytes/s |
| `fritz_wan_ipv6_prefix_info` | gauge | 1 | `prefix`, `prefix_length` | Delegated IPv6 prefix of the WAN connection (always 1 if present) |
| `fritz_wan_max_bitrate_bps` | gauge | 2 | `direction`, `wantype` | max bitrate at the physical layer |
| `fritz_wan_phys_link_status` | gauge | 1 | `wantype` | link status at the physical layer |
| `fritz_wifi_associations_count` | gauge | 3 | `enabled`, `ssid`, `standard`, `wifi_index`, `wifi_name` | Number of associations (devices) in WiFi |
| `fritz_wifi_channel` | gauge | 3 | `enabled`, `ssid`, `standard`, `wifi_index`, `wifi_name` | Channel of WiFi |
| `fritz_wifi_client_signal_strength` | gauge | 8 | `client_ip`, `client_mac`, `wifi_name` | Signal strength of an associated WiFi client in percent (needs `FRITZ_WIFI_CLIENT_INFO=true`) |
| `fritz_wifi_client_speed` | gauge | 8 | `client_ip`, `client_mac`, `wifi_name` | Negotiated speed of an associated WiFi client in Mbit/s (needs `FRITZ_WIFI_CLIENT_INFO=true`) |
| `fritz_wifi_packets_count_total` | counter | 6 | `direction`, `enabled`, `ssid`, `standard`, `wifi_index`, `wifi_name` | Amount of packets in WiFi (always 0) |
| `fritz_wifi_status` | gauge | 3 | `enabled`, `ssid`, `standard`, `wifi_index`, `wifi_name` | Status of WiFi |

## Translation from other exporters

Status: map = has an equivalent, hostinfo = needs FRITZ_HOST_INFO, missing = not in this exporter, n/a = not applicable here.

| Their metric | Status | Equivalent here | Note |
|---|---|---|---|
| `gateway_connection_max_bitrate` | map | `fritz_wan_max_bitrate_bps{direction="rx"|"tx"}` | Down→rx, Up→tx. This is the attainable rate (133/52); for the real sync rate use fritz_dsl_datarate_kbps{direction="rx",type="curr"} * 1000 |
| `gateway_max_bitrate` | map | `fritz_wan_max_bitrate_bps{direction="rx"|"tx"}` | Same as above |
| `gateway_wan_layer1_downstream_max_bitrate` | map | `fritz_wan_max_bitrate_bps{direction="rx"}` | Attainable rate; real sync: fritz_dsl_datarate_kbps{direction="rx",type="curr"} * 1000 |
| `gateway_wan_layer1_upstream_max_bitrate` | map | `fritz_wan_max_bitrate_bps{direction="tx"}` | Attainable rate; real sync: fritz_dsl_datarate_kbps{direction="tx",type="curr"} * 1000 |
| `gateway_connection_status` | map | `fritz_ppp_connection_state / fritz_wan_phys_link_status` | connection="IP"→PPP state, "Physical Link"→phys link |
| `gateway_wan_connection_status` | map | `fritz_ppp_connection_state` |  |
| `gateway_wan_layer1_link_status` | map | `fritz_wan_phys_link_status` |  |
| `gateway_connection_uptime_seconds` | map | `fritz_ppp_connection_uptime_seconds_total` |  |
| `gateway_wan_connection_uptime_seconds` | map | `fritz_ppp_connection_uptime_seconds_total` |  |
| `gateway_uptime_seconds` | map | `fritz_uptime_seconds_total` | service="WANIPConnection"→fritz_ppp_connection_uptime_seconds_total |
| `gateway_device_modelname` | map | `fritz_uptime_seconds_total (labels modelname, softwareversion)` | Shown via the labels |
| `gateway_traffic` | map | `fritz_wan_data_bytes_total{direction="rx"|"tx"}` | Received→rx, Sent→tx; use increase() for daily/hourly volume |
| `gateway_wan_traffic` | map | `fritz_wan_data_bytes_total{direction="rx"|"tx"}` | Received→rx, Sent→tx |
| `gateway_wan_bytes_received` | map | `fritz_wan_data_bytes_total{direction="rx"}` |  |
| `gateway_wan_bytes_sent` | map | `fritz_wan_data_bytes_total{direction="tx"}` |  |
| `gateway_wan_packets_received` | map | `fritz_wan_data_packets_count_total{direction="rx"}` |  |
| `gateway_wan_packets_sent` | map | `fritz_wan_data_packets_count_total{direction="tx"}` |  |
| `gateway_traffic_rate` | map | `fritz_wan_datarate_bytes{direction="rx"|"tx"}` | Bytes/s like the original (×8 for bit/s) |
| `gateway_wan_traffic_rate` | map | `fritz_wan_datarate_bytes{direction="rx"|"tx"}` |  |
| `gateway_wlan_current_connections` | map | `fritz_wifi_associations_count` | Per band via wifi_name="2.4GHz"|"5GHz"|"Guest" |
| `gateway_host_active` | map | `fritz_extras_host_active` | From fritz-extras (labels name, mac). fritz_host_active would need FRITZ_HOST_INFO=true (slow) |
| `gateway_data_ecostat_cputemp` | map | `fritz_extras_cpu_temperature_celsius` | From fritz-extras |
| `gateway_data_ecostat_cpuutil` | map | `fritz_extras_cpu_load_percent` | From fritz-extras |
| `gateway_data_ecostat_ramusage` | map | `fritz_extras_ram_percent{type="fixed"|"dynamic"|"free"}` | From fritz-extras |
| `gateway_data_energy_consumption` | map | `fritz_extras_energy_percent{component}` | From fritz-extras; percent of each part's maximum, no watts |
| `fritz_host_active` | map | `fritz_extras_host_active` | From fritz-extras; fritz_host_active itself needs FRITZ_HOST_INFO=true (slow) |
| `fritzbox_device_present` | n/a | `fritz_ha_device_present` | Smart Home: your exporter supports it, but no Smart Home devices are connected |
| `fritzbox_energy` | n/a | `fritz_ha_multimeter_energy_Wh` | Smart Home (no devices) |
| `fritzbox_power` | n/a | `fritz_ha_multimeter_power_W` | Smart Home (no devices) |
| `fritzbox_switch_state` | n/a | `fritz_ha_switch_state` | Smart Home (no devices) |
| `fritzbox_temperature` | n/a | `fritz_ha_temperature_C` | Smart Home (no devices) |
| `fritzbox_thermostat_battery_charge_level` | n/a | `fritz_ha_battery_level_percent` | Smart Home (no devices) |
| `fritzbox_thermostat_state` | n/a | `fritz_ha_heater_valve_set_state` | Smart Home (no devices) |
| `fritzbox_thermostat_window_open` | n/a | – | Smart Home (no devices) |
| `fritzbox_device_battery_percent` | n/a | `fritz_ha_battery_level_percent` | Smart Home (no devices) |
| `fritzbox_device_hkr_tist_celsius` | n/a | `fritz_ha_heater_temperature_C` | Smart Home (no devices) |
| `fritzbox_device_hkr_tsoll_celsius` | n/a | `fritz_ha_heater_set_temperature_C` | Smart Home (no devices) |
| `docsis` | n/a | – | Cable (DOCSIS) only; your line is DSL |
| `ping` | map | `probe_success / probe_duration_seconds{job="blackbox-icmp"}` | From the blackbox probes |
| `fritzbox_value [type_instance=constatus]` | map | `fritz_ppp_connection_state` |  |
| `fritzbox_value [type_instance=dslstatus]` | map | `fritz_dsl_status` |  |
| `fritzbox_value [type_instance=downstreammax]` | map | `fritz_wan_max_bitrate_bps{direction="rx"}` | Attainable rate; real sync: fritz_dsl_datarate_kbps{direction="rx",type="curr"} * 1000 |
| `fritzbox_value [type_instance=upstreammax]` | map | `fritz_wan_max_bitrate_bps{direction="tx"}` | Attainable rate; real sync: fritz_dsl_datarate_kbps{direction="tx",type="curr"} * 1000 |
| `fritzbox_value [type_instance=receiverate]` | map | `fritz_wan_datarate_bytes{direction="rx"}` |  |
| `fritzbox_value [type_instance=sendrate]` | map | `fritz_wan_datarate_bytes{direction="tx"}` |  |
| `fritzbox_value [type_instance=totalbytesreceived]` | map | `fritz_wan_data_bytes_total{direction="rx"}` |  |
| `fritzbox_value [type_instance=totalbytessent]` | map | `fritz_wan_data_bytes_total{direction="tx"}` |  |
| `fritzbox_value [type_instance=uptime]` | map | `fritz_uptime_seconds_total` |  |
| `fritzbox_value [type_instance=temperature]` | map | `fritz_extras_cpu_temperature_celsius` | From fritz-extras |

## Dashboards surveyed

| ID | Name | Data source | Works today | After translation |
|---|---|---|---|---|
| [713](https://grafana.com/grafana/dashboards/713) | FRITZ!Box Router Status | InfluxDB | 0 % | 100 % |
| [14068](https://grafana.com/grafana/dashboards/14068) | FRITZ!Box Router Status | InfluxDB | 0 % | 100 % |
| [11593](https://grafana.com/grafana/dashboards/11593) | FRITZ!Box | Prometheus | 0 % | 100 % |
| [11490](https://grafana.com/grafana/dashboards/11490) | FRITZ!Box Router Status | InfluxDB | 0 % | 100 % |
| [13279](https://grafana.com/grafana/dashboards/13279) | FRITZ!Box Router Status | InfluxDB | 0 % | 100 % |
| [11434](https://grafana.com/grafana/dashboards/11434) | Fritz!Box Status | InfluxDB | 0 % | 93 % |
| [13848](https://grafana.com/grafana/dashboards/13848) | Internet Dashboard | Prometheus | 0 % | 88 % |
| [13983](https://grafana.com/grafana/dashboards/13983) | Fritz!Exporter | Prometheus | 87 % | 87 % |
| [17751](https://grafana.com/grafana/dashboards/17751) | Fritz!Exporter Dash | Prometheus | 81 % | 81 % |
| [24649](https://grafana.com/grafana/dashboards/24649) | Fritz!Exporter Dash | Prometheus | 81 % | 81 % |
| [13377](https://grafana.com/grafana/dashboards/13377) | FRITZ!Box Status | Prometheus | 0 % | 78 % |
| [12579](https://grafana.com/grafana/dashboards/12579) | FRITZ!Box Status | Prometheus | 0 % | 75 % |
| [20242](https://grafana.com/grafana/dashboards/20242) | FRITZ!Box Status | Prometheus | 0 % | 68 % |
| [16929](https://grafana.com/grafana/dashboards/16929) | Kabelmodem Leitungsqualität + Ping Status | InfluxDB | 0 % | 12 % |
| [11345](https://grafana.com/grafana/dashboards/11345) | FRITZ!Box Home Automation | Prometheus | 0 % | 0 % |
| [7019](https://grafana.com/grafana/dashboards/7019) | FRITZ!Box Smarthome | Prometheus | 0 % | 0 % |
| [19759](https://grafana.com/grafana/dashboards/19759) | FRITZ!Box Smarthome | Prometheus | 0 % | 0 % |
