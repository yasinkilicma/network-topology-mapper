"""
topologie_aufbau.py – Netzwerk-Topologie-Graph aufbauen
========================================================
Dieses Modul wandelt die rohen Gerätedaten aus der SNMP-Erkennung
in einen strukturierten NetworkX-Graphen um.

NetworkX-Grundlagen:
  NetworkX ist eine Python-Bibliothek zur Analyse von Graphen und Netzwerken.
  Ein Graph besteht aus Knoten (Nodes) und Kanten (Edges):
    - Knoten = Netzwerkgeräte (Router, Switch, Server, Workstation)
    - Kanten = physische Verbindungen zwischen Geräten (aus LLDP/CDP)

  Jeder Knoten und jede Kante kann mit beliebigen Attributen versehen
  werden (z.B. typ, sys_descr, port_info, protokoll).

Gerätetyp-Erkennung:
  Der Gerätetyp wird anhand des sysDescr-Felds automatisch bestimmt.
  Enthält die Beschreibung Schlüsselwörter wie 'cisco catalyst' oder
  'procurve', wird der Typ als 'switch' klassifiziert.

  Erkannte Typen:
    router     – Cisco IOS Router, Juniper, pfSense, VyOS
    switch     – Cisco Catalyst, HP ProCurve, Aruba, Juniper EX
    server     – Linux, Windows Server, ESXi
    workstation– Windows Desktop, macOS
    firewall   – Fortinet, Palo Alto, ASA
    unknown    – Nicht eindeutig klassifizierbar
"""

from typing import List, Dict, Any

try:
    import networkx as nx
    NETWORKX_VERFUEGBAR = True
except ImportError:
    NETWORKX_VERFUEGBAR = False


# Schlüsselwörter zur Gerätetyp-Erkennung anhand von sysDescr
TYP_ERKENNUNG: Dict[str, List[str]] = {
    "router": [
        "cisco ios", "ios software", "juniper junos", "mikrotik routeros",
        "pfsense", "vyos", "openwrt", "router",
    ],
    "switch": [
        "catalyst", "procurve", "powerconnect", "aruba", "juniper ex",
        "netgear", "dell emc powerswitch", "switch", "nexus",
    ],
    "firewall": [
        "fortinet", "fortigate", "palo alto", "asa", "checkpoint",
        "sophos", "watchguard", "firewall",
    ],
    "server": [
        "linux", "ubuntu", "debian", "centos", "rhel", "windows server",
        "esxi", "vmware", "proxmox", "freebsd",
    ],
    "workstation": [
        "windows 10", "windows 11", "macos", "darwin",
    ],
}

# Farbzuordnung für Gerätetypen (verwendet in der Visualisierung)
TYP_FARBEN: Dict[str, str] = {
    "router":      "#e74c3c",   # Rot
    "switch":      "#2ecc71",   # Grün
    "firewall":    "#e67e22",   # Orange
    "server":      "#3498db",   # Blau
    "workstation": "#95a5a6",   # Grau
    "unknown":     "#bdc3c7",   # Hellgrau
}

# Icon-Symbole für die HTML-Visualisierung
TYP_SYMBOLE: Dict[str, str] = {
    "router":      "▲",
    "switch":      "■",
    "firewall":    "⛔",
    "server":      "♥",
    "workstation": "●",
    "unknown":     "?",
}


class TopologieAufbauer:
    """
    Baut einen NetworkX-Graphen aus den erkannten Gerätedaten auf.

    Der Graph ist ungerichtet (undirected), da physische Verbindungen
    zwischen zwei Geräten keine Richtung haben. Doppelte Kanten
    (wenn beide Seiten den jeweils anderen als Nachbar melden) werden
    automatisch zusammengeführt.
    """

    def aufbauen(self, geraete: List[Dict[str, Any]]):
        """
        Erstellt den Topologie-Graphen aus der Geräteliste.

        Jedes Gerät wird als Knoten angelegt. Nachbareinträge aus LLDP/CDP
        werden als Kanten hinzugefügt. Sind Geräte aus Nachbarlisten
        noch nicht als Knoten vorhanden, werden sie automatisch als
        Knoten mit Typ 'unknown' ergänzt.

        Parameter:
            geraete: Liste von Geräte-Dicts aus SNMPEntdecker

        Rückgabe:
            networkx.Graph mit annotierten Knoten und Kanten.
        """
        if not NETWORKX_VERFUEGBAR:
            raise RuntimeError("networkx ist nicht installiert: pip install networkx")

        graph = nx.Graph()

        # Schritt 1: Alle Geräte als Knoten hinzufügen
        for geraet in geraete:
            name = geraet["sys_name"]
            typ  = self._geraet_typ_erkennen(geraet.get("sys_descr", ""))
            graph.add_node(name, **{
                "host":         geraet.get("host", ""),
                "sys_descr":    geraet.get("sys_descr", ""),
                "sys_location": geraet.get("sys_location", ""),
                "typ":          typ,
                "farbe":        TYP_FARBEN.get(typ, TYP_FARBEN["unknown"]),
                "symbol":       TYP_SYMBOLE.get(typ, "?"),
            })

        # Schritt 2: Verbindungen als Kanten einfügen
        for geraet in geraete:
            quelle = geraet["sys_name"]
            for nachbar in geraet.get("nachbarn", []):
                ziel = nachbar["sys_name"]

                # Unbekannte Nachbarn als Knoten ergänzen
                if ziel not in graph:
                    graph.add_node(ziel, **{
                        "host": "", "sys_descr": "", "sys_location": "",
                        "typ": "unknown",
                        "farbe": TYP_FARBEN["unknown"],
                        "symbol": TYP_SYMBOLE["unknown"],
                    })

                # Kante hinzufügen (Duplikate werden automatisch überschrieben)
                graph.add_edge(quelle, ziel, **{
                    "port_lokal":  nachbar.get("port_lokal", ""),
                    "port_remote": nachbar.get("port_remote", ""),
                    "protokoll":   nachbar.get("protokoll", ""),
                    "label":       f"{nachbar.get('port_lokal', '')} ↔ {nachbar.get('port_remote', '')}",
                })

        return graph

    def _geraet_typ_erkennen(self, sys_descr: str) -> str:
        """
        Bestimmt den Gerätetyp anhand der SNMP-sysDescr-Beschreibung.

        Die Prüfung erfolgt in der Reihenfolge: router → switch →
        firewall → server → workstation. Der erste Treffer gewinnt.
        Kein Treffer → 'unknown'.
        """
        sys_descr_lower = sys_descr.lower()

        for typ, schluesselbegriffe in TYP_ERKENNUNG.items():
            for begriff in schluesselbegriffe:
                if begriff in sys_descr_lower:
                    return typ

        return "unknown"
