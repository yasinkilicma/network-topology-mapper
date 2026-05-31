# Netzwerk-Topologie-Mapper

Automatische Erkennung und Visualisierung von Netzwerk-Topologien.
Das Tool fragt Netzwerkgeräte per SNMP ab, wertet LLDP- und CDP-Nachbarinformationen
aus und erstellt daraus eine übersichtliche Netzwerkkarte als PNG-Bild oder
interaktive HTML-Seite.

---

## Funktionsumfang

| Modul | Beschreibung |
|---|---|
| **SNMP-Entdeckung** | Geräte per SNMPv2c/v3 abfragen: Systemname, Beschreibung, Interfaces |
| **LLDP-Auswertung** | IEEE-802.1AB-Nachbarn erkennen (herstellerunabhängig) |
| **CDP-Auswertung** | Cisco Discovery Protocol – Nachbarn auf Cisco-Geräten |
| **Topologie-Aufbau** | NetworkX-Graph aus Geräten und Verbindungen aufbauen |
| **Visualisierung** | Ausgabe als PNG (matplotlib), interaktives HTML (D3.js) oder Text |
| **Demo-Modus** | Vollständige Vorschau ohne SNMP-fähige Hardware |

---

## Voraussetzungen

- Python 3.8 oder höher
- Netzwerkgeräte mit aktiviertem SNMP (Community: `public` oder angepasst)
- LLDP oder CDP auf den Geräten aktiviert

```bash
pip install -r requirements.txt
```

---

## Installation

```bash
git clone https://github.com/yasinkilicma/network-topology-mapper.git
cd network-topology-mapper
pip install -r requirements.txt
```

---

## Verwendung

```bash
# Topologie eines Subnetzes erkennen und als PNG speichern
python mapper.py --netzwerk 192.168.1.0/24

# Einzelnen Host abfragen
python mapper.py --netzwerk 192.168.1.1

# Benutzerdefinierte SNMP-Community
python mapper.py --netzwerk 10.0.0.0/24 --community mein-passwort

# Ausgabe als interaktive HTML-Karte
python mapper.py --netzwerk 192.168.1.0/24 --ausgabe html

# Demo-Modus (ohne echte SNMP-Geräte)
python mapper.py --demo
python mapper.py --demo --ausgabe html
```

### Alle Parameter

```
--netzwerk  / -n   IP-Adresse oder CIDR-Netzwerk    (z.B. 192.168.1.0/24)
--community / -c   SNMP-Community-String             (Standard: public)
--ausgabe   / -o   Ausgabeformat: png, html, text    (Standard: png)
--timeout          SNMP-Timeout in Sekunden          (Standard: 2.0)
--demo             Demo-Modus mit Beispieldaten
```

---

## Beispielausgabe

### Textausgabe

```
============================================================
  NETZWERK-TOPOLOGIE-MAPPER
  Netzwerk: 192.168.1.0/24
  Zeitstempel: 31.05.2026 15:10:22
============================================================

[1/3] Starte SNMP-Erkennung...
     -> 5 Geräte mit SNMP-Antwort gefunden.

[2/3] Baue Topologie-Graph auf...
     -> 5 Knoten, 6 Verbindungen erkannt.

[3/3] Erstelle Visualisierung (PNG)...
     -> Gespeichert: output/topologie_20260531_151022.png

--- ERKANNTE GERÄTE ---
  Core-Router-01    192.168.1.1    Router   Cisco IOS 15.2
  Core-Switch-01    192.168.1.10   Switch   Cisco Catalyst 3750
  Core-Switch-02    192.168.1.11   Switch   Cisco Catalyst 3750
  Server-01         192.168.1.20   Server   Linux 5.15
  Server-02         192.168.1.21   Server   Linux 5.15

--- ERKANNTE VERBINDUNGEN ---
  Core-Router-01  Gi0/0 <-> Gi1/1  Core-Switch-01
  Core-Router-01  Gi0/1 <-> Gi1/1  Core-Switch-02
  Core-Switch-01  Gi1/2 <-> eth0   Server-01
  Core-Switch-02  Gi1/2 <-> eth0   Server-02
```

---

## SNMP-Voraussetzungen

### Cisco IOS
```
snmp-server community public RO
lldp run
```

### Linux (net-snmp)
```bash
apt install snmpd lldpd
# /etc/snmp/snmpd.conf: rocommunity public
systemctl restart snmpd lldpd
```

### Netzwerk-Switch allgemein
```
snmp-server enable
snmp-server community public read-only
lldp enable
```

---

## Projektstruktur

```
network-topology-mapper/
├── mapper.py                    # Hauptskript / Einstiegspunkt
├── requirements.txt
├── config/
│   └── config.example.yaml      # Beispielkonfiguration
├── demo/
│   └── beispiel_netzwerk.yaml   # Demo-Topologiedaten
├── modules/
│   ├── snmp_entdeckung.py       # SNMP/LLDP/CDP-Abfragen
│   ├── topologie_aufbau.py      # NetworkX-Graph aufbauen
│   └── visualisierung.py        # PNG, HTML, Text ausgeben
└── output/                      # Generierte Karten
```

---

## Zertifizierungsbezug

- **CompTIA Network+** – Netzwerk-Protokolle (SNMP, LLDP, CDP), Topologie-Typen
- **CompTIA Security+** – Netzwerk-Inventarisierung als Grundlage für Sicherheitsanalysen
- **CompTIA CySA+** – Asset-Discovery und Angriffsoberflächen-Kartierung
