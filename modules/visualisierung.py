"""
visualisierung.py – Topologie-Visualisierung
============================================
Dieses Modul erstellt aus dem NetworkX-Graphen eine visuelle Darstellung
der Netzwerktopologie in drei Ausgabeformaten:

  PNG  – Statisches Bild mit matplotlib und NetworkX Spring-Layout.
          Gerätetypen werden durch Farben und Knotenformen unterschieden.
          Verbindungslabels zeigen die Port-Informationen an.

  HTML – Interaktive Karte mit D3.js Force-Directed-Graph.
          Knoten können per Drag-and-Drop verschoben werden.
          Tooltip beim Überfahren zeigt IP, Typ und Standort.

  Text – ASCII-Darstellung im Terminal – tabellarisch mit Geräten
          und Verbindungen. Kein zusätzliches Paket erforderlich.

Spring-Layout (PNG):
  Das Spring-Layout (Fruchterman-Reingold-Algorithmus) simuliert
  physikalische Kräfte zwischen Knoten: Verbundene Knoten werden
  angezogen, alle anderen abgestoßen. Das Ergebnis ist eine
  ästhetisch ausgewogene, übersichtliche Graphdarstellung.

D3.js Force-Directed-Graph (HTML):
  D3 simuliert ebenfalls physikalische Kräfte im Browser. Die Simulation
  läuft interaktiv: Knoten lassen sich verschieben, Zoom und Pan sind
  möglich. Die Gerätedaten werden als JSON direkt in die HTML-Datei
  eingebettet – keine externe Server-Verbindung nach D3-CDN nötig
  für die Daten, nur für die D3-Bibliothek selbst.
"""

import os
import json
from datetime import datetime
from typing import Any, List, Dict

try:
    import networkx as nx
    import matplotlib
    matplotlib.use("Agg")   # Kein Display erforderlich (headless)
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    MATPLOTLIB_VERFUEGBAR = True
except ImportError:
    MATPLOTLIB_VERFUEGBAR = False

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
    FARBEN_VERFUEGBAR = True
except ImportError:
    FARBEN_VERFUEGBAR = False

AUSGABE_VERZEICHNIS = "output"


class Visualisierer:
    """Erstellt Topologiekarten in verschiedenen Ausgabeformaten."""

    def erstellen(self, graph: Any, geraete: List[Dict], format: str = "png") -> None:
        """
        Dispatcher – leitet an das passende Format weiter.

        Parameter:
            graph:   NetworkX-Graph mit annotierten Knoten/Kanten
            geraete: Originale Geräteliste (für Textausgabe)
            format:  'png', 'html' oder 'text'
        """
        os.makedirs(AUSGABE_VERZEICHNIS, exist_ok=True)
        zeitstempel = datetime.now().strftime("%Y%m%d_%H%M%S")

        if format == "png":
            self._png_erstellen(graph, zeitstempel)
        elif format == "html":
            self._html_erstellen(graph, zeitstempel)
        else:
            self._text_ausgabe(graph, geraete)

    # ------------------------------------------------------------------
    # PNG-Ausgabe (matplotlib + NetworkX)
    # ------------------------------------------------------------------

    def _png_erstellen(self, graph: Any, zeitstempel: str) -> None:
        """
        Erstellt ein PNG-Bild der Netzwerktopologie.

        Layoutalgorithmus: spring_layout (Fruchterman-Reingold)
        Knotenfarben und -formen entsprechen dem Gerätetyp.
        Kanten werden mit Port-Informationen beschriftet.
        """
        if not MATPLOTLIB_VERFUEGBAR:
            print("  matplotlib/networkx nicht installiert. Textausgabe stattdessen:")
            self._text_ausgabe(graph, [])
            return

        fig, ax = plt.subplots(figsize=(16, 10))
        ax.set_facecolor("#1a1a2e")
        fig.patch.set_facecolor("#1a1a2e")

        # Layout berechnen – seed für reproduzierbare Positionen
        positionen = nx.spring_layout(graph, k=2.5, seed=42)

        # Knoten nach Typ gruppieren für unterschiedliche Darstellung
        knotenfarben = [
            graph.nodes[n].get("farbe", "#bdc3c7")
            for n in graph.nodes()
        ]
        knotengroessen = [
            800 if graph.nodes[n].get("typ") in ("router", "firewall", "switch") else 500
            for n in graph.nodes()
        ]

        # Kanten zeichnen
        nx.draw_networkx_edges(
            graph, positionen, ax=ax,
            edge_color="#7f8c8d",
            width=1.5,
            alpha=0.7
        )

        # Knoten zeichnen
        nx.draw_networkx_nodes(
            graph, positionen, ax=ax,
            node_color=knotenfarben,
            node_size=knotengroessen,
            alpha=0.9
        )

        # Knotenbezeichnungen
        nx.draw_networkx_labels(
            graph, positionen, ax=ax,
            font_size=8,
            font_color="white",
            font_weight="bold"
        )

        # Kanten-Labels (Port-Informationen) – nur wenn gesetzt
        kanten_labels = {
            (u, v): d.get("protokoll", "")
            for u, v, d in graph.edges(data=True)
            if d.get("protokoll")
        }
        if kanten_labels:
            nx.draw_networkx_edge_labels(
                graph, positionen, kanten_labels, ax=ax,
                font_size=6,
                font_color="#bdc3c7",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="#2c3e50", alpha=0.7)
            )

        # Legende
        legende_eintraege = [
            mpatches.Patch(color="#e74c3c", label="Router"),
            mpatches.Patch(color="#2ecc71", label="Switch"),
            mpatches.Patch(color="#e67e22", label="Firewall"),
            mpatches.Patch(color="#3498db", label="Server"),
            mpatches.Patch(color="#95a5a6", label="Workstation"),
            mpatches.Patch(color="#bdc3c7", label="Unbekannt"),
        ]
        ax.legend(
            handles=legende_eintraege,
            loc="upper left",
            facecolor="#2c3e50",
            labelcolor="white",
            fontsize=9
        )

        ax.set_title(
            f"Netzwerk-Topologie  |  {graph.number_of_nodes()} Geräte, {graph.number_of_edges()} Verbindungen",
            color="white", fontsize=13, pad=15
        )
        ax.axis("off")
        plt.tight_layout()

        dateiname = os.path.join(AUSGABE_VERZEICHNIS, f"topologie_{zeitstempel}.png")
        plt.savefig(dateiname, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close()
        print(f"     -> PNG gespeichert: {dateiname}")

    # ------------------------------------------------------------------
    # HTML-Ausgabe (D3.js Force-Directed-Graph)
    # ------------------------------------------------------------------

    def _html_erstellen(self, graph: Any, zeitstempel: str) -> None:
        """
        Erstellt eine interaktive HTML-Topologiekarte mit D3.js.

        Die Gerätedaten werden als JSON direkt in die HTML-Datei eingebettet.
        D3.js simuliert eine physikalische Kräftesimulation im Browser:
          - Knotenabstoßung verhindert Überlappungen
          - Kantenanzug positioniert verbundene Knoten nahe beieinander
          - Drag-and-Drop ermöglicht manuelle Neuanordnung

        Die generierte Datei ist vollständig eigenständig (standalone):
        nur D3.js wird per CDN geladen, alle Daten sind eingebettet.
        """
        # Graphdaten für D3 vorbereiten
        knoten = []
        for node, data in graph.nodes(data=True):
            knoten.append({
                "id":       node,
                "typ":      data.get("typ", "unknown"),
                "host":     data.get("host", ""),
                "descr":    data.get("sys_descr", "")[:60],
                "location": data.get("sys_location", ""),
                "farbe":    data.get("farbe", "#bdc3c7"),
            })

        kanten = []
        for u, v, data in graph.edges(data=True):
            kanten.append({
                "source":    u,
                "target":    v,
                "protokoll": data.get("protokoll", ""),
                "label":     data.get("label", ""),
            })

        graph_json = json.dumps({"nodes": knoten, "links": kanten}, ensure_ascii=False)

        html = f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Netzwerk-Topologie</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ background: #1a1a2e; color: #eee; font-family: 'Segoe UI', sans-serif; }}
    #header {{ padding: 16px 24px; background: #16213e; border-bottom: 1px solid #0f3460; }}
    #header h1 {{ font-size: 1.3rem; color: #e94560; }}
    #header p  {{ font-size: 0.85rem; color: #7f8c8d; margin-top: 4px; }}
    #svg-container {{ width: 100%; height: calc(100vh - 70px); }}
    svg {{ width: 100%; height: 100%; }}
    .link {{ stroke: #7f8c8d; stroke-opacity: 0.6; stroke-width: 1.5px; }}
    .link-label {{ fill: #95a5a6; font-size: 10px; }}
    .node circle {{ stroke: #fff; stroke-width: 1.5px; cursor: pointer; }}
    .node circle:hover {{ stroke: #e94560; stroke-width: 2.5px; }}
    .node text {{ fill: #ecf0f1; font-size: 11px; pointer-events: none; }}
    #tooltip {{
      position: absolute; padding: 8px 12px; background: #16213e;
      border: 1px solid #0f3460; border-radius: 6px; font-size: 12px;
      pointer-events: none; opacity: 0; transition: opacity 0.2s;
      max-width: 260px; line-height: 1.6;
    }}
    #legend {{
      position: absolute; top: 80px; right: 20px;
      background: #16213e; border: 1px solid #0f3460;
      border-radius: 8px; padding: 12px 16px;
    }}
    .legend-item {{ display: flex; align-items: center; gap: 8px; margin: 4px 0; font-size: 12px; }}
    .legend-dot {{ width: 12px; height: 12px; border-radius: 50%; }}
  </style>
</head>
<body>
<div id="header">
  <h1>Netzwerk-Topologie-Karte</h1>
  <p>{graph.number_of_nodes()} Geräte &nbsp;•&nbsp; {graph.number_of_edges()} Verbindungen &nbsp;•&nbsp; {datetime.now().strftime('%d.%m.%Y %H:%M')}</p>
</div>
<div id="svg-container"><svg id="graph"></svg></div>
<div id="tooltip"></div>
<div id="legend">
  <div style="font-size:12px; font-weight:bold; margin-bottom:8px; color:#e94560">Gerätetypen</div>
  <div class="legend-item"><div class="legend-dot" style="background:#e74c3c"></div>Router</div>
  <div class="legend-item"><div class="legend-dot" style="background:#2ecc71"></div>Switch</div>
  <div class="legend-item"><div class="legend-dot" style="background:#e67e22"></div>Firewall</div>
  <div class="legend-item"><div class="legend-dot" style="background:#3498db"></div>Server</div>
  <div class="legend-item"><div class="legend-dot" style="background:#95a5a6"></div>Workstation</div>
  <div class="legend-item"><div class="legend-dot" style="background:#bdc3c7"></div>Unbekannt</div>
</div>
<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
<script>
const graphData = {graph_json};

const width  = document.getElementById('svg-container').clientWidth;
const height = document.getElementById('svg-container').clientHeight;
const svg = d3.select('#graph');
const tooltip = document.getElementById('tooltip');

// Zoom und Pan aktivieren
const zoom = d3.zoom().scaleExtent([0.2, 5]).on('zoom', e => container.attr('transform', e.transform));
svg.call(zoom);
const container = svg.append('g');

// Physikalische Simulation starten
const simulation = d3.forceSimulation(graphData.nodes)
  .force('link',   d3.forceLink(graphData.links).id(d => d.id).distance(120))
  .force('charge', d3.forceManyBody().strength(-400))
  .force('center', d3.forceCenter(width / 2, height / 2))
  .force('collision', d3.forceCollide(40));

// Kanten zeichnen
const link = container.append('g')
  .selectAll('line').data(graphData.links).join('line').attr('class', 'link');

// Kanten-Labels
const linkLabel = container.append('g')
  .selectAll('text').data(graphData.links).join('text')
  .attr('class', 'link-label').text(d => d.protokoll);

// Knoten-Gruppe
const node = container.append('g')
  .selectAll('g').data(graphData.nodes).join('g').attr('class', 'node')
  .call(d3.drag()
    .on('start', (e, d) => {{ if (!e.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; }})
    .on('drag',  (e, d) => {{ d.fx = e.x; d.fy = e.y; }})
    .on('end',   (e, d) => {{ if (!e.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; }})
  );

// Kreis für jeden Knoten
node.append('circle')
  .attr('r', d => ['router','switch','firewall'].includes(d.typ) ? 18 : 13)
  .attr('fill', d => d.farbe)
  .on('mouseover', (e, d) => {{
    tooltip.style.opacity = 1;
    tooltip.style.left = (e.pageX + 12) + 'px';
    tooltip.style.top  = (e.pageY - 10) + 'px';
    tooltip.innerHTML = `<strong>${{d.id}}</strong><br>IP: ${{d.host || '–'}}<br>Typ: ${{d.typ}}<br>Standort: ${{d.location || '–'}}<br><small style="color:#7f8c8d">${{d.descr}}</small>`;
  }})
  .on('mouseout', () => tooltip.style.opacity = 0);

// Bezeichnung unter dem Knoten
node.append('text').text(d => d.id).attr('y', d => ['router','switch','firewall'].includes(d.typ) ? 30 : 25).attr('text-anchor', 'middle');

// Simulationsschritt: Positionen aktualisieren
simulation.on('tick', () => {{
  link.attr('x1', d => d.source.x).attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
  linkLabel.attr('x', d => (d.source.x + d.target.x) / 2).attr('y', d => (d.source.y + d.target.y) / 2);
  node.attr('transform', d => `translate(${{d.x}},${{d.y}})`);
}});
</script>
</body></html>"""

        dateiname = os.path.join(AUSGABE_VERZEICHNIS, f"topologie_{zeitstempel}.html")
        with open(dateiname, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"     -> HTML gespeichert: {dateiname}")

    # ------------------------------------------------------------------
    # Textausgabe (Terminal)
    # ------------------------------------------------------------------

    def _text_ausgabe(self, graph: Any, geraete: List[Dict]) -> None:
        """Gibt die Topologie übersichtlich im Terminal aus."""
        farbe_typ = {
            "router":      Fore.RED    if FARBEN_VERFUEGBAR else "",
            "switch":      Fore.GREEN  if FARBEN_VERFUEGBAR else "",
            "firewall":    Fore.YELLOW if FARBEN_VERFUEGBAR else "",
            "server":      Fore.BLUE   if FARBEN_VERFUEGBAR else "",
            "workstation": Fore.WHITE  if FARBEN_VERFUEGBAR else "",
            "unknown":     ""          if not FARBEN_VERFUEGBAR else Fore.WHITE,
        }
        reset = Style.RESET_ALL if FARBEN_VERFUEGBAR else ""

        print(f"\n{'─'*60}")
        print(f"  ERKANNTE GERÄTE ({graph.number_of_nodes()})")
        print(f"{'─'*60}")
        print(f"  {'NAME':<22} {'IP':<16} {'TYP':<12} BESCHREIBUNG")
        print(f"  {'─'*20}  {'─'*14}  {'─'*10}  {'─'*20}")

        for node, data in sorted(graph.nodes(data=True)):
            typ   = data.get("typ", "unknown")
            farbe = farbe_typ.get(typ, "")
            descr = data.get("sys_descr", "")[:30]
            host  = data.get("host", "")
            print(f"  {farbe}{node:<22}{reset} {host:<16} {typ:<12} {descr}")

        print(f"\n{'─'*60}")
        print(f"  ERKANNTE VERBINDUNGEN ({graph.number_of_edges()})")
        print(f"{'─'*60}")

        for u, v, data in graph.edges(data=True):
            protokoll = data.get("protokoll", "")
            port_l    = data.get("port_lokal", "")
            port_r    = data.get("port_remote", "")
            if port_l and port_r:
                print(f"  {u:<22}  {port_l:<22} ↔  {port_r:<22}  {v}  [{protokoll}]")
            else:
                print(f"  {u:<22}  ↔  {v}  [{protokoll}]")

        print()
