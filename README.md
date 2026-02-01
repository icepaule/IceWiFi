# IceWiFi - Network Documentation

Network documentation for a multi-VLAN home network setup with UniFi, Sophos, Fritz!Box, and Home Assistant.

## Architecture

- **UniFi** - USG 3P Gateway, Cloud Key Plus Controller, 2x U6+ APs
- **Sophos XG** - Firewall between VLANs
- **Fritz!Box** - Internet gateway
- **MikroTik SwOS** - Managed switches with VLAN trunking (SFP+ backbone)
- **Home Assistant** - Monitoring and automation
- **Tor Transparent Proxy** - Anonymous VLAN via dedicated SSID

## VLANs

| VLAN | Subnet | Purpose |
|------|--------|---------|
| 11 | 10.10.0.0/24 | Sophos Management |
| 12 | 10.10.10.0/24 | IoT / UniFi |
| 13 | 10.10.13.0/24 | Tor Transparent Proxy |
| 666 | 192.168.178.0/24 | Internet / Fritz!Box |

## SSIDs

| SSID | Purpose |
|------|---------|
| Bad:INet | Internet access |
| Bad!IoT | IoT devices |
| Bad!Bad | Tor anonymous browsing |
| Bad!Net | Fritz!Box WiFi (fallback) |

## Documentation

- [Online Documentation](https://www.mpauli.de/icewifi/)
- `public/` - Public documentation (HTML, CSS, SVG diagrams)
- `generate.py` - Documentation generator (single-command update)

## Usage

```bash
# Generate documentation
cd /root/IceWiFi && python3 generate.py

# Generate and deploy everywhere
python3 generate.py --deploy

# Generate with fresh screenshots
python3 generate.py --deploy --screenshots
```

## License

Private documentation project.
