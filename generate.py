#!/usr/bin/env python3
"""
IceWiFi Documentation Generator
================================
Generates public and private network documentation from a single config source.

Usage:
    ./generate.py              # Generate both public and private docs
    ./generate.py --public     # Generate only public docs
    ./generate.py --private    # Generate only private docs
    ./generate.py --deploy     # Generate + deploy (git push + SCP + HA copy)
    ./generate.py --screenshots # Also refresh screenshots before generating

Config: icewifi-config.json (single source of truth)
"""

import json
import os
import sys
import shutil
import subprocess
import argparse
from datetime import datetime
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "icewifi-config.json"
PUBLIC_DIR = BASE_DIR / "public"
PRIVATE_DIR = Path("/var/lib/homeassistant/homeassistant/www/network-docs")
SCREENSHOT_DIR = PRIVATE_DIR / "screenshots"
TEMPLATE_CSS = PUBLIC_DIR / "css" / "style.css"

def load_config():
    with open(CONFIG_FILE) as f:
        return json.load(f)

def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# =============================================================================
# HTML Templates
# =============================================================================

def html_head(title, css_path="css/style.css", is_private=False):
    private_badge = '<span class="badge badge-private">PRIVAT</span>' if is_private else ''
    return f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - IceWiFi</title>
    <link rel="stylesheet" href="{css_path}">
</head>
<body>
<header>
    <div class="header-content">
        <h1>IceWiFi {private_badge}</h1>
        <nav>
            <a href="index.html">Start</a>
            <a href="admin-guide.html">Admin Guide</a>
            <a href="user-guide.html">User Guide</a>
            <a href="network-topology.html">Topologie</a>
            <a href="backup-restore.html">Backup</a>
            <a href="troubleshooting.html">Troubleshooting</a>"""

def html_head_private_extra():
    return """
            <a href="quick-reference.html" class="nav-private">Quick Ref</a>
            <a href="ssh-commands.html" class="nav-private">SSH</a>
            <a href="mongodb-commands.html" class="nav-private">MongoDB</a>"""

def html_head_close():
    return f"""
        </nav>
    </div>
</header>
<main>
"""

def html_foot(is_private=False):
    gen_info = f'Generiert: {timestamp()}'
    return f"""
</main>
<footer>
    <p>IceWiFi Netzwerk-Dokumentation | {gen_info}</p>
    <p>{"PRIVATE VERSION - Nicht veroeffentlichen!" if is_private else '<a href="https://github.com/icepaule/IceWiFi">GitHub</a>'}</p>
</footer>
</body>
</html>"""

def page_wrapper(title, content, is_private=False, css_path="css/style.css"):
    head = html_head(title, css_path, is_private)
    if is_private:
        head += html_head_private_extra()
    head += html_head_close()
    return head + content + html_foot(is_private)

# =============================================================================
# Sanitize for Public
# =============================================================================

SENSITIVE_PATTERNS = [
    "usual_Brutal9Clutch", "IceWiFi2026!", "HxmO1kUnp2Z", "gBqfpbLXM",
    "BadBadTor13", "MeinWiFiistSicher", "s3cr3t",
    "KFZ0-S89A-861I-ZK5H-7Q3Q-TD86-80DW",
    "70a741966779067b103406c8bbda062afd56d",
    "mpauli67@gmail.com",
    "94:c6:91:aa:9e:c3", "dc:8b:28:0d:e2:97",
    "70:a7:41:96:67:79", "fc:ec:da:d3:17:79", "fc:ec:da:d3:17:7a",
    "0c:ea:14:c0:fa:34", "0c:ea:14:8c:68:fd",
    "48:8f:5a:11:d8:0c", "48:8f:5a:11:d9:ca",
    "74:4d:28:d7:d8:29", "b0:f2:08:4d:23:d3", "74:d6:37:a4:06:68",
]

def sanitize_public(text):
    """Remove all sensitive data from public documentation."""
    replacements = {
        "usual_Brutal9Clutch": "••••••••",
        "IceWiFi2026!": "••••••••",
        "HxmO1kUnp2Z": "••••••••",
        "gBqfpbLXM": "admin-user",
        "BadBadTor13": "••••••••",
        "MeinWiFiistSicher": "••••••••",
        "s3cr3t": "••••••••",
        "KFZ0-S89A-861I-ZK5H-7Q3Q-TD86-80DW": "••••-••••-••••-••••",
        "70a741966779067b103406c8bbda062afd56d": "••••••••.id.ui.direct",
        "mpauli67@gmail.com": "user@example.com",
        "192.168.178.1": "192.168.x.1",
        "192.168.178.108": "192.168.x.108",
        "192.168.178.250": "192.168.x.250",
        "192.168.178.154": "192.168.x.154",
        "192.168.178.165": "192.168.x.165",
        "192.168.178.191": "192.168.x.191",
        "192.168.178.174": "192.168.x.174",
        "192.168.1.8": "192.168.y.8",
        "192.168.1.20": "192.168.y.20",
    }
    for pattern in SENSITIVE_PATTERNS:
        if pattern not in replacements:
            replacements[pattern] = "xx:xx:xx:xx:xx:xx" if ":" in pattern and len(pattern) == 17 else "••••••••"
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

# =============================================================================
# Page Generators
# =============================================================================

def gen_index(cfg, is_private=False):
    devices = cfg["devices"]
    vlans = cfg["network"]["vlans"]
    content = """
<section class="hero">
    <h2>Netzwerk-Dokumentation</h2>
    <p>Komplette Dokumentation des Heimnetzwerks mit UniFi, Sophos, Fritz!Box und Home Assistant.</p>
</section>

<section class="cards">
    <div class="card">
        <h3>VLANs</h3>
        <table>
            <tr><th>VLAN</th><th>Subnet</th><th>Zweck</th></tr>
"""
    for vid, v in vlans.items():
        content += f'            <tr><td><span class="vlan-badge" style="background:{v["color"]}">{vid}</span></td><td><code>{v["subnet"]}</code></td><td>{v["name"]}</td></tr>\n'
    content += """        </table>
    </div>

    <div class="card">
        <h3>SSIDs</h3>
        <table>
            <tr><th>SSID</th><th>VLAN</th><th>Zweck</th></tr>
"""
    for ssid, s in cfg["network"]["ssids"].items():
        content += f'            <tr><td><code>{ssid}</code></td><td>{s["vlan"]}</td><td>{s["purpose"]}</td></tr>\n'
    content += """        </table>
    </div>

    <div class="card">
        <h3>Geraete</h3>
        <table>
            <tr><th>Geraet</th><th>IP</th><th>Rolle</th></tr>
"""
    for key, d in devices.items():
        ip = d.get("ip", d.get("ip_wan", d.get("ip_wifi", d.get("ip_internal", "-"))))
        role = d.get("role", d.get("type", "-"))
        content += f'            <tr><td>{d["name"]}</td><td><code>{ip}</code></td><td>{role}</td></tr>\n'
    content += """        </table>
    </div>

    <div class="card">
        <h3>Services</h3>
        <table>
            <tr><th>Service</th><th>Status</th><th>Beschreibung</th></tr>
"""
    for key, s in cfg["services"].items():
        status = '<span class="badge badge-ok">persistent</span>' if s["persistent"] else '<span class="badge badge-warn">manuell</span>'
        content += f'            <tr><td><code>{s["name"]}</code></td><td>{status}</td><td>{s["description"]}</td></tr>\n'
    content += """        </table>
    </div>
</section>
"""
    if is_private:
        content += """
<section class="cards">
    <div class="card card-private">
        <h3>Schnellzugriff</h3>
        <ul>
"""
        for key, d in devices.items():
            web = d.get("web", "")
            if web:
                content += f'            <li><a href="{web}" target="_blank">{d["name"]}</a> - {web}</li>\n'
        content += """        </ul>
    </div>
</section>
"""
    return page_wrapper("Start", content, is_private)


def gen_admin_guide(cfg, is_private=False):
    content = """
<h2>Admin Guide</h2>

<section class="card">
    <h3>VLAN-Konfiguration</h3>
    <p>Das Netzwerk ist in mehrere VLANs segmentiert, die ueber MikroTik SwOS Switches getrunked werden.</p>

    <h4>VLAN-Uebersicht</h4>
    <table>
        <tr><th>VLAN</th><th>Subnet</th><th>Gateway</th><th>Zweck</th><th>DHCP</th></tr>
        <tr><td>11</td><td>10.10.0.0/24</td><td>10.10.0.2 (Sophos)</td><td>Sophos Internal</td><td>Nein</td></tr>
        <tr><td>12</td><td>10.10.10.0/24</td><td>10.10.10.1 (USG)</td><td>IoT / UniFi</td><td>USG</td></tr>
        <tr><td>13</td><td>10.10.13.0/24</td><td>10.10.13.1 (NUC)</td><td>Tor Transparent Proxy</td><td>dnsmasq-tor</td></tr>
        <tr><td>666</td><td>192.168.178.0/24</td><td>192.168.178.1 (Fritz!Box)</td><td>Internet / Fritz!Box</td><td>Fritz!Box</td></tr>
    </table>
</section>

<section class="card">
    <h3>Switch Port-Zuordnung (Arbeitszimmer)</h3>
    <table>
        <tr><th>Port</th><th>Geraet</th><th>Modus</th><th>PVID</th><th>VLANs</th></tr>
        <tr><td>19</td><td>CK+ Cloud Key</td><td>TRUNK</td><td>12</td><td>1, 11, 12, 13</td></tr>
        <tr><td>20</td><td>USG WAN</td><td>TRUNK</td><td>666</td><td>666</td></tr>
        <tr><td>21</td><td>USG LAN</td><td>TRUNK</td><td>12</td><td>1, 10, 11, 12</td></tr>
        <tr><td>22</td><td>U6+ Arbeitszimmer</td><td>TRUNK</td><td>12</td><td>1, 10, 11, 12, 13</td></tr>
        <tr><td>24</td><td>NUC-HA</td><td>TRUNK</td><td>666</td><td>Alle</td></tr>
        <tr><td>25-26</td><td>SFP+ Backbone</td><td>TRUNK</td><td>666</td><td>Alle</td></tr>
    </table>
</section>

<section class="card">
    <h3>Switch Port-Zuordnung (Keller)</h3>
    <table>
        <tr><th>Port</th><th>Geraet</th><th>Modus</th><th>PVID</th><th>VLANs</th></tr>
        <tr><td>1-4</td><td>ESXi7 (vmnic0-3)</td><td>TRUNK</td><td>1</td><td>1, 11, 12, 666</td></tr>
        <tr><td>5</td><td>ESXi7 iLO</td><td>ACCESS</td><td>666</td><td>-</td></tr>
        <tr><td>8</td><td>KI01</td><td>TRUNK</td><td>12</td><td>1, 12</td></tr>
        <tr><td>23</td><td>U6+ Keller</td><td>TRUNK</td><td>12</td><td>1, 12, 13</td></tr>
        <tr><td>24</td><td>Fritz!Box</td><td>ACCESS</td><td>666</td><td>-</td></tr>
        <tr><td>25</td><td>SFP+ nach 1.OG</td><td>TRUNK</td><td>666</td><td>Alle</td></tr>
    </table>
</section>

<section class="card">
    <h3>UniFi Controller (CK+)</h3>
    <p>Der UniFi Controller laeuft auf einem Cloud Key Plus (UCK G2+) im VLAN 12.</p>
    <ul>
        <li><strong>Zugriff vom NUC:</strong> via socat-Proxy auf <code>127.0.0.1:8443</code></li>
        <li><strong>Direkt:</strong> <code>https://10.10.10.10</code> (aus VLAN 12)</li>
        <li><strong>Verwaltete Geraete:</strong> USG 3P, 2x U6+ APs</li>
        <li><strong>MongoDB:</strong> Port 27117, Datenbank <code>ace</code></li>
    </ul>
"""
    if is_private:
        content += """
    <div class="private-info">
        <h4>Credentials</h4>
        <table>
            <tr><th>Zugang</th><th>User</th><th>Passwort</th></tr>
            <tr><td>CK+ SSH</td><td><code>root</code></td><td><code>usual_Brutal9Clutch</code></td></tr>
            <tr><td>CK+ HA-Admin</td><td><code>icewifi-admin</code></td><td><code>IceWiFi2026!</code></td></tr>
            <tr><td>USG SSH</td><td><code>gBqfpbLXM</code></td><td><code>HxmO1kUnp2Z</code></td></tr>
        </table>
        <p><strong>Hinweis:</strong> CK+ SSH funktioniert nur per <code>expect</code> (keyboard-interactive Auth).</p>
    </div>
"""
    content += """
</section>

<section class="card">
    <h3>Tor Transparent Proxy (VLAN 13)</h3>
    <p>VLAN 13 routet allen Traffic ueber das Tor-Netzwerk. Geraete im SSID "Bad!Bad" erhalten
    automatisch eine IP via DHCP und werden transparent durch Tor geleitet.</p>

    <h4>Komponenten</h4>
    <table>
        <tr><th>Service</th><th>Funktion</th><th>Config</th></tr>
        <tr><td><code>tor@default</code></td><td>Tor Daemon (TransPort 9040, DNSPort 5399)</td><td><code>/etc/tor/torrc</code></td></tr>
        <tr><td><code>dnsmasq-tor</code></td><td>DHCP fuer VLAN 13</td><td><code>/etc/dnsmasq.d/tor-vlan13.conf</code></td></tr>
        <tr><td><code>iptables-tor</code></td><td>NAT-Redirect DNS→5399, TCP→9040</td><td>systemd ExecStart</td></tr>
    </table>

    <h4>Tor-Konfiguration</h4>
    <pre><code>SocksPort 0
VirtualAddrNetworkIPv4 10.192.0.0/10
AutomapHostsOnResolve 1
TransPort 10.10.13.1:9040
DNSPort 10.10.13.1:5399</code></pre>
</section>

<section class="card">
    <h3>Firewall (USG)</h3>
    <p>Die USG Firewall-Regeln werden ueber die MongoDB auf dem CK+ verwaltet.</p>

    <h4>LAN_IN Regelkette</h4>
    <table>
        <tr><th>Index</th><th>Aktion</th><th>Beschreibung</th></tr>
        <tr><td>2000</td><td>RETURN</td><td>ESTABLISHED/RELATED aus NUC-Subnet</td></tr>
        <tr><td>2001</td><td>RETURN</td><td>NEW TCP zu NUC Services (1883, 8883, 8123)</td></tr>
        <tr><td>2002</td><td>RETURN</td><td>DNS (TCP+UDP) zur USG</td></tr>
        <tr><td>2003</td><td>RETURN</td><td>NTP (UDP)</td></tr>
        <tr><td>6001</td><td>RETURN</td><td>Allow 10.10.10.0/24 Traffic</td></tr>
        <tr><td>10000</td><td>RETURN</td><td>Default</td></tr>
    </table>
</section>

<section class="card">
    <h3>Sophos XG Firewall</h3>
    <p>Die Sophos Firewall sitzt zwischen VLAN 11 (internal), VLAN 12 (IoT) und VLAN 666 (Internet).</p>
    <table>
        <tr><th>Interface</th><th>IP</th><th>VLAN</th></tr>
        <tr><td>eth0</td><td>10.10.0.2</td><td>11 (Internal)</td></tr>
        <tr><td>eth1</td><td>192.168.178.154</td><td>666 (Internet)</td></tr>
        <tr><td>eth2</td><td>10.10.10.2</td><td>12 (IoT)</td></tr>
    </table>
"""
    if is_private:
        content += """
    <div class="private-info">
        <p><strong>Web Admin:</strong> <a href="https://10.10.0.2:4444" target="_blank">https://10.10.0.2:4444</a></p>
        <p><strong>Zugang vom NUC:</strong> ueber eno1.11 (10.10.0.100)</p>
    </div>
"""
    content += """
</section>

<section class="card">
    <h3>Home Assistant Integration</h3>
    <p>Home Assistant laeuft als Docker-Container auf dem NUC und ist ueber die Bridge-IP erreichbar.</p>
    <ul>
        <li><strong>Config:</strong> <code>/var/lib/homeassistant/homeassistant/</code></li>
        <li><strong>Web:</strong> <code>http://192.168.178.108:8123</code></li>
        <li><strong>UniFi Package:</strong> <code>packages/unifi.yaml</code></li>
        <li><strong>Netzwerk Dashboard:</strong> <code>dashboards/network.yaml</code></li>
    </ul>

    <h4>Systemd Services (IceWiFi)</h4>
    <pre><code># Status pruefen
systemctl status socat-unifi dnsmasq-tor iptables-tor

# Neustarten
systemctl restart socat-unifi dnsmasq-tor iptables-tor

# Logs
journalctl -u socat-unifi -u dnsmasq-tor -u iptables-tor --since today</code></pre>
</section>
"""
    return page_wrapper("Admin Guide", content, is_private)


def gen_user_guide(cfg, is_private=False):
    content = """
<h2>User Guide</h2>

<section class="card">
    <h3>Verfuegbare WLANs</h3>

    <div class="ssid-card">
        <h4>Bad:INet</h4>
        <p class="ssid-purpose">Normaler Internet-Zugang</p>
        <p>Standard-WLAN fuer alle Geraete mit Internet-Zugang. Laeuft ueber den UniFi Controller und USG.</p>
"""
    if is_private:
        content += '        <p class="private-info"><strong>Passwort:</strong> <code>[im UniFi Controller konfiguriert]</code></p>\n'
    content += """
    </div>

    <div class="ssid-card">
        <h4>Bad!IoT</h4>
        <p class="ssid-purpose">IoT-Geraete (Tasmota, Sensoren)</p>
        <p>Fuer Smart-Home-Geraete. Gleicher IP-Bereich wie Bad:INet, aber logisch getrennt.</p>
"""
    if is_private:
        content += '        <p class="private-info"><strong>Rescue Passwort:</strong> <code>MeinWiFiistSicher</code></p>\n'
    content += """
    </div>

    <div class="ssid-card">
        <h4>Bad!Bad</h4>
        <p class="ssid-purpose">Anonymer Tor-Zugang</p>
        <p>Aller Traffic wird automatisch ueber das Tor-Netzwerk geroutet.
        Ideal fuer anonymes Surfen. Kein Zugriff auf lokale Netzwerk-Ressourcen.</p>
"""
    if is_private:
        content += '        <p class="private-info"><strong>Passwort:</strong> <code>BadBadTor13</code></p>\n'
    content += """
    </div>

    <div class="ssid-card">
        <h4>Bad!Net</h4>
        <p class="ssid-purpose">Fritz!Box WiFi (direkt)</p>
        <p>Direktes Fritz!Box-WLAN ohne UniFi. Fuer Fallback-Zugang wenn UniFi nicht verfuegbar.</p>
    </div>
</section>

<section class="card">
    <h3>Verbindungsanleitung</h3>
    <ol>
        <li>WLAN-Einstellungen auf dem Geraet oeffnen</li>
        <li>Gewuenschtes Netzwerk auswaehlen (Bad:INet fuer normalen Zugang)</li>
        <li>Passwort eingeben</li>
        <li>Verbindung wird automatisch hergestellt</li>
    </ol>

    <h4>Tor-WLAN (Bad!Bad) Hinweise</h4>
    <ul>
        <li>Geschwindigkeit ist deutlich langsamer (Tor-typisch)</li>
        <li>Manche Websites blockieren Tor-Exit-Nodes</li>
        <li>DNS-Anfragen werden ebenfalls ueber Tor geleitet</li>
        <li>Kein Zugriff auf lokale Geraete (Drucker, NAS, etc.)</li>
    </ul>
</section>
"""
    return page_wrapper("User Guide", content, is_private)


def gen_topology(cfg, is_private=False):
    content = """
<h2>Netzwerk-Topologie</h2>

<section class="card">
    <h3>Physische Topologie</h3>
    <div class="diagram-container">
        <img src="diagrams/topology.svg" alt="Netzwerk-Topologie" class="diagram">
    </div>
</section>

<section class="card">
    <h3>VLAN-Map</h3>
    <div class="diagram-container">
        <img src="diagrams/vlan-map.svg" alt="VLAN Map" class="diagram">
    </div>
</section>

<section class="card">
    <h3>Physische Verbindungen (Text)</h3>
    <pre><code>Internet
  └── Fritz!Box (192.168.178.1)
        ├── USG 3P (WAN: 192.168.178.250)
        │     └── LAN: 10.10.10.1/24
        │           ├── SW Arbeitszimmer
        │           │     ├── Port 19: CK+ (10.10.10.10)
        │           │     ├── Port 20: USG WAN
        │           │     ├── Port 21: USG LAN
        │           │     ├── Port 22: U6+ AZ (10.10.10.11)
        │           │     ├── Port 24: NUC-HA
        │           │     └── Port 25-26: SFP+ → Backbone
        │           │
        │           └── CRS305 Backbone (SFP+)
        │                 └── SW Keller
        │                       ├── Port 1-5: ESXi7
        │                       ├── Port 8: KI01
        │                       ├── Port 23: U6+ Keller (10.10.10.12)
        │                       ├── Port 24: Fritz!Box
        │                       └── Port 25: SFP+ → 1.OG
        │
        ├── Sophos XG (192.168.178.154)
        │     ├── eth0: 10.10.0.2 (VLAN 11)
        │     └── eth2: 10.10.10.2 (VLAN 12)
        │
        └── NUC-HA (192.168.178.108 WiFi)
              ├── eno1.11: 10.10.0.100 (Sophos)
              ├── eno1.12: 10.10.10.100 (IoT/UniFi)
              └── eno1.13: 10.10.13.1 (Tor Gateway)</code></pre>
</section>

<section class="card">
    <h3>Routing (NUC)</h3>
    <pre><code>default via 192.168.178.1 dev wlp0s20f3  (WiFi → Internet)
10.10.0.0/24  dev eno1.11  src 10.10.0.100   (VLAN 11 → Sophos)
10.10.10.0/24 dev eno1.12  src 10.10.10.100  (VLAN 12 → IoT/UniFi)
10.10.13.0/24 dev eno1.13  src 10.10.13.1    (VLAN 13 → Tor)
172.30.32.0/23 dev hassio  src 172.30.32.1   (Home Assistant)</code></pre>
</section>
"""
    return page_wrapper("Netzwerk-Topologie", content, is_private)


def gen_backup_restore(cfg, is_private=False):
    content = """
<h2>Backup &amp; Restore</h2>

<section class="card">
    <h3>Backup-Uebersicht</h3>
    <table>
        <tr><th>Was</th><th>Wie</th><th>Wann</th><th>Aufbewahrung</th></tr>
        <tr><td>Home Assistant</td><td>HA Backup (automatisch)</td><td>Taeglich 05:00</td><td>3 Kopien</td></tr>
        <tr><td>UniFi Controller</td><td><code>backup-unifi.sh</code></td><td>Taeglich 03:00</td><td>7 Backups</td></tr>
        <tr><td>Netzwerk-Config</td><td><code>backup-network-config.sh</code></td><td>Taeglich 03:00</td><td>30 Backups</td></tr>
        <tr><td>Switch-Configs</td><td><code>switch_backup/</code></td><td>Manuell</td><td>Unbegrenzt</td></tr>
    </table>
</section>

<section class="card">
    <h3>UniFi Backup</h3>
    <pre><code># Manuelles Backup
/usr/local/bin/backup-unifi.sh

# Backup-Verzeichnis
ls -la /var/backups/icewifi/unifi/

# Restore: Backup-Datei im CK+ Controller importieren
# via https://10.10.10.10 → Settings → Backup</code></pre>
</section>

<section class="card">
    <h3>Netzwerk-Config Backup</h3>
    <pre><code># Manuelles Backup
/usr/local/bin/backup-network-config.sh

# Inhalt: iptables, NetworkManager, dnsmasq, tor, systemd units
ls -la /var/backups/icewifi/config/</code></pre>
</section>

<section class="card">
    <h3>Home Assistant Restore</h3>
    <pre><code># Backups auflisten
ha backups list

# Restore (Container wird neu gestartet)
ha backups restore &lt;slug&gt; --homeassistant</code></pre>
"""
    if is_private:
        content += f"""
    <div class="private-info">
        <p><strong>HA Backup Encryption Key:</strong> <code>{cfg["backup"]["ha_encryption_key"]}</code></p>
    </div>
"""
    content += """
</section>

<section class="card">
    <h3>Disaster Recovery</h3>
    <ol>
        <li>NUC mit Debian 13 neu installieren</li>
        <li>Home Assistant Supervised installieren</li>
        <li>HA Backup wiederherstellen (Encryption Key benoetigt)</li>
        <li>VLAN-Interfaces einrichten (eno1.11, eno1.12, eno1.13)</li>
        <li>Systemd Services deployen (socat, dnsmasq, iptables)</li>
        <li>IceWiFi Dokumentation von GitHub klonen</li>
    </ol>
</section>
"""
    return page_wrapper("Backup & Restore", content, is_private)


def gen_troubleshooting(cfg, is_private=False):
    content = """
<h2>Troubleshooting</h2>

<section class="card">
    <h3>Service-Status pruefen</h3>
    <pre><code># Alle IceWiFi Services
systemctl status socat-unifi dnsmasq-tor iptables-tor tor@default

# VLAN Interfaces
ip addr show eno1.11 eno1.12 eno1.13

# Routing
ip route show

# iptables Tor-Regeln
iptables -t nat -L PREROUTING -n -v | grep eno1.13</code></pre>
</section>

<section class="card">
    <h3>UniFi Controller nicht erreichbar</h3>
    <ol>
        <li>Socat-Proxy pruefen: <code>systemctl status socat-unifi</code></li>
        <li>VLAN 12 Interface: <code>ip addr show eno1.12</code></li>
        <li>CK+ erreichbar: <code>ping -c 3 10.10.10.10</code></li>
        <li>CK+ HTTPS: <code>curl -sk https://10.10.10.10/status</code></li>
        <li>Socat neustarten: <code>systemctl restart socat-unifi</code></li>
    </ol>
</section>

<section class="card">
    <h3>Tor-WLAN (Bad!Bad) funktioniert nicht</h3>
    <ol>
        <li>DHCP pruefen: <code>systemctl status dnsmasq-tor</code></li>
        <li>Tor-Daemon: <code>systemctl status tor@default</code></li>
        <li>iptables-Regeln: <code>systemctl status iptables-tor</code></li>
        <li>VLAN 13 Interface: <code>ip addr show eno1.13</code></li>
        <li>Tor Bootstrap: <code>journalctl -u tor@default | grep Bootstrap</code></li>
        <li>Alles neustarten:
            <pre><code>systemctl restart iptables-tor dnsmasq-tor tor@default</code></pre>
        </li>
    </ol>
</section>

<section class="card">
    <h3>VLAN-Interface kommt nicht hoch</h3>
    <pre><code># NetworkManager Verbindungen pruefen
nmcli con show

# Autoconnect pruefen
nmcli con show "eno1.11" | grep autoconnect
nmcli con show "eno1.12" | grep autoconnect

# Manuell aktivieren
nmcli con up "eno1.11"
nmcli con up "eno1.12"

# Basis-Interface pruefen
ip link show eno1</code></pre>
</section>

<section class="card">
    <h3>CK+ SSH-Zugang</h3>
    <p>Der CK+ akzeptiert nur keyboard-interactive Auth. Normaler SSH funktioniert nicht.</p>
    <pre><code># Expect-basierter SSH-Zugang
expect -c '
  spawn ssh root@10.10.10.10
  expect "Password:"
  send "PASSWORT\\r"
  interact
'</code></pre>
</section>

<section class="card">
    <h3>Home Assistant neustarten</h3>
    <pre><code># HA Core neustarten (schnell)
ha core restart

# HA Supervisor neustarten
ha supervisor restart

# Kompletter Docker-Neustart (langsam)
systemctl restart hassio-supervisor

# Konfiguration validieren
ha core check</code></pre>
</section>

<section class="card">
    <h3>Screenshots neu generieren</h3>
    <pre><code># Manuell
python3 /root/scripts/icewifi-screenshots.py

# Via systemd
systemctl start icewifi-screenshots

# Timer-Status
systemctl list-timers icewifi-screenshots.timer</code></pre>
</section>

<section class="card">
    <h3>Dokumentation neu generieren</h3>
    <pre><code># Nur generieren
cd /root/IceWiFi && python3 generate.py

# Generieren + Deployen
cd /root/IceWiFi && python3 generate.py --deploy

# Nur private Doku
cd /root/IceWiFi && python3 generate.py --private

# Mit frischen Screenshots
cd /root/IceWiFi && python3 generate.py --deploy --screenshots</code></pre>
</section>
"""
    return page_wrapper("Troubleshooting", content, is_private)


# =============================================================================
# Private-Only Pages
# =============================================================================

def gen_quick_reference(cfg):
    devices = cfg["devices"]
    content = """
<h2>Quick Reference - Alle Credentials</h2>
<p class="warning">DIESE SEITE NIEMALS VEROEFFENTLICHEN!</p>

<section class="card card-private">
    <h3>SSH Zugaenge</h3>
    <table>
        <tr><th>Geraet</th><th>IP</th><th>User</th><th>Passwort</th><th>Hinweis</th></tr>
"""
    ssh_devices = [
        ("CK+ Cloud Key", "10.10.10.10", "root", "usual_Brutal9Clutch", "Nur keyboard-interactive (expect)"),
        ("USG 3P", "10.10.10.1", "gBqfpbLXM", "HxmO1kUnp2Z", "Auto-generated"),
        ("NUC-HA", "192.168.178.108", "root", "(SSH-Key)", "Ed25519"),
        ("ESXi7", "192.168.178.174", "mpauli", "usual_Brutal9Clutch", "SSH"),
    ]
    for name, ip, user, pw, note in ssh_devices:
        content += f'        <tr><td>{name}</td><td><code>{ip}</code></td><td><code>{user}</code></td><td><code>{pw}</code></td><td>{note}</td></tr>\n'
    content += """    </table>
</section>

<section class="card card-private">
    <h3>Web-Interfaces</h3>
    <table>
        <tr><th>Service</th><th>URL</th><th>User</th><th>Passwort</th></tr>
        <tr><td>UniFi Controller</td><td><a href="https://10.10.10.10" target="_blank">https://10.10.10.10</a></td><td>icewifi-admin</td><td><code>IceWiFi2026!</code></td></tr>
        <tr><td>UniFi (via Proxy)</td><td><a href="https://127.0.0.1:8443" target="_blank">https://127.0.0.1:8443</a></td><td>icewifi-admin</td><td><code>IceWiFi2026!</code></td></tr>
        <tr><td>Fritz!Box</td><td><a href="http://192.168.178.1" target="_blank">http://192.168.178.1</a></td><td>-</td><td>-</td></tr>
        <tr><td>Sophos XG</td><td><a href="https://10.10.0.2:4444" target="_blank">https://10.10.0.2:4444</a></td><td>-</td><td>-</td></tr>
        <tr><td>Home Assistant</td><td><a href="http://192.168.178.108:8123" target="_blank">http://192.168.178.108:8123</a></td><td>-</td><td>-</td></tr>
        <tr><td>SW Keller</td><td><a href="http://192.168.178.165" target="_blank">http://192.168.178.165</a></td><td>admin</td><td>(leer)</td></tr>
        <tr><td>CRS305 Backbone</td><td><a href="http://192.168.178.191" target="_blank">http://192.168.178.191</a></td><td>admin</td><td>-</td></tr>
        <tr><td>ESXi7</td><td><a href="https://192.168.178.174" target="_blank">https://192.168.178.174</a></td><td>mpauli</td><td><code>usual_Brutal9Clutch</code></td></tr>
    </table>
</section>

<section class="card card-private">
    <h3>WLAN Passwoerter</h3>
    <table>
        <tr><th>SSID</th><th>Passwort</th><th>VLAN</th></tr>
        <tr><td>Bad!Bad</td><td><code>BadBadTor13</code></td><td>13 (Tor)</td></tr>
        <tr><td>Bad!IoT (Rescue)</td><td><code>MeinWiFiistSicher</code></td><td>Default</td></tr>
    </table>
</section>

<section class="card card-private">
    <h3>SNMP Communities</h3>
    <table>
        <tr><th>Geraet</th><th>IP</th><th>Community</th></tr>
        <tr><td>SW Arbeitszimmer</td><td>192.168.1.20</td><td><code>public</code></td></tr>
        <tr><td>SW Keller</td><td>192.168.178.165</td><td><code>public</code></td></tr>
        <tr><td>CRS305 Backbone</td><td>192.168.178.191</td><td><code>s3cr3t</code></td></tr>
    </table>
</section>

<section class="card card-private">
    <h3>Sonstige Keys</h3>
    <table>
        <tr><th>Was</th><th>Wert</th></tr>
        <tr><td>HA Backup Encryption</td><td><code>KFZ0-S89A-861I-ZK5H-7Q3Q-TD86-80DW</code></td></tr>
        <tr><td>NUC SSH Public Key</td><td><code>ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINdmD3pzyFM9M+CWpYmOhw9dqVSIQQc+11A+DtjLUcJ3 root@NUC-HA</code></td></tr>
        <tr><td>CK+ Direct Connect</td><td><code>70a741966779067b103406c8bbda062afd56d.id.ui.direct</code></td></tr>
    </table>
</section>
"""
    return page_wrapper("Quick Reference", content, is_private=True)


def gen_ssh_commands(cfg):
    content = """
<h2>SSH Befehle</h2>

<section class="card card-private">
    <h3>CK+ Cloud Key (via Expect)</h3>
    <pre><code>expect -c '
  set timeout 30
  spawn ssh -o StrictHostKeyChecking=no root@10.10.10.10
  expect "Password:"
  send "usual_Brutal9Clutch\\r"
  interact
'</code></pre>
    <p><strong>Hinweis:</strong> Normaler <code>ssh root@10.10.10.10</code> funktioniert NICHT (keyboard-interactive only).</p>
</section>

<section class="card card-private">
    <h3>USG 3P</h3>
    <pre><code>ssh gBqfpbLXM@10.10.10.1
# Passwort: HxmO1kUnp2Z

# Firewall-Regeln anzeigen
sudo iptables -L LAN_IN -n -v --line-numbers

# Interfaces
show interfaces</code></pre>
</section>

<section class="card card-private">
    <h3>ESXi7</h3>
    <pre><code>ssh mpauli@192.168.178.174
# Passwort: usual_Brutal9Clutch

# VMs auflisten
vim-cmd vmsvc/getallvms

# VM Status
esxcli vm process list</code></pre>
</section>

<section class="card card-private">
    <h3>Switch-Konfiguration (API)</h3>
    <pre><code># Switch Config lesen
curl -s -m 10 --digest -u "admin:" "http://192.168.178.165/fwd.b"

# VLAN Config lesen
curl -s -m 10 --digest -u "admin:" "http://192.168.178.165/vlan.b"

# Konfiguration speichern
curl -s -m 5 --digest -u "admin:" "http://192.168.178.165/!dstore.b"</code></pre>
</section>

<section class="card card-private">
    <h3>NUC Netzwerk-Diagnose</h3>
    <pre><code># VLAN Interfaces pruefen
ip addr show eno1.11 eno1.12 eno1.13

# Routing-Tabelle
ip route show

# NetworkManager
nmcli con show
nmcli device status

# Services pruefen
systemctl status socat-unifi dnsmasq-tor iptables-tor tor@default

# iptables NAT
iptables -t nat -L PREROUTING -n -v</code></pre>
</section>
"""
    return page_wrapper("SSH Befehle", content, is_private=True)


def gen_mongodb_commands(cfg):
    content = """
<h2>MongoDB Befehle (CK+)</h2>
<p>Alle Befehle auf dem CK+ ausfuehren: <code>mongo --port 27117 ace --quiet</code></p>

<section class="card card-private">
    <h3>Verbindung herstellen</h3>
    <pre><code># Auf dem CK+ (nach SSH-Login):
mongo --port 27117 ace --quiet

# Vom NUC aus (Einzeiler via expect):
expect -c '
  set timeout 30
  spawn ssh -o StrictHostKeyChecking=no root@10.10.10.10
  expect "Password:"
  send "usual_Brutal9Clutch\\r"
  expect "#"
  send "mongo --port 27117 ace --quiet\\r"
  interact
'</code></pre>
</section>

<section class="card card-private">
    <h3>Geraete auflisten</h3>
    <pre><code>db.device.find({}).forEach(function(d){
  printjson({
    _id: String(d._id),
    name: d.name,
    model: d.model,
    ip: d.ip,
    type: d.type,
    state: d.state,
    adopted: d.adopted
  })
})</code></pre>
    <p><strong>Bekannte Device IDs:</strong></p>
    <table>
        <tr><th>Geraet</th><th>ObjectId</th><th>Modell</th></tr>
        <tr><td>USG 3P</td><td><code>697e05338f36df498fd342d3</code></td><td>UGW3</td></tr>
        <tr><td>U6+ AZ</td><td><code>697e05358f36df498fd342d7</code></td><td>UAPL6</td></tr>
        <tr><td>U6+ Keller</td><td><code>697e07848f36df498fd342f0</code></td><td>UAPL6</td></tr>
    </table>
</section>

<section class="card card-private">
    <h3>WLAN-Konfiguration</h3>
    <pre><code>db.wlanconf.find({}).forEach(function(w){
  printjson({
    _id: w._id,
    name: w.name,
    enabled: w.enabled,
    security: w.security,
    wpa_mode: w.wpa_mode,
    networkconf_id: w.networkconf_id,
    vlan: w.vlan,
    vlan_enabled: w.vlan_enabled,
    is_guest: w.is_guest
  })
})</code></pre>
    <p><strong>Bekannte WLAN IDs:</strong></p>
    <table>
        <tr><th>SSID</th><th>ObjectId</th><th>Network</th></tr>
        <tr><td>element-5a77c15c...</td><td><code>697dfa4494dc713125df3f38</code></td><td>Default</td></tr>
        <tr><td>Bad!Bad</td><td><code>697e1d2bb5b315f1ed6146f3</code></td><td>697e1d2bb5b315f1ed6146f2</td></tr>
        <tr><td>Bad!IoT</td><td><code>697e2ff31e5dba79a3a92abd</code></td><td>Default</td></tr>
    </table>
</section>

<section class="card card-private">
    <h3>Firewall-Regeln</h3>
    <pre><code># Alle Regeln anzeigen
db.firewallrule.find({}).forEach(function(r){
  printjson(r)
})

# Regel loeschen (Vorsicht!)
var r = db.firewallrule.findOne({rule_index: XXXX});
db.firewallrule.remove({_id: r._id});

# USG re-provisionieren (nach Aenderungen)
var d = db.device.findOne({ip: "192.168.178.250"});
db.device.update({_id: d._id}, {$set: {cfgversion: "force_" + Date.now()}});</code></pre>
</section>

<section class="card card-private">
    <h3>Netzwerk-Konfiguration</h3>
    <pre><code>db.networkconf.find({}).forEach(function(n){
  printjson({
    _id: n._id,
    name: n.name,
    purpose: n.purpose,
    vlan: n.vlan,
    subnet: n.ip_subnet,
    dhcp: n.dhcpd_enabled,
    enabled: n.enabled
  })
})</code></pre>
</section>

<section class="card card-private">
    <h3>Admin-Benutzer verwalten</h3>
    <pre><code># Alle Admins anzeigen
db.admin.find({}, {name:1, email:1, super_admin:1}).toArray()

# Admin loeschen
db.admin.remove({name: "icewifi-admin"})

# Passwort aendern (SHA-512 Hash generieren mit: openssl passwd -6 'NeuesPasswort')
db.admin.update(
  {name: "icewifi-admin"},
  {$set: {x_shadow: "NEUER_HASH"}}
)</code></pre>
</section>
"""
    return page_wrapper("MongoDB Befehle", content, is_private=True)


# =============================================================================
# Main Generator
# =============================================================================

def generate_public(cfg):
    """Generate public documentation (sanitized)."""
    print("[PUBLIC] Generating public documentation...")
    os.makedirs(PUBLIC_DIR / "css", exist_ok=True)
    os.makedirs(PUBLIC_DIR / "diagrams", exist_ok=True)

    pages = {
        "index.html": gen_index(cfg, is_private=False),
        "admin-guide.html": gen_admin_guide(cfg, is_private=False),
        "user-guide.html": gen_user_guide(cfg, is_private=False),
        "network-topology.html": gen_topology(cfg, is_private=False),
        "backup-restore.html": gen_backup_restore(cfg, is_private=False),
        "troubleshooting.html": gen_troubleshooting(cfg, is_private=False),
    }

    for filename, content in pages.items():
        sanitized = sanitize_public(content)
        # Verify no sensitive data leaked
        for pattern in SENSITIVE_PATTERNS:
            if pattern in sanitized:
                print(f"  WARNING: Sensitive pattern found in public {filename}: {pattern[:20]}...")
        filepath = PUBLIC_DIR / filename
        with open(filepath, "w") as f:
            f.write(sanitized)
        print(f"  [OK] {filepath}")

    print(f"[PUBLIC] Done - {len(pages)} pages generated")


def generate_private(cfg):
    """Generate private documentation (with all credentials)."""
    print("[PRIVATE] Generating private documentation...")
    os.makedirs(PRIVATE_DIR / "css", exist_ok=True)
    os.makedirs(PRIVATE_DIR / "diagrams", exist_ok=True)
    os.makedirs(PRIVATE_DIR / "screenshots", exist_ok=True)

    pages = {
        "index.html": gen_index(cfg, is_private=True),
        "admin-guide.html": gen_admin_guide(cfg, is_private=True),
        "user-guide.html": gen_user_guide(cfg, is_private=True),
        "network-topology.html": gen_topology(cfg, is_private=True),
        "backup-restore.html": gen_backup_restore(cfg, is_private=True),
        "troubleshooting.html": gen_troubleshooting(cfg, is_private=True),
        "quick-reference.html": gen_quick_reference(cfg),
        "ssh-commands.html": gen_ssh_commands(cfg),
        "mongodb-commands.html": gen_mongodb_commands(cfg),
    }

    for filename, content in pages.items():
        filepath = PRIVATE_DIR / filename
        with open(filepath, "w") as f:
            f.write(content)
        print(f"  [OK] {filepath}")

    # Copy CSS and diagrams
    if (PUBLIC_DIR / "css" / "style.css").exists():
        shutil.copy2(PUBLIC_DIR / "css" / "style.css", PRIVATE_DIR / "css" / "style.css")
        print("  [OK] CSS copied")

    for svg in (PUBLIC_DIR / "diagrams").glob("*.svg"):
        shutil.copy2(svg, PRIVATE_DIR / "diagrams" / svg.name)
        print(f"  [OK] Diagram copied: {svg.name}")

    print(f"[PRIVATE] Done - {len(pages)} pages generated")


def deploy(cfg):
    """Deploy documentation to GitHub and website."""
    ext = cfg["external"]

    print("\n[DEPLOY] Starting deployment...")

    # Git push
    print("[DEPLOY] Pushing to GitHub...")
    os.chdir(PUBLIC_DIR.parent)
    cmds = [
        "git add -A",
        'git commit -m "docs: update IceWiFi documentation" --allow-empty',
        "git push origin main",
    ]
    for cmd in cmds:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0 and "nothing to commit" not in result.stdout + result.stderr:
            print(f"  WARN: {cmd}: {result.stderr.strip()}")
        else:
            print(f"  [OK] {cmd}")

    # SCP to website
    print(f"[DEPLOY] Uploading to {ext['website']}...")
    scp_cmd = f"scp -r {PUBLIC_DIR}/* root@{ext['website_ip']}:/var/www/html{ext['website_path']}"
    result = subprocess.run(scp_cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"  [OK] Uploaded to {ext['website']}{ext['website_path']}")
    else:
        print(f"  WARN: SCP failed: {result.stderr.strip()}")

    print("[DEPLOY] Done")


def main():
    parser = argparse.ArgumentParser(description="IceWiFi Documentation Generator")
    parser.add_argument("--public", action="store_true", help="Generate only public docs")
    parser.add_argument("--private", action="store_true", help="Generate only private docs")
    parser.add_argument("--deploy", action="store_true", help="Also deploy after generating")
    parser.add_argument("--screenshots", action="store_true", help="Refresh screenshots first")
    args = parser.parse_args()

    print(f"=== IceWiFi Documentation Generator ===")
    print(f"Time: {timestamp()}")
    print(f"Config: {CONFIG_FILE}")
    print()

    cfg = load_config()

    if args.screenshots:
        print("[SCREENSHOTS] Refreshing screenshots...")
        result = subprocess.run(
            ["python3", "/root/scripts/icewifi-screenshots.py"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print("[SCREENSHOTS] Done")
        else:
            print(f"[SCREENSHOTS] Warning: {result.stderr.strip()}")
        print()

    if args.public or (not args.public and not args.private):
        generate_public(cfg)
        print()

    if args.private or (not args.public and not args.private):
        generate_private(cfg)
        print()

    if args.deploy:
        deploy(cfg)

    print(f"\n=== Generation Complete ===")


if __name__ == "__main__":
    main()
