"""
ACER Graph Visualization - DTDL-style interactive graph view
Inspired by Azure Digital Twins DTDL viewer
"""
import tempfile
from pathlib import Path
from typing import Optional

from pyvis.network import Network
import streamlit as st

from models.acer_graph import AcerGraph, Relationship, Datapoint


def create_acer_graph_view(graph: AcerGraph, height: str = "600px") -> str:
    """
    Create an interactive DTDL-style graph visualization.
    
    Layout:
    - Document node at center
    - 6 relationship nodes around it
    - Datapoint nodes connected to hasDatapoint
    
    Returns HTML string.
    """
    net = Network(height=height, width="100%", bgcolor="#1e1e1e", font_color="white",
                  notebook=False, cdn_resources='remote')
    
    # Physics settings for nice layout
    net.set_options("""
    {
      "nodes": {
        "borderWidth": 2,
        "borderWidthSelected": 4,
        "font": {
          "size": 14,
          "face": "arial"
        }
      },
      "edges": {
        "color": {
          "inherit": true
        },
        "smooth": {
          "type": "continuous",
          "roundness": 0.5
        }
      },
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -100,
          "centralGravity": 0.01,
          "springLength": 150,
          "springConstant": 0.08
        },
        "maxVelocity": 50,
        "solver": "forceAtlas2Based",
        "timestep": 0.35,
        "stabilization": {
          "enabled": true,
          "iterations": 1000
        }
      },
      "interaction": {
        "hover": true,
        "tooltipDelay": 100,
        "hideEdgesOnDrag": true,
        "navigationButtons": true
      }
    }
    """)
    
    # Colors for relationship types
    colors = {
        "document": "#6366f1",      # Indigo - document
        "metadata": "#22c55e",       # Green - auto
        "equipment": "#3b82f6",     # Blue - equipment
        "asset_type": "#8b5cf6",    # Purple - classification
        "datapoint": "#f59e0b",      # Amber - data
        "impact": "#ec4899",          # Pink - sustainability
        "requirement": "#ef4444",    # Red - compliance
        "datapoint_child": "#fbbf24" # Yellow - individual datapoint
    }
    
    # === Document Node (Center) ===
    doc_id = "document"
    doc_label = graph.document_name.split('.')[0] if '.' in graph.document_name else graph.document_name
    
    net.add_node(
        doc_id,
        label=doc_label,
        title=f"Document: {graph.document_name}\n\nClick relationships to expand",
        color=colors["document"],
        shape="box",
        size=40,
        font={"size": 16, "color": "white", "bold": True}
    )
    
    # === Relationship Nodes ===
    relationship_colors = {
        "hasMetadata": colors["metadata"],
        "hasEquipment": colors["equipment"],
        "hasAssetType": colors["asset_type"],
        "hasDatapoint": colors["datapoint"],
        "hasImpactCategory": colors["impact"],
        "hasRequirementSource": colors["requirement"]
    }
    
    relationship_shapes = {
        "hasMetadata": "dot",
        "hasEquipment": "diamond",
        "hasAssetType": "triangle",
        "hasDatapoint": "star",
        "hasImpactCategory": "hexagon",
        "hasRequirementSource": "square"
    }
    
    for name, rel in graph.get_all_relationships():
        display_name = graph.RELATIONSHIP_DISPLAY_NAMES.get(name, name)
        
        # Create node ID
        rel_id = name
        
        # Status indicator
        status_icon = "✓" if rel.found else "○"
        status_color = relationship_colors.get(display_name, "#888888")
        
        # Count for datapoints
        count_info = ""
        if isinstance(rel.value, list) and rel.value:
            count_info = f"\n📊 {len(rel.value)} items"
        
        # Confidence
        conf_info = f"\nConfidence: {rel.confidence:.0%}" if rel.confidence else ""
        
        # Description
        desc = graph.RELATIONSHIP_DESCRIPTIONS.get(display_name, "")
        
        net.add_node(
            rel_id,
            label=f"{status_icon} {display_name}",
            title=f"{display_name}\n\n{desc}\n{conf_info}{count_info}",
            color=status_color if rel.found else "#555555",
            shape=relationship_shapes.get(display_name, "dot"),
            size=30 if rel.found else 20,
            font={"size": 12, "color": "white"}
        )
        
        # Edge from document to relationship
        edge_color = "#22c55e" if rel.found else "#555555"
        edge_width = 3 if rel.found else 1
        
        net.add_edge(
            doc_id,
            rel_id,
            color=edge_color,
            width=edge_width,
            title=f"has{display_name.replace('has', '')}" if "has" not in display_name.lower() else display_name
        )
        
        # === Datapoint Nodes (children of hasDatapoint) ===
        if display_name == "hasDatapoint" and isinstance(rel.value, list):
            for dp in rel.value[:20]:  # Limit to 20 for performance
                dp_id = f"dp_{dp.id}"
                
                conf_color = "#22c55e" if dp.confidence >= 0.85 else "#f59e0b" if dp.confidence >= 0.6 else "#ef4444"
                
                net.add_node(
                    dp_id,
                    label=f"#{dp.id} {dp.aligned_datapoint[:15]}...",
                    title=f"ACER Datapoint\n\n{dp.aligned_datapoint}\nValue: {dp.value} {dp.unit or ''}\nConfidence: {dp.confidence:.0%}\nCategory: {dp.impact_category}",
                    color=conf_color,
                    shape="dot",
                    size=15,
                    font={"size": 10, "color": "white"}
                )
                
                net.add_edge(
                    rel_id,
                    dp_id,
                    color="#f59e0b",
                    width=2,
                    title=f"value: {dp.value}"
                )
    
    # Generate HTML
    html = net.generate_html(notebook=False)
    return html


def render_graph_html(html_content: str) -> None:
    """Render pyvis HTML in Streamlit."""
    st.components.v1.html(html_content, height=600, scrolling=True)


def render_simple_graph_view(graph: AcerGraph) -> None:
    """Simple fallback graph using Streamlit columns."""
    st.subheader("ACER Graph Structure")
    
    # Document header
    st.markdown(f"""
    <div style="background: #6366f1; padding: 1rem; border-radius: 8px; text-align: center; margin-bottom: 1rem;">
        <strong style="color: white; font-size: 1.2em;">📄 {graph.document_name}</strong>
    </div>
    """, unsafe_allow_html=True)
    
    # Create visual representation
    cols = st.columns(3)
    
    for idx, (name, rel) in enumerate(graph.get_all_relationships()):
        col = cols[idx % 3]
        display_name = graph.RELATIONSHIP_DISPLAY_NAMES.get(name, name)
        
        with col:
            status = "✓" if rel.found else "○"
            color = "#22c55e" if rel.found else "#888888"
            
            if isinstance(rel.value, list):
                count = len(rel.value)
                info = f"{count} datapoints"
            elif isinstance(rel.value, dict):
                info = ", ".join(f"{k}: {v}" for k, v in list(rel.value.items())[:2])
            elif rel.value:
                info = str(rel.value)[:30]
            else:
                info = "Not found"
            
            st.markdown(f"""
            <div style="background: {color}22; border-left: 4px solid {color}; padding: 0.75rem; border-radius: 4px; margin-bottom: 0.5rem;">
                <strong>{status} {display_name}</strong>
                <br><small style="color: #888;">{info}</small>
            </div>
            """, unsafe_allow_html=True)
