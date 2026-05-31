"""
snmp_entdeckung.py – SNMP-basierte Netzwerkgeräteerkennung
===========================================================
Dieses Modul fragt Netzwerkgeräte über SNMP ab und sammelt:
  - Systeminformationen (Name, Beschreibung, Standort)
  - LLDP-Nachbarn (IEEE 802.1AB – herstellerunabhängig)
  - CDP-Nachbarn  (Cisco Discovery Protocol – Cisco-spezifisch)

SNMP-Grundlagen:
  SNMP (Simple Network Management Protocol) ist ein Standardprotokoll
  zur Überwachung und Verwaltung von Netzwerkgeräten. Es nutzt eine
  baumartige Datenstruktur (MIB – Management Information Base), in der
  jeder Datenpunkt durch einen OID (Object Identifier) adressiert wird.

  Beispiel: 1.3.6.1.2.1.1.5.0 = sysName (Gerätename)
            1.3.6.1.2.1.1.1.0 = sysDescr (Beschreibung)

LLDP vs. CDP:
  LLDP (Link Layer Discovery Protocol) ist ein offener IEEE-Standard.
  CDP ist ein proprietäres Cisco-Protokoll, das auf Cisco-Geräten
  standardmäßig aktiv ist. Beide Protokolle verbreiten Informationen
  über direkt verbundene Nachbarn auf Layer-2-Ebene.

Verwendete OIDs:
  System:
    sysDescr    1.3.6.1.2.1.1.1.0
    sysName     1.3.6.1.2.1.1.5.0
    sysLocation 1.3.6.1.2.1.1.6.0
    sysContact  1.3.6.1.2.1.1.4.0

  LLDP (IEEE 802.1AB MIB):
    lldpRemSysName  1.0.8802.1.1.2.1.4.1.1.9
    lldpRemPortId   1.0.8802.1.1.2.1.4.1.1.7
    lldpRemSysDesc  1.0.8802.1.1.2.1.4.1.1.10

  CDP (Cisco MIB):
    cdpCacheDeviceId   1.3.6.1.4.1.9.9.23.1.2.1.1.6
    cdpCacheDevicePort 1.3.6.1.4.1.9.9.23.1.2.1.1.7
    cdpCachePlatform   1.3.6.1.4.1.9.9.23.1.2.1.1.8
"""

import ipaddress
import socket
from typing import List, Dict, Any, Optional

try:
    from pysnmp.hlapi import (
        getCmd, nextCmd, SnmpEngine,
        CommunityData, UdpTransportTarget,
        ContextData, ObjectType, ObjectIdentity
    )
    SNMP_VERFUEGBAR = True
except ImportError:
    # pysnmp nicht installiert – nur Demo-Modus möglich
    SNMP_VERFUEGBAR = False

try:
    import yaml
    YAML_VERFUEGBAR = True
except ImportError:
    YAML_VERFUEGBAR = False

import os

# OID-Konstanten für bessere Lesbarkeit
OID_SYS_DESCR    = "1.3.6.1.2.1.1.1.0"
OID_SYS_NAME     = "1.3.6.1.2.1.1.5.0"
OID_SYS_LOCATION = "1.3.6.1.2.1.1.6.0"
OID_SYS_CONTACT  = "1.3.6.1.2.1.1.4.0"

OID_LLDP_REM_SYS_NAME = "1.0.8802.1.1.2.1.4.1.1.9"
OID_LLDP_REM_PORT_ID  = "1.0.8802.1.1.2.1.4.1.1.7"
OID_LLDP_REM_SYS_DESC = "1.0.8802.1.1.2.1.4.1.1.10"

OID_CDP_DEVICE_ID   = "1.3.6.1.4.1.9.9.23.1.2.1.1.6"
OID_CDP_DEVICE_PORT = "1.3.6.1.4.1.9.9.23.1.2.1.1.7"
OID_CDP_PLATFORM    = "1.3.6.1.4.1.9.9.23.1.2.1.1.8"

# Pfad zu den Demo-Daten
DEMO_DATEI = os.path.join(os.path.dirname(__file__), "..", "demo", "beispiel_netzwerk.yaml")


def demo_geraete_laden() -> List[Dict[str, Any]]:
    """
    Lädt vorgefertigte Beispiel-Gerätedaten aus der YAML-Datei.

    Diese Funktion wird im Demo-Modus verwendet, wenn keine echten
    SNMP-fähigen Geräte im Netzwerk vorhanden sind.
    """
    if YAML_VERFUEGBAR:
        try:
            with open(DEMO_DATEI, "r", encoding="utf-8") as f:
                daten = yaml.safe_load(f)
                return daten.get("geraete", [])
        except FileNotFoundError:
            pass

    # Eingebettete Fallback-Daten falls YAML-Datei fehlt
    return [
        {
            "host": "192.168.1.1", "sys_name": "Core-Router-01",
            "sys_descr": "Cisco IOS Software, Version 15.2(4)M",
            "sys_location": "Serverraum EG",
            "nachbarn": [
                {"sys_name": "Core-Switch-01", "port_lokal": "GigabitEthernet0/0", "port_remote": "GigabitEthernet1/0/1", "protokoll": "CDP"},
                {"sys_name": "Core-Switch-02", "port_lokal": "GigabitEthernet0/1", "port_remote": "GigabitEthernet1/0/1", "protokoll": "CDP"},
            ]
        },
        {
            "host": "192.168.1.10", "sys_name": "Core-Switch-01",
            "sys_descr": "Cisco Catalyst 3750 Series",
            "sys_location": "Serverraum EG Rack A",
            "nachbarn": [
                {"sys_name": "Core-Router-01",   "port_lokal": "GigabitEthernet1/0/1", "port_remote": "GigabitEthernet0/0",   "protokoll": "CDP"},
                {"sys_name": "Access-Switch-01", "port_lokal": "GigabitEthernet1/0/2", "port_remote": "GigabitEthernet0/1",   "protokoll": "LLDP"},
                {"sys_name": "Server-01",        "port_lokal": "GigabitEthernet1/0/3", "port_remote": "eth0",                 "protokoll": "LLDP"},
            ]
        },
        {
            "host": "192.168.1.11", "sys_name": "Core-Switch-02",
            "sys_descr": "Cisco Catalyst 3750 Series",
            "sys_location": "Serverraum EG Rack B",
            "nachbarn": [
                {"sys_name": "Core-Router-01",   "port_lokal": "GigabitEthernet1/0/1", "port_remote": "GigabitEthernet0/1",  "protokoll": "CDP"},
                {"sys_name": "Access-Switch-02", "port_lokal": "GigabitEthernet1/0/2", "port_remote": "GigabitEthernet0/1", "protokoll": "LLDP"},
                {"sys_name": "Server-02",        "port_lokal": "GigabitEthernet1/0/3", "port_remote": "eth0",                "protokoll": "LLDP"},
            ]
        },
        {
            "host": "192.168.1.20", "sys_name": "Access-Switch-01",
            "sys_descr": "HP ProCurve Switch 2510G",
            "sys_location": "Büro OG",
            "nachbarn": [
                {"sys_name": "Core-Switch-01", "port_lokal": "GigabitEthernet0/1",  "port_remote": "GigabitEthernet1/0/2", "protokoll": "LLDP"},
                {"sys_name": "Workstation-01", "port_lokal": "FastEthernet0/1",     "port_remote": "eth0",                 "protokoll": "LLDP"},
                {"sys_name": "Workstation-02", "port_lokal": "FastEthernet0/2",     "port_remote": "eth0",                 "protokoll": "LLDP"},
            ]
        },
        {
            "host": "192.168.1.21", "sys_name": "Access-Switch-02",
            "sys_descr": "HP ProCurve Switch 2510G",
            "sys_location": "Büro UG",
            "nachbarn": [
                {"sys_name": "Core-Switch-02", "port_lokal": "GigabitEthernet0/1", "port_remote": "GigabitEthernet1/0/2", "protokoll": "LLDP"},
                {"sys_name": "Workstation-03", "port_lokal": "FastEthernet0/1",    "port_remote": "eth0",                "protokoll": "LLDP"},
            ]
        },
        {"host": "192.168.1.30", "sys_name": "Server-01",      "sys_descr": "Linux Ubuntu 22.04 LTS", "sys_location": "Serverraum EG", "nachbarn": []},
        {"host": "192.168.1.31", "sys_name": "Server-02",      "sys_descr": "Linux Debian 11",        "sys_location": "Serverraum EG", "nachbarn": []},
        {"host": "192.168.1.40", "sys_name": "Workstation-01", "sys_descr": "Windows 11 Pro",         "sys_location": "Büro OG",       "nachbarn": []},
        {"host": "192.168.1.41", "sys_name": "Workstation-02", "sys_descr": "Windows 11 Pro",         "sys_location": "Büro OG",       "nachbarn": []},
        {"host": "192.168.1.42", "sys_name": "Workstation-03", "sys_descr": "Windows 10 Pro",         "sys_location": "Büro UG",       "nachbarn": []},
    ]


class SNMPEntdecker:
    """
    Erkennt Netzwerkgeräte per SNMP und sammelt Topologieinformationen.

    Für jeden erreichbaren Host werden abgefragt:
      - Systemname und -beschreibung (Standard-MIB)
      - Direkte Nachbarn via LLDP (IEEE 802.1AB)
      - Direkte Nachbarn via CDP  (Cisco-proprietär)

    Parameter:
        community (str): SNMP-Community-String (Read-Only genügt)
        timeout (float): Timeout pro SNMP-Anfrage in Sekunden
    """

    def __init__(self, community: str = "public", timeout: float = 2.0):
        if not SNMP_VERFUEGBAR:
            raise RuntimeError(
                "pysnmp ist nicht installiert. "
                "Bitte 'pip install pysnmp' ausführen oder --demo verwenden."
            )
        self.community = community
        self.timeout = timeout

    def netzwerk_scannen(self, netzwerk_cidr: str) -> List[Dict[str, Any]]:
        """
        Scannt alle Hosts eines Netzwerks auf SNMP-Erreichbarkeit.

        Ablauf:
          1. CIDR-Netzwerk in einzelne Host-IPs aufteilen
          2. Jeden Host mit einem schnellen TCP-Check auf Port 161 prüfen
          3. Antwortende Hosts per SNMP vollständig abfragen

        Parameter:
            netzwerk_cidr: IP oder CIDR (z.B. "192.168.1.0/24" oder "10.0.0.1")

        Rückgabe:
            Liste von Geräte-Dictionaries mit allen gesammelten Daten.
        """
        hosts = self._hosts_ermitteln(netzwerk_cidr)
        print(f"     Scanne {len(hosts)} Host(s) auf SNMP-Erreichbarkeit...")

        erreichbare_hosts = [h for h in hosts if self._snmp_erreichbar(h)]
        print(f"     -> {len(erreichbare_hosts)} Host(s) antworten auf SNMP.")

        geraete = []
        for host in erreichbare_hosts:
            geraet = self.host_abfragen(host)
            if geraet:
                geraete.append(geraet)

        return geraete

    def host_abfragen(self, host: str) -> Optional[Dict[str, Any]]:
        """
        Vollständige SNMP-Abfrage eines einzelnen Hosts.

        Fragt nacheinander ab:
          1. Systeminformationen (sysName, sysDescr, sysLocation)
          2. LLDP-Nachbartabelle
          3. CDP-Nachbartabelle (nur Cisco)

        Rückgabe:
            Geräte-Dictionary oder None bei Fehler.
        """
        sys_info = self._system_info_holen(host)
        if not sys_info:
            return None

        nachbarn = []
        nachbarn.extend(self._lldp_nachbarn_holen(host))
        nachbarn.extend(self._cdp_nachbarn_holen(host))

        return {
            "host":         host,
            "sys_name":     sys_info.get("sys_name", host),
            "sys_descr":    sys_info.get("sys_descr", ""),
            "sys_location": sys_info.get("sys_location", ""),
            "nachbarn":     nachbarn,
        }

    def _system_info_holen(self, host: str) -> Optional[Dict[str, str]]:
        """
        Liest grundlegende Systeminformationen per SNMP-GET.

        Diese Werte stammen aus der Standard-MIB-2 (RFC 1213) und
        werden von praktisch allen SNMP-fähigen Geräten unterstützt.
        """
        oids = {
            "sys_descr":    OID_SYS_DESCR,
            "sys_name":     OID_SYS_NAME,
            "sys_location": OID_SYS_LOCATION,
        }
        ergebnis = {}

        for schluessel, oid in oids.items():
            wert = self._snmp_get(host, oid)
            if wert:
                ergebnis[schluessel] = wert

        return ergebnis if ergebnis else None

    def _lldp_nachbarn_holen(self, host: str) -> List[Dict[str, str]]:
        """
        Liest LLDP-Nachbartabelle via SNMP-WALK (IEEE 802.1AB MIB).

        LLDP speichert Nachbarinformationen in einer Tabelle, die über
        den SNMP-WALK-Befehl ausgelesen wird. Der OID-Index kodiert dabei
        die lokale Port-Nummer und eine Nachbar-ID.

        Typische Rückgabestruktur:
          1.0.8802.1.1.2.1.4.1.1.9.0.1.1 = "Switch-Name"
                                ^^^^^^^^^^
                                Port-Index.Nachbar-Index
        """
        sys_namen = self._snmp_walk(host, OID_LLDP_REM_SYS_NAME)
        port_ids  = self._snmp_walk(host, OID_LLDP_REM_PORT_ID)

        nachbarn = []
        for oid_key, sys_name in sys_namen.items():
            if not sys_name or sys_name == "":
                continue
            # Port-ID aus dem korrespondierenden OID holen
            port_id = port_ids.get(oid_key.replace(
                OID_LLDP_REM_SYS_NAME, OID_LLDP_REM_PORT_ID
            ), "")
            nachbarn.append({
                "sys_name":    sys_name,
                "port_lokal":  "",   # Lokaler Port aus Port-Index extrahierbar
                "port_remote": port_id,
                "protokoll":   "LLDP",
            })

        return nachbarn

    def _cdp_nachbarn_holen(self, host: str) -> List[Dict[str, str]]:
        """
        Liest CDP-Nachbartabelle via SNMP-WALK (Cisco CISCO-CDP-MIB).

        CDP ist ein Cisco-proprietäres Protokoll und nur auf Cisco-Geräten
        verfügbar. Es liefert Gerätename, Port und Plattformtyp des Nachbarn.
        """
        geraete_ids = self._snmp_walk(host, OID_CDP_DEVICE_ID)
        geraete_ports = self._snmp_walk(host, OID_CDP_DEVICE_PORT)

        nachbarn = []
        for oid_key, geraet_id in geraete_ids.items():
            if not geraet_id:
                continue
            port = geraete_ports.get(
                oid_key.replace(OID_CDP_DEVICE_ID, OID_CDP_DEVICE_PORT), ""
            )
            nachbarn.append({
                "sys_name":    geraet_id,
                "port_lokal":  "",
                "port_remote": port,
                "protokoll":   "CDP",
            })

        return nachbarn

    def _snmp_get(self, host: str, oid: str) -> Optional[str]:
        """Einzelne SNMP-GET-Anfrage für einen bestimmten OID."""
        iterator = getCmd(
            SnmpEngine(),
            CommunityData(self.community, mpModel=1),  # mpModel=1 = SNMPv2c
            UdpTransportTarget((host, 161), timeout=self.timeout, retries=0),
            ContextData(),
            ObjectType(ObjectIdentity(oid))
        )
        errorIndication, errorStatus, _, varBinds = next(iterator)
        if errorIndication or errorStatus:
            return None
        for varBind in varBinds:
            return str(varBind[1])
        return None

    def _snmp_walk(self, host: str, oid: str) -> Dict[str, str]:
        """
        SNMP-WALK: Alle Einträge unterhalb eines OID-Zweigs abrufen.

        nextCmd() iteriert durch alle Sub-OIDs bis der Baum endet
        (lexicographicMode=False stoppt am Ende des Teilbaums).
        """
        ergebnisse = {}
        for errorIndication, errorStatus, _, varBinds in nextCmd(
            SnmpEngine(),
            CommunityData(self.community, mpModel=1),
            UdpTransportTarget((host, 161), timeout=self.timeout, retries=0),
            ContextData(),
            ObjectType(ObjectIdentity(oid)),
            lexicographicMode=False
        ):
            if errorIndication or errorStatus:
                break
            for varBind in varBinds:
                ergebnisse[str(varBind[0])] = str(varBind[1])
        return ergebnisse

    def _snmp_erreichbar(self, host: str) -> bool:
        """
        Schneller Vorcheck: Antwortet der Host überhaupt auf UDP-Port 161?

        Statt direkt SNMP zu senden, wird ein UDP-Socket geöffnet.
        Geräte ohne SNMP verwerfen das Paket, die Verbindung schreibt
        keinen Fehler – daher kurzer Timeout mit Dummy-Abfrage.
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(0.5)
            # Minimales SNMP-GET-Paket für sysDescr senden
            sock.sendto(b"\x30\x26\x02\x01\x01", (host, 161))
            sock.recvfrom(1024)
            sock.close()
            return True
        except Exception:
            return False

    def _hosts_ermitteln(self, netzwerk_cidr: str) -> List[str]:
        """CIDR-Netzwerk in eine Liste einzelner Host-IPs umwandeln."""
        try:
            netz = ipaddress.ip_network(netzwerk_cidr, strict=False)
            hosts = [str(ip) for ip in netz.hosts()]
            return hosts if hosts else [str(netz.network_address)]
        except ValueError:
            return [netzwerk_cidr]
