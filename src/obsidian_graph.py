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
    - Color gradient from green (100% conf) to red (0% conf)
    """
    
    def confidence_to_color(confidence: float) -> str:
        """Convert confidence (0-1) to color: red -> yellow -> green"""
        if confidence is None:
            return "#ef4444"  # bright red
        
        # Clamp to valid range
        confidence = max(0.0, min(1.0, confidence))
        
        # Three-point gradient: Red (#ef4444) -> Yellow (#eab308) -> Green (#22c55e)
        red = (239, 68, 68)
        yellow = (234, 179, 8)
        green = (34, 197, 94)
        
        if confidence >= 0.5:
            # Yellow to Green (0.5 -> 1.0)
            t = (confidence - 0.5) / 0.5
            r = int(yellow[0] + (green[0] - yellow[0]) * t)
            g = int(yellow[1] + (green[1] - yellow[1]) * t)
            b = int(yellow[2] + (green[2] - yellow[2]) * t)
        else:
            # Red to Yellow (0.0 -> 0.5)
            t = confidence / 0.5
            r = int(red[0] + (yellow[0] - red[0]) * t)
            g = int(red[1] + (yellow[1] - red[1]) * t)
            b = int(red[2] + (yellow[2] - red[2]) * t)
        
        return f"#{r:02x}{g:02x}{b:02x}"
    
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
        "size": 25,
        "color": "#6366f1"
    })
    
    for name, rel in graph.get_all_relationships():
        # Skip NOT FOUND relationships entirely
        if not rel.found:
            continue
            
        display_name = graph.RELATIONSHIP_DISPLAY_NAMES.get(name, name)
        rel_id = "rel_" + name
        
        # Color based on confidence
        conf_color = confidence_to_color(rel.confidence)
        
        if isinstance(rel.value, list) and rel.value:
            count = len(rel.value)
            label = display_name + "\n(" + str(count) + ")"
        else:
            label = display_name
        
        nodes.append({
            "id": rel_id,
            "label": label,
            "type": "relationship",
            "found": True,
            "color": conf_color,
            "displayName": display_name,
            "confidence": rel.confidence,
            "size": 18
        })
        
        links.append({
            "source": doc_id,
            "target": rel_id,
            "strength": 1
        })
        
        # Datapoint nodes
        if display_name == "hasDatapoint" and isinstance(rel.value, list):
            for dp in rel.value[:25]:
                dp_id = "dp_" + str(dp.id)
                
                dp_conf_color = confidence_to_color(dp.confidence)
                
                tooltip = {
                    "id": dp.id,
                    "datapoint": dp.aligned_datapoint,
                    "value": dp.value,
                    "unit": dp.unit or "",
                    "category": dp.impact_category,
                    "confidence": dp.confidence,
                    "sourcePage": dp.source_page or "",
                    "sourceLocation": dp.source_location or ""
                }
                
                nodes.append({
                    "id": dp_id,
                    "label": "#" + str(dp.id),
                    "type": "datapoint",
                    "found": True,
                    "color": dp_conf_color,
                    "confidence": dp.confidence,
                    "size": 10,
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
    .node.datapoint circle { fill-opacity: 0.85; }
    .node text { fill: #ccc; font-size: 9px; font-family: inherit; text-anchor: middle; pointer-events: none; text-shadow: 0 1px 3px rgba(0,0,0,0.8); }
    .link { stroke: #444; stroke-opacity: 0.6; stroke-width: 1.5px; }
    #tooltip { position: absolute; background: #252525; border: 1px solid #444; border-radius: 8px; padding: 12px; font-size: 12px; color: #e0e0e0; pointer-events: none; opacity: 0; transition: opacity 0.2s; max-width: 320px; box-shadow: 0 4px 12px rgba(0,0,0,0.4); z-index: 1000; }
    #tooltip.visible { opacity: 1; }
    #tooltip .title { font-weight: 600; color: #fff; margin-bottom: 8px; }
    #tooltip .row { display: flex; justify-content: space-between; margin: 4px 0; gap: 16px; }
    #tooltip .label { color: #888; }
    #tooltip .value { color: #ddd; }
    #tooltip .confidence { font-weight: 600; }
    #controls { position: absolute; top: 10px; right: 10px; display: flex; gap: 8px; }
    #controls button { background: #2a2a2a; border: 1px solid #444; color: #ccc; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; transition: all 0.2s; }
    #controls button:hover { background: #3a3a3a; color: #fff; }
    #legend { position: absolute; bottom: 10px; left: 10px; background: #252525cc; border: 1px solid #333; border-radius: 8px; padding: 10px 14px; font-size: 11px; color: #aaa; }
    #legend .item { display: flex; align-items: center; gap: 8px; margin: 4px 0; }
    #legend .dot { width: 10px; height: 10px; border-radius: 50%; }
    #legend .gradient { width: 80px; height: 10px; border-radius: 3px; background: linear-gradient(to right, #ef4444, #eab308, #22c55e); }
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
        .attr("class", "link")
        .style("stroke", "#444")
        .style("stroke-opacity", 0.6);
    
    const node = g.append("g")
        .selectAll(".node")
        .data(graphData.nodes)
        .join("g")
        .attr("class", function(d) { return "node " + d.type; })
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
            var conf = d.confidence ? (d.confidence * 100).toFixed(0) + '%' : 'N/A';
            return '<div class="title">' + (d.displayName || d.label) + '</div><div class="row"><span class="label">Confidence</span><span class="confidence" style="color:' + d.color + '">' + conf + '</span></div>';
        }
        if (d.type === "datapoint" && d.tooltip) {
            var t = d.tooltip;
            var sourceInfo = "";
            if (t.sourcePage || t.sourceLocation) {
                sourceInfo = '<div class="row"><span class="label">Source</span><span class="value">' + (t.sourcePage ? 'p.' + t.sourcePage : '') + (t.sourcePage && t.sourceLocation ? ' · ' : '') + (t.sourceLocation || '') + '</span></div>';
            }
            return '<div class="title">#' + t.id + ': ' + t.datapoint + '</div><div class="row"><span class="label">Value</span><span class="value">' + t.value + ' ' + t.unit + '</span></div><div class="row"><span class="label">Category</span><span class="value">' + t.category + '</span></div><div class="row"><span class="label">Confidence</span><span class="confidence" style="color:' + d.color + '">' + (t.confidence * 100).toFixed(0) + '%</span></div>' + sourceInfo;
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
        <div style="margin-top: 8px; margin-bottom: 4px; font-weight: 600;">Confidence</div>
        <div class="item"><div class="gradient"></div></div>
        <div class="item" style="justify-content: space-between; font-size: 10px;">
            <span>0%</span>
            <span>100%</span>
        </div>
    </div>
    
    <script src="https://d3js.org/d3.v7.min.js" integrity="sha384-nZ9T6N0h0Mqr8/2LZ0iW2u3S2i3T4T0M0M0M0M0M0M0M0M0M0M0M0M0M0M0" crossorigin="anonymous"></script>
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
    **Confidence Scale:**
    | Color | Meaning |
    |-------|---------|
    | 🟢 Green | 100% - High confidence |
    | 🟡 Yellow | 50% - Medium confidence |
    | 🔴 Red | 0% - Low confidence |
    
    Colors interpolate smoothly between these values.
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
