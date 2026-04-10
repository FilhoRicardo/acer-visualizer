"""
ACER Visualizer - Building Passport Processor
Streamlit Web Application

Run with: streamlit run src/app.py
"""
import streamlit as st
import json
import io
from datetime import datetime
import pdfplumber

# Import models
import sys
sys.path.insert(0, 'src')
from models import (
    AcerGraph, 
    Relationship, 
    Datapoint,
    RelationshipStatus,
    ConfidenceLevel,
    create_carrier_rtu_graph,
    create_simple_example_graph,
    create_trane_chiller_graph,
    create_daikin_vrv_graph
)
from extraction import extract_from_text
from obsidian_graph import create_obsidian_graph_html, render_obsidian_graph, render_extraction_vs_alignment_info
from openrouter_client import (
    fetch_available_models,
    extract_with_openrouter,
    validate_api_key,
    get_display_name,
    RECOMMENDED_MODELS,
    get_openrouter_config,
    set_openrouter_config,
)

# Model pricing lookup (input_cost, output_cost per M tokens) - shared across functions
MODEL_PRICING = {
    "anthropic/claude-3-haiku": (0.25, 1.25),
    "anthropic/claude-3-sonnet": (3.00, 15.00),
    "meta-llama/llama-3-8b-instruct": (0.0, 0.0),
    "mistralai/mistral-7b-instruct": (0.0, 0.0),
    "openai/gpt-4o-mini": (0.15, 0.60),
    "google/gemini-pro-1.5": (1.25, 5.00),
    "deepseek/deepseek-chat-v2": (0.28, 1.10),
}


def _to_str(val, default=''):
    """Convert value to string safely."""
    if val is None:
        return default
    return str(val)

def build_graph_from_extraction(extraction: dict, filename: str) -> AcerGraph:
    """
    Build an AcerGraph from extraction results.
    
    Handles two input formats:
    1. OpenRouter raw dict (keys: hasEquipment, hasDatapoint, etc.)
    2. Demo extraction dict (keys: equipment, datapoints, etc. with dataclass values)
    """
    # Detect format and normalize to OpenRouter-style dict
    is_demo_format = 'equipment' in extraction or 'datapoints' in extraction
    
    if is_demo_format:
        # Demo format: convert dataclass objects to dicts
        equip = extraction.get('equipment')
        asset_type = extraction.get('asset_type')
        dps = extraction.get('datapoints', [])
        reqs = extraction.get('requirements', [])
        
        equip_data = {
            'name': getattr(equip, 'name', None),
            'manufacturer': getattr(equip, 'manufacturer', None),
            'confidence': getattr(equip, 'confidence', 0.8)
        } if equip else {}
        
        asset_data = {
            'type': getattr(asset_type, 'type', None),
            'confidence': getattr(asset_type, 'confidence', 0.8)
        } if asset_type else {}
        
        dp_list = []
        for dp in dps:
            dp_list.append({
                'aligned_datapoint': getattr(dp, 'aligned_datapoint', 'Unknown'),
                'value': getattr(dp, 'value', ''),
                'unit': getattr(dp, 'unit', ''),
                'confidence': getattr(dp, 'confidence', 0.5),
                'source_page': str(getattr(dp, 'source_page', '?')),
                'impact_category': getattr(dp, 'impact_category', ''),
                'impact_subcategory': getattr(dp, 'impact_subcategory', '')
            })
        
        standards = [getattr(r, 'standard_name', '') for r in reqs if getattr(r, 'standard_name', '')]
        req_data = {'standards': standards, 'confidence': 0.85}
        
        meta = extraction.get('metadata')
        metadata_data = {
            'filename': getattr(meta, 'filename', filename) if meta else filename,
            'pageCount': getattr(meta, 'page_count', 0) if meta else 0
        }
        
    else:
        # OpenRouter raw dict format
        equip_data = extraction.get('hasEquipment', {}) or {}
        asset_data = extraction.get('hasAssetType', {}) or {}
        dp_list = extraction.get('hasDatapoint', []) or []
        req_data = extraction.get('hasRequirementSource', {}) or {}
        metadata_data = extraction.get('hasMetadata', {}) or {}
    
    # Build metadata relationship
    metadata_rel = Relationship(
        name="hasMetadata",
        found=True,
        value={
            "filename": metadata_data.get('filename', filename) if isinstance(metadata_data, dict) else filename,
            "pages": metadata_data.get('pageCount', metadata_data.get('page_count', 0)) if isinstance(metadata_data, dict) else 0,
            "extractedAt": datetime.now().isoformat()
        },
        confidence=1.0,
        status=RelationshipStatus.FOUND
    )
    
    # Build equipment relationship
    equip_name = equip_data.get('name') if isinstance(equip_data, dict) else getattr(equip_data, 'name', None)
    equip_conf = equip_data.get('confidence', 0.8) if isinstance(equip_data, dict) else getattr(equip_data, 'confidence', 0.8)
    equipment_rel = Relationship(
        name="hasEquipment",
        found=bool(equip_name),
        value=equip_name,
        confidence=equip_conf,
        source_location="OpenRouter LLM" if not is_demo_format else "Demo Extraction",
        status=RelationshipStatus.FOUND if equip_name else RelationshipStatus.NOT_FOUND
    )
    
    # Build asset type relationship
    asset_val = asset_data.get('type') if isinstance(asset_data, dict) else getattr(asset_data, 'type', None)
    asset_conf = asset_data.get('confidence', 0.8) if isinstance(asset_data, dict) else getattr(asset_data, 'confidence', 0.8)
    asset_type_rel = Relationship(
        name="hasAssetType",
        found=bool(asset_val),
        value=asset_val,
        confidence=asset_conf,
        status=RelationshipStatus.FOUND if asset_val else RelationshipStatus.NOT_FOUND
    )
    
    # Build datapoint objects
    datapoint_objects = []
    for i, dp in enumerate(dp_list):
        if isinstance(dp, dict):
            dp_name = dp.get('aligned_datapoint', 'Unknown')
            dp_val = dp.get('value', '')
            dp_unit = dp.get('unit', '')
            dp_conf = dp.get('confidence', 0.5)
            dp_cat = dp.get('impact_category')
            dp_subcat = dp.get('impact_subcategory')
            dp_page = str(dp.get('source_page', '?'))
        else:
            dp_name = getattr(dp, 'aligned_datapoint', 'Unknown')
            dp_val = getattr(dp, 'value', '')
            dp_unit = getattr(dp, 'unit', '')
            dp_conf = getattr(dp, 'confidence', 0.5)
            dp_cat = getattr(dp, 'impact_category', '')
            dp_subcat = getattr(dp, 'impact_subcategory', '')
            dp_page = str(getattr(dp, 'source_page', '?'))
        
        dp_obj = Datapoint(
            id=i + 1,
            aligned_datapoint=dp_name,
            impact_category=dp_cat,
            impact_subcategory=dp_subcat or "General",
            value=str(dp_val),
            unit=dp_unit,
            confidence=dp_conf,
            source_page=dp_page
        )
        datapoint_objects.append(dp_obj)
    
    has_datapoint_rel = Relationship(
        name="hasDatapoint",
        found=len(datapoint_objects) > 0,
        value=datapoint_objects,
        confidence=sum(d.confidence for d in datapoint_objects) / len(datapoint_objects) if datapoint_objects else 0.0,
        status=RelationshipStatus.FOUND if datapoint_objects else RelationshipStatus.NOT_FOUND
    )
    
    # Build impact category
    if isinstance(dp_list[0], dict) if dp_list else False:
        categories = set(dp.get('impact_category') for dp in dp_list if isinstance(dp, dict) and dp.get('impact_category'))
    else:
        categories = set(getattr(dp, 'impact_category', '') for dp in dp_list if getattr(dp, 'impact_category', ''))
    impact_cat_value = ", ".join(sorted(categories)) if categories else None
    impact_cat_rel = Relationship(
        name="hasImpactCategory",
        found=impact_cat_value is not None,
        value=impact_cat_value,
        confidence=0.8 if impact_cat_value else 0.0,
        status=RelationshipStatus.FOUND if impact_cat_value else RelationshipStatus.NOT_FOUND
    )
    
    # Build requirement sources
    if isinstance(req_data, dict):
        standards = req_data.get('standards', [])
        req_conf = req_data.get('confidence', 0.85)
    else:
        standards = [getattr(r, 'standard_name', '') for r in req_data if getattr(r, 'standard_name', '')]
        req_conf = 0.85
    req_values = standards if isinstance(standards, list) else []
    req_rel = Relationship(
        name="hasRequirementSource",
        found=len(req_values) > 0,
        value=req_values,
        confidence=req_conf if req_values else 0.0,
        status=RelationshipStatus.FOUND if req_values else RelationshipStatus.NOT_FOUND
    )
    
    # Build and return graph
    graph = AcerGraph(
        document_name=filename,
        source_file=filename,
        has_metadata=metadata_rel,
        has_equipment=equipment_rel,
        has_asset_type=asset_type_rel,
        has_datapoint=has_datapoint_rel,
        has_impact_category=impact_cat_rel,
        has_requirement_source=req_rel,
        extracted_at=datetime.now(),
        llm_model="OpenRouter" if not is_demo_format else "Demo",
        processing_time_seconds=0.0
    )
    
    return graph


# Page config
st.set_page_config(
    page_title="ACER Visualizer",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1a1a2e;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .relationship-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        margin: 0.5rem 0;
    }
    .relationship-found {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
    }
    .relationship-missing {
        background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
    }
    .confidence-high { color: #11998e; font-weight: bold; }
    .confidence-medium { color: #f59e0b; font-weight: bold; }
    .confidence-low { color: #eb3349; font-weight: bold; }
    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #1a1a2e;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #666;
    }
    .datapoint-row {
        padding: 0.75rem;
        border-left: 4px solid #667eea;
        margin: 0.5rem 0;
        background: #f8f9fa;
        border-radius: 0 8px 8px 0;
    }
    .stButton>button {
        width: 100%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.75rem 1.5rem;
        border-radius: 8px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


def render_confidence_badge(confidence: float | None) -> str:
    """Render confidence as colored badge."""
    if confidence is None:
        return '<span class="confidence-low">—</span>'
    
    if confidence >= 0.85:
        return f'<span class="confidence-high">✓ {confidence:.0%}</span>'
    elif confidence >= 0.60:
        return f'<span class="confidence-medium">⚠ {confidence:.0%}</span>'
    else:
        return f'<span class="confidence-low">✗ {confidence:.0%}</span>'


def render_relationship_card(name: str, relationship: Relationship, description: str):
    """Render a single relationship card."""
    found = relationship.found
    status_class = "relationship-found" if found else "relationship-missing"
    status_icon = "✓" if found else "✗"
    
    st.markdown(f"""
    <div class="relationship-card {status_class}">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h3 style="margin: 0;">{status_icon} {name}</h3>
                <p style="margin: 0.25rem 0 0 0; opacity: 0.9; font-size: 0.9rem;">{description}</p>
            </div>
            <div style="text-align: right;">
                {render_confidence_badge(relationship.confidence)}
            </div>
        </div>
        <div style="margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid rgba(255,255,255,0.2);">
            <strong>Value:</strong> {relationship.display_value}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_datapoint_item(datapoint: Datapoint):
    """Render a single datapoint row."""
    conf_class = datapoint.confidence_level.value
    conf_color = "#11998e" if conf_class == "high" else "#f59e0b" if conf_class == "medium" else "#eb3349"
    conf_icon = "✓" if conf_class == "high" else "⚠️" if conf_class == "medium" else "✗"
    
    st.markdown(f"""
    <div class="datapoint-row">
        <div style="display: flex; justify-content: space-between; align-items: start;">
            <div>
                <strong>#{datapoint.id}</strong> {datapoint.aligned_datapoint}
                <br>
                <span style="color: #666; font-size: 0.85rem;">
                    {datapoint.impact_category} → {datapoint.impact_subcategory}
                </span>
            </div>
            <div style="text-align: right;">
                <span style="font-size: 1.2rem; font-weight: bold;">{datapoint.value}</span>
                <span style="color: #666;"> {datapoint.unit or ''}</span>
                <br>
                <span style="color: {conf_color};">{conf_icon} {datapoint.confidence:.0%}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def main():
    """Main application."""
    
    # Header
    st.markdown('<p class="main-header">🏢 ACER Visualizer</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Building Passport Processor — Extract structured data from equipment documents</p>', unsafe_allow_html=True)
    
    # Sidebar for navigation (reordered per user request)
    with st.sidebar:
        st.header("Navigation")
        page = st.radio(
            "Go to",
            ["⚙️ Settings", "📤 Upload PDF", "🕸️ Graph View", "📊 Relationship Cards", "📄 Sample Documents"],
            label_visibility="collapsed",
            key="nav_selection"
        )
        
        st.divider()
        
        st.subheader("About ACER")
        st.markdown("""
        **ACER** = Asset Carbon and Energy Reporting
        
        Every document maps to **6 relationships**:
        1. hasEquipment
        2. hasAssetType  
        3. hasDatapoint
        4. hasMetadata
        5. hasImpactCategory
        6. hasRequirementSource
        """)
    
    if page == "⚙️ Settings":
        render_settings()
    elif page == "📤 Upload PDF":
        render_upload_pdf()
    elif page == "🕸️ Graph View":
        render_graph_network_view()
    elif page == "📊 Relationship Cards":
        render_graph_view()
    elif page == "📄 Sample Documents":
        render_sample_documents()


def render_graph_view():
    """Main ACER Graph visualization view."""
    
    # Check for uploaded graph
    if 'current_graph' not in st.session_state:
        st.session_state.current_graph = None
    
    # Auto-load graph from last extraction if available and not yet loaded
    has_last_extraction = 'last_extraction' in st.session_state and st.session_state.last_extraction is not None
    if has_last_extraction and not st.session_state.current_graph:
        st.session_state.current_graph = build_graph_from_extraction(
            st.session_state.last_extraction,
            st.session_state.last_extraction_filename
        )
    
    # Toolbar
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    
    with col1:
        st.subheader("ACER Graph")
        if st.session_state.current_graph:
            st.caption(f"Document: {st.session_state.current_graph.document_name}")
        elif has_last_extraction:
            st.caption(f"Last extraction: {st.session_state.last_extraction_filename}")
        else:
            st.caption("No document loaded — select a sample or upload")
    
    with col2:
        if st.button("📊 Load Sample", use_container_width=True):
            st.session_state.current_graph = create_carrier_rtu_graph()
            st.rerun()
    
    with col3:
        if st.button("📄 Simple Demo", use_container_width=True):
            st.session_state.current_graph = create_simple_example_graph()
            st.rerun()
    
    with col4:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.current_graph = None
            st.rerun()
    
    st.divider()
    
    # Use sample if no graph loaded
    graph = st.session_state.current_graph or create_carrier_rtu_graph()
    
    # Summary metrics
    st.subheader("Summary")
    
    m1, m2, m3, m4, m5 = st.columns(5)
    
    with m1:
        st.metric(
            "Relationships Found",
            f"{graph.relationships_found}/6",
            delta=f"{graph.relationships_missing} missing" if graph.relationships_missing else None,
            delta_color="off"
        )
    
    with m2:
        st.metric(
            "Datapoints",
            graph.total_datapoints,
        )
    
    with m3:
        avg_conf = graph.average_confidence
        st.metric(
            "Avg Confidence",
            f"{avg_conf:.0%}",
            delta="High" if avg_conf >= 0.85 else "Medium" if avg_conf >= 0.60 else "Low",
            delta_color="normal" if avg_conf >= 0.85 else "off"
        )
    
    with m4:
        breakdown = graph.confidence_breakdown
        st.metric("High Conf", breakdown['high'])
    
    with m5:
        st.metric("Review Needed", breakdown['medium'] + breakdown['low'])
    
    st.divider()
    
    # Display document name
    st.markdown(f"### {graph.document_name}")
    
    # Two columns for relationships
    col_left, col_right = st.columns(2)
    
    with col_left:
        # Primary relationships (usually found)
        st.markdown("#### ✓ Extracted from Document")
        
        for name in ['hasMetadata', 'hasEquipment', 'hasAssetType']:
            rel = graph.get_relationship(name)
            if rel:
                render_relationship_card(name, rel, graph.RELATIONSHIP_DESCRIPTIONS.get(name, ""))
                st.markdown("")  # Spacing
    
    with col_right:
        # hasDatapoint (the big one)
        st.markdown("#### 📊 Extracted Datapoints")
        
        if graph.has_datapoint and graph.has_datapoint.found:
            # Show summary first
            dp = graph.has_datapoint
            avg_conf = sum(d.confidence for d in dp.value) / len(dp.value) if dp.value else 0
            
            st.markdown(f"""
            <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
                <strong>{len(dp.value)} datapoints</strong> extracted
                <br>
                <span style="color: #666;">Average confidence: {avg_conf:.0%}</span>
            </div>
            """, unsafe_allow_html=True)
            
            # Expandable datapoint list
            with st.expander("View all datapoints", expanded=True):
                # Group by impact category
                by_category: dict = {}
                for d in dp.value:
                    cat = d.impact_category
                    if cat not in by_category:
                        by_category[cat] = []
                    by_category[cat].append(d)
                
                for category, datapoints in by_category.items():
                    with st.expander(f"📁 {category} ({len(datapoints)})", expanded=False):
                        for d in datapoints:
                            render_datapoint_item(d)
        else:
            st.info("No datapoints extracted")
    
    # Missing relationships - only show if actually missing
    missing_rels = []
    
    if graph.has_impact_category and not graph.has_impact_category.found:
        missing_rels.append(("hasImpactCategory", graph.has_impact_category))
    
    if graph.has_requirement_source and not graph.has_requirement_source.found:
        missing_rels.append(("hasRequirementSource", graph.has_requirement_source))
    
    if missing_rels:
        st.divider()
        st.markdown("#### ✗ Missing Relationships")
        
        cols = st.columns(len(missing_rels)) if len(missing_rels) < 3 else st.columns(2)
        
        for i, (name, rel) in enumerate(missing_rels):
            with cols[i]:
                with st.container():
                    if name == "hasImpactCategory":
                        desc = "Sustainability dimension"
                    else:
                        desc = "Compliance standards"
                    
                    st.markdown(f"""
                    <div class="relationship-card relationship-missing">
                        <h3>✗ {name}</h3>
                        <p style="opacity: 0.9; margin: 0;">{desc}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if rel and rel.suggested:
                        suggestion = rel.suggested if isinstance(rel.suggested, str) else ', '.join(rel.suggested)
                        st.caption(f"💡 Suggested: {suggestion}")
                    
                    if st.button(f"Add {name}", key=f"add_{name}"):
                        st.info(f"{name} selection modal would open here")
    
    # Export section
    st.divider()
    st.subheader("Export")
    
    exp_col1, exp_col2, exp_col3 = st.columns(3)
    
    with exp_col1:
        json_str = json.dumps(graph.to_dict(), indent=2)
        st.download_button(
            "📥 Download JSON",
            data=json_str,
            file_name=f"{graph.document_name}.acer.json",
            mime="application/json",
            use_container_width=True
        )
    
    with exp_col2:
        md_str = graph.to_markdown()
        st.download_button(
            "📥 Download Markdown",
            data=md_str,
            file_name=f"{graph.document_name}.md",
            mime="text/markdown",
            use_container_width=True
        )
    
    with exp_col3:
        if st.button("📋 Copy JSON", use_container_width=True):
            st.code(json_str, language="json")
            st.success("JSON displayed above — copy manually")


def render_upload_pdf():
    """PDF Upload and extraction view."""
    st.subheader("Upload PDF Document")
    
    # Check OpenRouter configuration
    openrouter_enabled = st.session_state.get('openrouter_enabled', False)
    openrouter_api_key = st.session_state.get('openrouter_api_key', '')
    openrouter_model = st.session_state.get('openrouter_model', RECOMMENDED_MODELS[0])
    
    if openrouter_enabled:
        st.info("""
        **OpenRouter LLM Extraction Enabled**
        - Model: {} 
        - Configure in Settings to change model or disable
        
        Upload a PDF to extract ACER relationships using the configured LLM.
        """.format(get_display_name(openrouter_model)))
    else:
        st.markdown("""
        Upload a building equipment specification PDF to extract ACER relationships.
        
        **To enable real LLM extraction:**
        1. Go to **⚙️ Settings**
        2. Enter your OpenRouter API key
        3. Select a model and enable LLM extraction
        
        Currently running in demo mode with mock data.
        """)
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=["pdf"],
        help="Max file size: 50MB",
        max_size=50
    )
    
    if uploaded_file:
        st.divider()
        
        # Show file info
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Filename", uploaded_file.name)
        
        with col2:
            size_kb = len(uploaded_file.getvalue()) / 1024
            st.metric("Size", f"{size_kb:.1f} KB")
        
        with col3:
            st.metric("Type", uploaded_file.type or "application/pdf")
        
        st.divider()
        
        # Cost preview
        if openrouter_enabled and openrouter_api_key:
            model = openrouter_model
            input_cost, output_cost = MODEL_PRICING.get(model, (0.25, 1.25))
            pages_est = 5  # Default estimate, actual count shown after extraction
            tokens_in = pages_est * 2000
            tokens_out = min(tokens_in // 2, 1500)
            cost_est = (tokens_in / 1e6) * input_cost + (tokens_out / 1e6) * output_cost
            
            cost_col1, cost_col2, cost_col3 = st.columns(3)
            with cost_col1:
                st.metric("Est. Pages", "~5")
            with cost_col2:
                st.metric("Tokens (in)", f"{tokens_in:,}")
            with cost_col3:
                if cost_est == 0:
                    st.metric("Est. Cost", "FREE ✓")
                else:
                    st.metric("Est. Cost", f"${cost_est:.4f}")
        
        # Extraction button
        if st.button("🔍 Extract ACER Relationships", type="primary", use_container_width=True):
            with st.spinner("Extracting data from document..."):
                try:
                    # Read PDF text using pdfplumber
                    
                    pdf_bytes = uploaded_file.getvalue()
                    document_text = ""
                    page_count = 0
                    
                    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                        page_count = len(pdf.pages)
                        for page in pdf.pages:
                            text = page.extract_text()
                            if text:
                                document_text += text + "\n\n"
                    
                    # Check if OpenRouter is configured
                    if openrouter_enabled and openrouter_api_key:
                        # Use OpenRouter for extraction
                        st.info(f"Using {get_display_name(openrouter_model)} for extraction...")
                        
                        llm_result = extract_with_openrouter(
                            api_key=openrouter_api_key,
                            model_id=openrouter_model,
                            document_text=document_text[:15000] if document_text else "",  # Limit text length
                            filename=uploaded_file.name
                        )
                        
                        # Use LLM result directly (raw dict), guard against None
                        extraction = llm_result if isinstance(llm_result, dict) else {}
                        if not extraction:
                            st.error("LLM returned no data. Please try again or use demo mode.")
                            st.stop()
                    else:
                        # Fall back to mock extraction
                        sample_text = f"""
                        CARRIER 40RUS 060-8 ROOFTOP UNIT
                        
                        SPECIFICATIONS:
                        Cooling Capacity: 50 tons
                        EER: 11.5
                        IEER: 13.0
                        Airflow: 2,000 CFM
                        Unit Weight: 850 lbs
                        
                        COMPLIANCE:
                        Meets ASHRAE 90.1-2019 standards
                        Energy Star certified
                        LEED compliant
                        
                        MANUFACTURER: Carrier Corporation
                        MODEL: 40RUS 060-8
                        """
                        extraction = extract_from_text(uploaded_file.name, sample_text)
                        extraction['llm_extraction'] = False
                    
                    # Build a simple ACER graph from extraction
                    from models import create_carrier_rtu_graph
                    
                    # Ensure extraction is a valid dict before displaying
                    if not isinstance(extraction, dict):
                        extraction = {}
                    
                    # Show extraction results
                    extraction_type = "LLM" if extraction.get('llm_extraction') else "Demo"
                    st.success(f"Extraction complete! ({extraction_type} mode)")
                    
                    st.markdown("### Extracted Data")
                    
                    # Metadata (handle both demo dataclass and LLM dict formats)
                    meta = extraction.get('metadata') or extraction.get('hasMetadata', {}) or {}
                    meta_filename = uploaded_file.name
                    meta_pages = "?"
                    
                    if isinstance(meta, dict):
                        meta_filename = meta.get('filename', uploaded_file.name) or uploaded_file.name
                        pages_val = meta.get('pageCount') or meta.get('page_count')
                        meta_pages = str(pages_val) if pages_val is not None else "?"
                    elif hasattr(meta, 'filename'):
                        meta_filename = meta.filename or uploaded_file.name
                        meta_pages = str(meta.page_count) if meta.page_count else "?"
                    
                    if meta:
                        st.markdown("""
                        #### Document Metadata
                        """)
                        st.table({
                            "Property": ["Filename", "Pages"],
                            "Value": [meta_filename, meta_pages]
                        })
                    
                    # Equipment detected
                    equip_data = extraction.get('hasEquipment', {}) or {}
                    equip_name = ""
                    equip_conf = 0.5
                    equip_manuf = "Unknown"
                    
                    if isinstance(equip_data, dict):
                        equip_name = equip_data.get('name', '') or ''
                        equip_conf = equip_data.get('confidence', 0.5) or 0.5
                        equip_manuf = equip_data.get('manufacturer', 'Unknown') or 'Unknown'
                    elif hasattr(equip_data, 'name'):
                        equip_name = getattr(equip_data, 'name', '') or ''
                        equip_conf = getattr(equip_data, 'confidence', 0.5) or 0.5
                        equip_manuf = getattr(equip_data, 'manufacturer', 'Unknown') or 'Unknown'
                    
                    if equip_name:
                        conf_emoji = "✅" if equip_conf >= 0.85 else "⚠️"
                        st.markdown(f"""
                        #### Equipment Detected {conf_emoji}
                        - **Name:** {equip_name}
                        - **Manufacturer:** {equip_manuf}
                        - **Confidence:** {equip_conf:.0%}
                        """)
                    
                    # Datapoints found
                    dp_list = extraction.get('hasDatapoint', []) or []
                    if dp_list and isinstance(dp_list, list):
                        st.markdown(f"""
                        #### Data Points Found ({len(dp_list)})
                        """)
                        
                        dp_data = []
                        for dp in dp_list:
                            if isinstance(dp, dict):
                                conf = dp.get('confidence', 0.5) or 0.5
                                conf_class = "✓" if conf >= 0.85 else "⚠️" if conf >= 0.6 else "✗"
                                cat = dp.get('impact_category', '') or ''
                                dp_name = dp.get('aligned_datapoint', 'Unknown') or 'Unknown'
                                val = dp.get('value', '') or ''
                                unit = dp.get('unit', '') or ''
                            elif hasattr(dp, 'aligned_datapoint'):
                                conf = getattr(dp, 'confidence', 0.5) or 0.5
                                conf_class = "✓" if conf >= 0.85 else "⚠️" if conf >= 0.6 else "✗"
                                cat = getattr(dp, 'impact_category', '') or ''
                                dp_name = getattr(dp, 'aligned_datapoint', 'Unknown') or 'Unknown'
                                val = getattr(dp, 'value', '') or ''
                                unit = getattr(dp, 'unit', '') or ''
                            else:
                                continue
                            
                            dp_data.append({
                                "Category": (cat[:20] + "..." if len(cat) > 20 else cat),
                                "Datapoint": (dp_name[:30] + "..." if len(dp_name) > 30 else dp_name),
                                "Value": f"{val} {unit}".strip(),
                                "Conf": conf_class
                            })
                        
                        if dp_data:
                            st.dataframe(dp_data, use_container_width=True)
                    
                    # Requirements
                    req_data = extraction.get('hasRequirementSource', {}) or {}
                    standards = []
                    
                    if isinstance(req_data, dict):
                        std_val = req_data.get('standards', [])
                        if isinstance(std_val, list):
                            standards = std_val
                    elif hasattr(req_data, 'standards'):
                        std_val = getattr(req_data, 'standards', [])
                        if isinstance(std_val, list):
                            standards = std_val
                    
                    if standards:
                        st.markdown(f"""
                        #### Compliance Standards ({len(standards)})
                        """)
                        for std in standards:
                            if std:
                                st.markdown(f"- **{std}:** Found in document (LLM extraction)")
                    
                    st.divider()
                    
                    # Store extraction in session state for persistence
                    st.session_state.last_extraction = extraction
                    st.session_state.last_extraction_filename = uploaded_file.name
                    
                    # Action buttons
                    col_load, col_view = st.columns(2)
                    
                    with col_load:
                        if st.button("📊 Load as ACER Graph", type="primary", use_container_width=True):
                            # Build actual graph from extraction
                            graph = build_graph_from_extraction(extraction, uploaded_file.name)
                            st.session_state.current_graph = graph
                            st.success("Graph loaded from extraction!")
                            st.rerun()
                    
                    with col_view:
                        if st.button("🔍 View Full Results", use_container_width=True):
                            # Build and switch to graph view
                            graph = build_graph_from_extraction(extraction, uploaded_file.name)
                            st.session_state.current_graph = graph
                            # Navigate by switching the sidebar selection
                            st.session_state['nav_selection'] = "🕸️ Graph View"
                            st.rerun()
                
                except Exception as e:
                    st.error(f"Error processing PDF: {str(e)}")
                    st.info("In production, this would connect to Azure Document Intelligence or your PDF parsing pipeline.")
    
    else:
        # Show upload instructions
        st.info("👆 Upload a PDF file to begin extraction")
        
        with st.expander("📋 Supported Document Types"):
            st.markdown("""
            - Equipment specification sheets
            - Product data sheets
            - Technical manuals
            - Building permits
            - Compliance certificates
            
            **Extraction Capabilities:**
            - Equipment identification
            - Technical specifications
            - Performance ratings
            - Compliance standards
            """)


def render_sample_documents():
    """Sample documents browser."""
    st.subheader("Sample Documents")
    
    samples = {
        "Carrier 40RUS 060-8": create_carrier_rtu_graph,
        "Trane CVHE 450": create_trane_chiller_graph,
        "Daikin VRV IV": create_daikin_vrv_graph,
        "Simple Demo": create_simple_example_graph
    }
    
    for name, func in samples.items():
        with st.expander(f"📄 {name}"):
            if st.button(f"Load {name}", key=f"load_{name}"):
                st.session_state.current_graph = func()
                st.success(f"Loaded {name}")
                st.rerun()
            
            graph = func()
            
            # Quick stats
            st.markdown(f"""
            **Relationships:** {graph.relationships_found}/6 found  
            **Datapoints:** {graph.total_datapoints} extracted  
            **Avg Confidence:** {graph.average_confidence:.0%}
            """)


def render_graph_network_view():
    """Interactive Obsidian-style graph visualization."""
    
    # Check for uploaded graph
    if 'current_graph' not in st.session_state:
        st.session_state.current_graph = None
    
    # Auto-load graph from last extraction if available and not yet loaded
    has_last_extraction = 'last_extraction' in st.session_state and st.session_state.last_extraction is not None
    if has_last_extraction and not st.session_state.current_graph:
        st.session_state.current_graph = build_graph_from_extraction(
            st.session_state.last_extraction,
            st.session_state.last_extraction_filename
        )
    
    # Toolbar
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("ACER Graph Network")
        if st.session_state.current_graph:
            st.caption(f"Document: {st.session_state.current_graph.document_name}")
        elif has_last_extraction:
            st.caption(f"Last extraction: {st.session_state.last_extraction_filename}")
        else:
            st.caption("No document loaded")
    
    with col2:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.current_graph = None
            st.rerun()
    
    st.divider()
    
    # If no graph, use sample
    if not st.session_state.current_graph:
        if st.button("📊 Load Sample", type="primary"):
            st.session_state.current_graph = create_carrier_rtu_graph()
            st.rerun()
            return
        st.info("Upload a PDF and click 'Load as ACER Graph' to see results here.")
        return
    
    # Get graph
    graph = st.session_state.current_graph
    
    # Create and render the Obsidian-style graph
    with st.spinner("Generating graph visualization..."):
        try:
            render_obsidian_graph(graph, height="650px")
            
            # Confidence info
            render_extraction_vs_alignment_info()
            
        except Exception as e:
            st.error(f"Graph visualization error: {str(e)}")
            st.info("Try the Relationship Cards view instead.")


def render_settings():
    """Settings page with OpenRouter configuration."""
    st.subheader("Settings")
    
    # Initialize session state defaults
    if 'openrouter_api_key' not in st.session_state:
        st.session_state['openrouter_api_key'] = ""
    if 'openrouter_model' not in st.session_state:
        st.session_state['openrouter_model'] = RECOMMENDED_MODELS[0]
    if 'openrouter_enabled' not in st.session_state:
        st.session_state['openrouter_enabled'] = False
    
    # OpenRouter Configuration Section
    st.markdown("""
    ## OpenRouter Configuration
    
    Use your own OpenRouter API key to enable real LLM-powered PDF extraction.
    This allows anyone to test the app without needing access to our systems.
    """)
    
    # API Key input
    col1, col2 = st.columns([3, 1])
    
    with col1:
        api_key = st.text_input(
            "OpenRouter API Key",
            value=st.session_state.get('openrouter_api_key', ''),
            type="password",
            help="Get your API key at openrouter.ai/keys"
        )
    
    with col2:
        st.write("")  # Spacing
        if st.button("🔑 Validate Key", use_container_width=True):
            if api_key and validate_api_key(api_key):
                st.session_state['openrouter_api_key'] = api_key
                st.session_state['openrouter_enabled'] = True
                st.success("API key validated!")
            else:
                st.error("Invalid API key")
    
    st.caption("Don't have a key? Get one at [openrouter.ai](https://openrouter.ai/keys)")
    
    st.divider()
    
    # Model selection
    st.markdown("### Model Selection")
    
    model_options = []
    selected_model = st.session_state.get('openrouter_model', RECOMMENDED_MODELS[0])
    
    # Use recommended models if API key is set
    if api_key and validate_api_key(api_key):
        with st.spinner("Fetching available models..."):
            available_models = fetch_available_models(api_key)
            
        if available_models:
            model_options = [m['id'] for m in available_models]
            selected_model = st.selectbox(
                "Choose a model",
                options=model_options,
                index=model_options.index(selected_model) if selected_model in model_options else 0,
                format_func=get_display_name,
                help="Select the LLM model for PDF extraction"
            )
        else:
            st.warning("Could not fetch models. Using recommended models.")
            model_options = RECOMMENDED_MODELS
            selected_model = st.selectbox(
                "Choose a model",
                options=model_options,
                index=model_options.index(selected_model) if selected_model in model_options else 0,
                format_func=get_display_name,
                help="Select the LLM model for PDF extraction"
            )
    else:
        model_options = RECOMMENDED_MODELS
        selected_model = st.selectbox(
            "Choose a model",
            options=model_options,
            index=model_options.index(selected_model) if selected_model in model_options else 0,
            format_func=get_display_name,
            help="Enter and validate an API key to use custom models"
        )
    
    # Save model selection
    st.session_state['openrouter_model'] = selected_model
    
    # Dynamic cost estimator
    st.markdown("### Cost Estimator")
    
    # Get pricing for selected model (defaults to Claude Haiku)
    input_cost, output_cost = MODEL_PRICING.get(selected_model, (0.25, 1.25))
    
    # Estimate tokens based on pages (rough: ~2000 tokens per page)
    estimated_pages = st.slider("Estimated pages in PDF", 1, 50, 5, help="Slide to match your document")
    tokens_per_page = 2000
    input_tokens = estimated_pages * tokens_per_page
    output_tokens = min(input_tokens // 2, 1500)  # Output is typically smaller
    
    # Calculate costs
    input_cost_actual = (input_tokens / 1_000_000) * input_cost
    output_cost_actual = (output_tokens / 1_000_000) * output_cost
    total_cost = input_cost_actual + output_cost_actual
    
    # Display with color coding
    cost_col1, cost_col2, cost_col3 = st.columns(3)
    
    with cost_col1:
        st.metric("Input Tokens", f"{input_tokens:,}")
    with cost_col2:
        st.metric("Output Tokens", f"{output_tokens:,}")
    with cost_col3:
        if total_cost == 0:
            st.metric("Est. Cost", "FREE ✓", delta="Open source model")
        else:
            st.metric("Est. Cost", f"${total_cost:.4f}", delta=f"${input_cost_actual:.4f} in + ${output_cost_actual:.4f} out")
    
    if total_cost > 0:
        st.caption(f"Prices: ${input_cost:.2f}/M tokens in, ${output_cost:.2f}/M tokens out")
    else:
        st.caption("This model is free on OpenRouter (open source)")
    
    st.divider()
    
    # Enable/disable toggle
    enable_llm = st.toggle(
        "Enable LLM Extraction",
        value=st.session_state.get('openrouter_enabled', False),
        help="When enabled, PDFs will be extracted using the configured LLM"
    )
    st.session_state['openrouter_enabled'] = enable_llm and bool(api_key)
    
    if enable_llm and not api_key:
        st.warning("Enter and validate an API key to enable LLM extraction")
    
    # Current status
    status_col1, status_col2 = st.columns(2)
    
    with status_col1:
        st.metric("LLM Extraction", "Enabled" if st.session_state['openrouter_enabled'] else "Disabled")
    
    with status_col2:
        st.metric("Model", get_display_name(selected_model).split(" (")[0])
    
    st.divider()
    
    # Other settings
    with st.expander("Other Settings"):
        st.markdown("""
        ### PDF Processing
        - Max file size: 50MB
        - Supported formats: PDF
        
        ### Confidence Thresholds
        - High: ≥ 85%
        - Medium: 60-84%
        - Low: < 60%
        
        ### Ontology
        - Version: 0.0.1
        - Datapoints: 80+
        """)


if __name__ == "__main__":
    main()
