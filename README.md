# IceWiFi

**Enterprise-grade home network with UniFi, VLAN segmentation, Tor transparent proxy, and Home Assistant integration.**

## Overview

IceWiFi is a documented home network project featuring:
- **UniFi** managed WiFi with multiple SSIDs for different purposes
- **VLAN segmentation** for security isolation
- **Tor transparent proxy** for anonymous browsing
- **MikroTik SwOS** switches with 10G SFP+ backbone
- **Sophos XG** firewall integration
- **Home Assistant** monitoring and dashboards
- **MQTT** for IoT device communication

## Network Architecture

```
Internet
  └── Fritz!Box 6591 Cable
        ├── UniFi Security Gateway (USG 3P)
        │     └── LAN: Managed WiFi + IoT
        │           ├── Cloud Key Plus (Controller)
        │           ├── U6+ AP (1st Floor)
        │           └── U6+ AP (Basement)
        │
        ├── Sophos XG Firewall
        │     └── Inter-VLAN routing & inspection
        │
        └── Home Assistant (NUC)
              ├── MQTT Broker (Mosquitto)
              ├── Tor Transparent Proxy
              ├── SNMP Switch Monitoring
              └── Network Dashboards
```

## VLAN Design

| VLAN | Purpose | Description |
|------|---------|-------------|
| 11 | Internal | Firewall management network |
| 12 | IoT/WiFi | UniFi managed devices, IoT |
| 13 | Tor | Anonymous browsing via transparent proxy |
| 666 | Internet | WAN/Internet access |

## WiFi Networks (SSIDs)

| SSID | Purpose | Features |
|------|---------|----------|
| **Bad:INet** | Standard Internet | Full speed, unrestricted access |
| **Bad!IoT** | IoT Devices | Dedicated for Tasmota/smart home devices, MQTT |
| **Bad!Bad** | Anonymous (Tor) | All traffic routed through Tor network |

### Bad:INet - Standard Internet Access
- Primary WiFi for all devices (phones, laptops, tablets)
- Full internet speed via cable modem
- Standard WPA2 security
- DHCP via UniFi Security Gateway
- Available on all access points

### Bad!IoT - IoT / Smart Home
- Dedicated SSID for IoT devices
- Tasmota-based energy monitors communicate via MQTT
- Connected to Home Assistant's Mosquitto broker
- Logically separated from regular client traffic

### Bad!Bad - Tor Transparent Proxy
- **All traffic automatically routed through Tor**
- No special software needed - works with any device/browser
- DNS queries also routed through Tor
- No access to local network resources (by design)
- Slower speeds (Tor limitation)
- Components:
  - `tor` daemon with TransPort and DNSPort
  - `dnsmasq` for DHCP in the Tor VLAN
  - `iptables` rules for transparent redirection

## Hardware

### Network Equipment
| Device | Model | Role |
|--------|-------|------|
| Modem/Router | Fritz!Box 6591 Cable | Internet uplink |
| Gateway | UniFi USG 3P | Security Gateway, DHCP, Firewall |
| Controller | UniFi Cloud Key Plus | Network management |
| AP (1F) | UniFi U6+ | WiFi access point |
| AP (Basement) | UniFi U6+ | WiFi access point |
| Switch (1F) | MikroTik CSS326-24G-2S+ | 24-port GbE + 2x SFP+ |
| Switch (Basement) | MikroTik CSS326-24G-2S+ | 24-port GbE + 2x SFP+ |
| Backbone | MikroTik CRS305-1G-4S+ | 4x SFP+ aggregation |
| Firewall | Sophos XG | Inter-VLAN security |

### Servers
| Device | Role |
|--------|------|
| Intel NUC | Home Assistant, MQTT, Tor Proxy, Monitoring |
| VMware ESXi | Virtualization host |

## Home Assistant Integration

### Monitoring
- UniFi controller API polling (clients per SSID, AP health, gateway status)
- SNMP switch monitoring (port status, traffic, temperature)
- Network health dashboard with status indicators
- Automated alerts for network issues

### MQTT IoT
- Mosquitto broker accessible from IoT VLAN
- Tasmota energy monitoring sensors (PV, appliances)
- Switches for remote power control

### Dashboards
- **Network Overview**: VLAN status, switch ports, AP health
- **UniFi Monitor**: Per-SSID clients, AP details, gateway throughput, WiFi quality
- **Kiosk Mode**: Tablet-optimized view for Galaxy Tab with network status

## Tor Transparent Proxy

The Tor VLAN provides completely transparent anonymization:

```
Client --> WiFi (Bad!Bad) --> VLAN 13 --> iptables REDIRECT --> Tor --> Internet
                                       --> DNS REDIRECT --> Tor DNSPort
```

**Key features:**
- Zero client configuration needed
- Works with any device (phones, laptops, IoT)
- DNS leak protection (all DNS through Tor)
- No access to local LAN (isolation)

**Systemd services:**
- `tor@default` - Tor daemon
- `dnsmasq-tor` - DHCP server for Tor VLAN
- `iptables-tor` - NAT redirect rules

## Switch Management

MikroTik switches are managed via SwOS web interface and REST API:
- VLAN trunk configuration across all switch ports
- SFP+ 10Gbit backbone between floors
- SNMP monitoring integrated into Home Assistant

## Backup Strategy

| Component | Method | Schedule |
|-----------|--------|----------|
| Home Assistant | HA Backup (encrypted) | Daily |
| UniFi Controller | API backup script | Daily |
| Network Config | Config file backup | Daily |
| Switch Configs | SwOS backup export | Manual |

## Documentation

- [Online Documentation](https://www.mpauli.de/icewifi/)
- `public/` - Public HTML documentation (admin guide, user guide, troubleshooting)
- `generate.py` - Documentation generator (single-command update)

### Usage

```bash
# Generate documentation
cd /root/IceWiFi && python3 generate.py

# Generate and deploy everywhere
python3 generate.py --deploy

# Generate with fresh screenshots
python3 generate.py --deploy --screenshots
```

## Project Structure

```
IceWiFi/
├── README.md                    # This file
├── generate.py                  # Documentation generator & deployer
├── .gitignore                   # Excludes private data, screenshots
├── public/                      # Public documentation (HTML)
│   ├── index.html               # Landing page
│   ├── admin-guide.html         # Administration guide (sanitized)
│   ├── user-guide.html          # End-user WiFi guide
│   ├── network-topology.html    # Interactive network topology
│   ├── backup-restore.html      # Backup & restore procedures
│   ├── troubleshooting.html     # Troubleshooting guide
│   ├── css/style.css            # Dark theme stylesheet
│   └── diagrams/
│       ├── topology.svg         # Network topology diagram
│       └── vlan-map.svg         # VLAN mapping diagram
├── ha-config/                   # Home Assistant config examples
│   ├── packages/
│   │   └── unifi.yaml           # UniFi monitoring sensors (sanitized)
│   └── dashboards/
│       └── network.yaml         # Network dashboard (sanitized)
├── private/                     # Private docs (gitignored)
├── scripts/                     # Utility scripts
└── templates/                   # Documentation templates
```

## License

This project documents a personal home network setup. Feel free to use the architecture and configuration concepts for your own network.

## Author

Marcus Pauli - [mpauli.de](https://www.mpauli.de/icewifi/)

---

*Built with UniFi, MikroTik SwOS, Sophos XG, Home Assistant, and Tor.*
