"""
ACER Graph Visualization - Obsidian Style
Clean, minimal force-directed graph with Obsidian aesthetics
"""
import json
from typing import Optional

import streamlit.components.v1 as components
import streamlit as st

from models.acer_graph import AcerGraph, Relationship, Datapoint, ConfidenceLevel


def create_obsidian_graph_html(graph: AcerGraph, height: str = "650px") -> str:
    """
    Create an Obsidian-style interactive graph visualization.
    
    Features:
    - Dark theme with subtle borders
    - Circular nodes with labels
    - Force-directed layout
    - Hover tooltips
    - Drag and zoom
    """
    
    # Build D3 graph data
    nodes = []
    links = []
    
    # Document node (center)
    doc_id = "doc"
    nodes.append({
        "id": doc_id,
        "label": graph.document_name.split('.')[0] if '.' in graph.document_name else graph.document_name,
        "type": "document",
        "found": True,
        "size": 40
    })
    
    # Relationship colors
    rel_colors = {
        "hasMetadata": "#4ade80",
        "hasEquipment": "#60a5fa", 
        "hasAssetType": "#a78bfa",
        "hasDatapoint": "#fbbf24",
        "hasImpactCategory": "#f472b6",
        "hasRequirementSource": "#f87171"
    }
    
    for name, rel in graph.get_all_relationships():
        display_name = graph.RELATIONSHIP_DISPLAY_NAMES.get(name, name)
        rel_id = "rel_" + name
        
        if isinstance(rel.value, list) and rel.value:
            count = len(rel.value)
            label = display_name + "\n(" + str(count) + ")"
        else:
            label = display_name
        
        nodes.append({
            "id": rel_id,
            "label": label,
            "type": "relationship",
            "found": rel.found,
            "color": rel_colors.get(display_name, "#888888"),
            "displayName": display_name,
            "size": 28 if rel.found else 22
        })
        
        links.append({
            "source": doc_id,
            "target": rel_id,
            "strength": 1 if rel.found else 0.3
        })
        
        # Datapoint nodes
        if display_name == "hasDatapoint" and isinstance(rel.value, list):
            for dp in rel.value[:25]:
                dp_id = "dp_" + str(dp.id)
                
                if dp.confidence >= 0.85:
                    conf_color = "#4ade80"
                elif dp.confidence >= 0.60:
                    conf_color = "#fbbf24"
                else:
                    conf_color = "#f87171"
                
                tooltip = {
                    "id": dp.id,
                    "datapoint": dp.aligned_datapoint,
                    "value": dp.value,
                    "unit": dp.unit or "",
                    "category": dp.impact_category,
                    "confidence": dp.confidence
                }
                
                nodes.append({
                    "id": dp_id,
                    "label": "#" + str(dp.id),
                    "type": "datapoint",
                    "found": True,
                    "color": conf_color,
                    "size": 16,
                    "tooltip": tooltip
                })
                
                links.append({
                    "source": rel_id,
                    "target": dp_id,
                    "strength": 0.5
                })
    
    graph_data = {
        "nodes": nodes,
        "links": links
    }
    
    graph_json = json.dumps(graph_data)
    
    # CSS styles
    css = """
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { background: #1a1a1a; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; overflow: hidden; }
    #graph { width: 100%; height: HEIGHT_PLACEHOLDER; background: #1a1a1a; }
    .node circle { stroke: #333; stroke-width: 2px; cursor: pointer; transition: all 0.2s ease; }
    .node circle:hover { stroke: #fff; stroke-width: 3px; }
    .node.document circle { fill: #6366f1; }
    .node.relationship circle { fill-opacity: 0.9; }
    .node.relationship.not-found circle { fill: #444; stroke: #555; stroke-dasharray: 4,2; }
    .node.datapoint circle { fill-opacity: 0.85; }
    .node text { fill: #ccc; font-size: 11px; font-family: inherit; text-anchor: middle; pointer-events: none; text-shadow: 0 1px 3px rgba(0,0,0,0.8); }
    .link { stroke: #444; stroke-opacity: 0.6; stroke-width: 1.5px; }
    .link.not-found { stroke: #2a2a2a; stroke-opacity: 0.3; stroke-dasharray: 3,3; }
    #tooltip { position: absolute; background: #252525; border: 1px solid #444; border-radius: 8px; padding: 12px; font-size: 12px; color: #e0e0e0; pointer-events: none; opacity: 0; transition: opacity 0.2s; max-width: 320px; box-shadow: 0 4px 12px rgba(0,0,0,0.4); z-index: 1000; }
    #tooltip.visible { opacity: 1; }
    #tooltip .title { font-weight: 600; color: #fff; margin-bottom: 8px; }
    #tooltip .row { display: flex; justify-content: space-between; margin: 4px 0; gap: 16px; }
    #tooltip .label { color: #888; }
    #tooltip .value { color: #ddd; }
    #tooltip .conf-high { color: #4ade80; }
    #tooltip .conf-medium { color: #fbbf24; }
    #tooltip .conf-low { color: #f87171; }
    #controls { position: absolute; top: 10px; right: 10px; display: flex; gap: 8px; }
    #controls button { background: #2a2a2a; border: 1px solid #444; color: #ccc; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; transition: all 0.2s; }
    #controls button:hover { background: #3a3a3a; color: #fff; }
    #legend { position: absolute; bottom: 10px; left: 10px; background: #252525cc; border: 1px solid #333; border-radius: 8px; padding: 10px 14px; font-size: 11px; color: #aaa; }
    #legend .item { display: flex; align-items: center; gap: 8px; margin: 4px 0; }
    #legend .dot { width: 10px; height: 10px; border-radius: 50%; }
    """
    
    # JavaScript - avoiding f-string conflicts by using string concatenation
    js = """
    const graphData = GRAPH_DATA_JSON;
    
    let showLabels = true;
    
    const svg = d3.select("#graph")
        .append("svg")
        .attr("width", "100%")
        .attr("height", "100%");
    
    const g = svg.append("g");
    
    const zoom = d3.zoom()
        .scaleExtent([0.2, 4])
        .on("zoom", function(event) {
            g.attr("transform", event.transform);
        });
    svg.call(zoom);
    
    function resetZoom() {
        svg.transition().duration(500).call(zoom.transform, d3.zoomIdentity);
    }
    
    function toggleLabels() {
        showLabels = !showLabels;
        g.selectAll(".node text").style("opacity", showLabels ? 1 : 0);
    }
    
    const simulation = d3.forceSimulation(graphData.nodes)
        .force("link", d3.forceLink(graphData.links).id(function(d) { return d.id; }).distance(100))
        .force("charge", d3.forceManyBody().strength(-300))
        .force("center", d3.forceCenter(
            document.getElementById("graph").clientWidth / 2,
            document.getElementById("graph").clientHeight / 2
        ))
        .force("collision", d3.forceCollide().radius(function(d) { return d.size + 10; }));
    
    const link = g.append("g")
        .selectAll(".link")
        .data(graphData.links)
        .join("line")
        .attr("class", function(d) { return d.strength < 1 ? "link not-found" : "link"; })
        .style("stroke", function(d) { return d.strength >= 1 ? "#444" : "#2a2a2a"; })
        .style("stroke-opacity", function(d) { return d.strength >= 1 ? 0.6 : 0.3; });
    
    const node = g.append("g")
        .selectAll(".node")
        .data(graphData.nodes)
        .join("g")
        .attr("class", function(d) {
            var cls = "node " + d.type;
            if (d.type === "relationship" && !d.found) cls += " not-found";
            return cls;
        })
        .call(d3.drag()
            .on("start", dragstarted)
            .on("drag", dragged)
            .on("end", dragended));
    
    node.append("circle")
        .attr("r", function(d) { return d.size; })
        .style("fill", function(d) { return d.color || "#888"; });
    
    node.append("text")
        .attr("dy", function(d) { return d.size + 16; })
        .text(function(d) { return d.label.split("\\n")[0]; })
        .style("font-size", function(d) { return d.type === "document" ? "13px" : "11px"; });
    
    const tooltip = d3.select("#tooltip");
    
    node.on("mouseover", function(event, d) {
        tooltip.html(getTooltipHTML(d)).classed("visible", true);
    });
    
    node.on("mousemove", function(event) {
        tooltip
            .style("left", (event.pageX + 15) + "px")
            .style("top", (event.pageY - 10) + "px");
    });
    
    node.on("mouseout", function() {
        tooltip.classed("visible", false);
    });
    
    function getTooltipHTML(d) {
        if (d.type === "document") {
            return '<div class="title">Document</div><div class="value">' + d.label + '</div>';
        }
        if (d.type === "relationship") {
            var status = d.found ? "Found" : "Not Found";
            return '<div class="title">' + (d.displayName || d.label) + '</div><div class="row"><span class="label">Status</span><span class="value">' + status + '</span></div>';
        }
        if (d.type === "datapoint" && d.tooltip) {
            var t = d.tooltip;
            var confClass = t.confidence >= 0.85 ? "conf-high" : t.confidence >= 0.60 ? "conf-medium" : "conf-low";
            return '<div class="title">#' + t.id + ': ' + t.datapoint + '</div><div class="row"><span class="label">Value</span><span class="value">' + t.value + ' ' + t.unit + '</span></div><div class="row"><span class="label">Category</span><span class="value">' + t.category + '</span></div><div class="row"><span class="label">Confidence</span><span class="value ' + confClass + '">' + (t.confidence * 100).toFixed(0) + '%</span></div>';
        }
        return '<div class="title">' + d.label + '</div>';
    }
    
    simulation.on("tick", function() {
        link
            .attr("x1", function(d) { return d.source.x; })
            .attr("y1", function(d) { return d.source.y; })
            .attr("x2", function(d) { return d.target.x; })
            .attr("y2", function(d) { return d.target.y; });
        
        node.attr("transform", function(d) { return "translate(" + d.x + "," + d.y + ")"; });
    });
    
    function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }
    
    function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }
    
    function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }
    
    resetZoom();
    """
    
    # HTML template
    html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>""" + css + """</style>
</head>
<body>
    <div id="graph"></div>
    <div id="tooltip"></div>
    <div id="controls">
        <button onclick="resetZoom()">Reset View</button>
        <button onclick="toggleLabels()">Toggle Labels</button>
    </div>
    <div id="legend">
        <div class="item"><div class="dot" style="background:#6366f1"></div>Document</div>
        <div class="item"><div class="dot" style="background:#4ade80"></div>Metadata</div>
        <div class="item"><div class="dot" style="background:#60a5fa"></div>Equipment</div>
        <div class="item"><div class="dot" style="background:#a78bfa"></div>Asset Type</div>
        <div class="item"><div class="dot" style="background:#fbbf24"></div>Datapoints</div>
        <div class="item"><div class="dot" style="background:#f472b6"></div>Impact Category</div>
        <div class="item"><div class="dot" style="background:#f87171"></div>Requirement Source</div>
    </div>
    
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script>""" + js + """</script>
</body>
</html>"""
    
    # Replace placeholders
    html = html.replace("HEIGHT_PLACEHOLDER", height)
    html = html.replace("GRAPH_DATA_JSON", graph_json)
    
    return html


def render_obsidian_graph(graph: AcerGraph, height: str = "650px") -> None:
    """Render Obsidian-style graph in Streamlit."""
    html = create_obsidian_graph_html(graph, height)
    height_px = int(height.replace("px", "")) + 50
    components.html(html, height=height_px, scrolling=True)


def render_confidence_legend():
    """Show confidence level legend."""
    st.markdown("""
    **Confidence Levels:**
    - High (>=85%) -- Reliable extraction
    - Medium (60-84%) -- Verify manually  
    - Low (<60%) -- Needs review
    """)


def render_extraction_vs_alignment_info():
    """Explain the two confidence types."""
    with st.expander("About Confidence Scores"):
        st.markdown("""
        **Two Confidence Types:**
        
        | Type | Description | When Low |
        |------|-------------|----------|
        | **Extraction Confidence** | Did we read the PDF correctly? | Poor scan, tables, small text |
        | **Alignment Confidence** | Did we map to the right ACER datapoint? | Ambiguous terms, synonyms |
        
        **Overall Confidence** = Extraction x Alignment
        
        Example: PDF extraction was clear (95%) but the term "SEER" could map to multiple ACER datapoints (70%) -> Overall: 67%
        """)
