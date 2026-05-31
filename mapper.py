#!/usr/bin/env python3
"""
mapper.py – Netzwerk-Topologie-Mapper Hauptskript
==================================================
Dieses Skript erkennt automatisch die Topologie eines Netzwerks.
Der Ablauf:

  1. SNMP-Erkennung:
     Jeder Host im angegebenen Netzwerk wird per SNMP abgefragt.
     Geräte, die antworten, liefern Systemname, Beschreibung und
     ihre direkten Nachbarn via LLDP oder CDP.

  2. Topologie-Aufbau:
     Aus den gesammelten Geräte- und Verbindungsdaten wird ein
     gewichteter NetworkX-Graph erstellt. Gerätetypen (Router,
     Switch, Server, Host) werden automatisch erkannt.

  3. Visualisierung:
     Der Graph wird als PNG-Bild (matplotlib), interaktive
     HTML-Seite (D3.js) oder Textausgabe dargestellt.

Demo-Modus:
  Mit --demo werden vorgefertigte Beispieldaten verwendet.
  So kann die Visualisierung ohne SNMP-fähige Hardware getestet werden.

Aufruf:
    python mapper.py --netzwerk 192.168.1.0/24
    python mapper.py --netzwerk 10.0.0.1 --community private --ausgabe html
    python mapper.py --demo
"""

import argparse
import sys
from datetime import datetime

from modules.snmp_entdeckung import SNMPEntdecker, demo_geraete_laden
from modules.topologie_aufbau import TopologieAufbauer
from modules.visualisierung import Visualisierer


def parse_argumente() -> argparse.Namespace:
    """
    Liest und validiert die Kommandozeilenargumente.

    Im Demo-Modus (--demo) ist --netzwerk optional, da die
    Beispieldaten aus der YAML-Datei geladen werden.
    """
    parser = argparse.ArgumentParser(
        description="Netzwerk-Topologie-Mapper – SNMP/LLDP/CDP-basierte Topologieerkennung",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  %(prog)s --netzwerk 192.168.1.0/24
  %(prog)s --netzwerk 10.0.0.1 --community geheim --ausgabe html
  %(prog)s --demo
  %(prog)s --demo --ausgabe html
        """
    )

    parser.add_argument(
        "--netzwerk", "-n",
        help="Ziel-IP-Adresse oder CIDR-Netzwerk (z.B. 192.168.1.0/24)"
    )
    parser.add_argument(
        "--community", "-c",
        default="public",
        help="SNMP-Community-String (Standard: public)"
    )
    parser.add_argument(
        "--ausgabe", "-o",
        choices=["png", "html", "text"],
        default="png",
        help="Ausgabeformat der Topologiekarte (Standard: png)"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=2.0,
        help="SNMP-Timeout in Sekunden pro Gerät (Standard: 2.0)"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Demo-Modus: Beispieltopologie ohne echte SNMP-Geräte"
    )

    args = parser.parse_args()

    # Im normalen Modus ist --netzwerk Pflichtfeld
    if not args.demo and not args.netzwerk:
        parser.error("--netzwerk ist erforderlich (oder --demo für Testmodus verwenden)")

    return args


def hauptprogramm() -> None:
    """
    Koordiniert den Topologie-Erkennungsprozess in drei Phasen:

      Phase 1 – SNMP-Erkennung:
        Alle Hosts im angegebenen Netzwerk werden per SNMP abgefragt.
        Für jedes antwortende Gerät werden Systemname, Beschreibung
        sowie LLDP/CDP-Nachbarn gesammelt.

      Phase 2 – Topologie-Aufbau:
        Die gesammelten Rohdaten werden in einen NetworkX-Graph
        umgewandelt. Jeder Knoten repräsentiert ein Gerät, jede
        Kante eine physische oder logische Verbindung.

      Phase 3 – Visualisierung:
        Der Graph wird im gewählten Format ausgegeben.
    """
    args = parse_argumente()
    ziel = args.netzwerk if args.netzwerk else "Demo-Netzwerk"

    print(f"\n{'='*60}")
    print(f"  NETZWERK-TOPOLOGIE-MAPPER")
    print(f"  Netzwerk:    {ziel}")
    print(f"  Modus:       {'Demo' if args.demo else 'SNMP-Live'}")
    print(f"  Zeitstempel: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print(f"{'='*60}\n")

    # --- Phase 1: Geräte erkennen ---
    print("[1/3] Starte Geräteerkennung...")

    if args.demo:
        # Demo-Geräte aus YAML-Datei laden – kein SNMP erforderlich
        geraete = demo_geraete_laden()
        print(f"     -> {len(geraete)} Demo-Geräte geladen.")
    else:
        entdecker = SNMPEntdecker(community=args.community, timeout=args.timeout)
        geraete = entdecker.netzwerk_scannen(args.netzwerk)
        print(f"     -> {len(geraete)} Geräte mit SNMP-Antwort gefunden.")

    if not geraete:
        print("  Keine Geräte erkannt. Prüfen Sie SNMP-Community und Netzwerk-Erreichbarkeit.")
        sys.exit(1)

    # --- Phase 2: Topologie-Graph aufbauen ---
    print("[2/3] Baue Topologie-Graph auf...")
    aufbauer = TopologieAufbauer()
    graph = aufbauer.aufbauen(geraete)
    print(f"     -> {graph.number_of_nodes()} Knoten, {graph.number_of_edges()} Verbindungen.")

    # --- Phase 3: Visualisieren ---
    print(f"[3/3] Erstelle Visualisierung ({args.ausgabe.upper()})...")
    visualisierer = Visualisierer()
    visualisierer.erstellen(graph, geraete, format=args.ausgabe)


if __name__ == "__main__":
    hauptprogramm()
