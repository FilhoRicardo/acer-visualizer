"""
ACER Visualizer - Building Passport Processor
Streamlit Web Application

Run with: streamlit run src/app.py
"""
import streamlit as st
import json
from datetime import datetime

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


# Page config
st.set_page_config(
    page_title="ACER Visualizer",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
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
    
    # Sidebar for navigation
    with st.sidebar:
        st.header("Navigation")
        page = st.radio(
            "Go to",
            ["🕸️ Graph View", "📊 Relationship Cards", "📄 Sample Documents", "📤 Upload PDF", "⚙️ Settings"],
            label_visibility="collapsed"
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
    
    if page == "🕸️ Graph View":
        render_graph_network_view()
    elif page == "📊 Relationship Cards":
        render_graph_view()
    elif page == "📄 Sample Documents":
        render_sample_documents()
    elif page == "📤 Upload PDF":
        render_upload_pdf()
    else:
        render_settings()


def render_graph_view():
    """Main ACER Graph visualization view."""
    
    # Check for uploaded graph or use sample
    if 'current_graph' not in st.session_state:
        st.session_state.current_graph = None
    
    # Toolbar
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    
    with col1:
        st.subheader("ACER Graph")
        if st.session_state.current_graph:
            st.caption(f"Document: {st.session_state.current_graph.document_name}")
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
    
    # Missing relationships
    st.divider()
    st.markdown("#### ✗ Missing Relationships")
    
    col_m1, col_m2 = st.columns(2)
    
    with col_m1:
        rel = graph.has_impact_category
        with st.container():
            st.markdown(f"""
            <div class="relationship-card relationship-missing">
                <h3>✗ hasImpactCategory</h3>
                <p style="opacity: 0.9; margin: 0;">Sustainability dimension</p>
            </div>
            """, unsafe_allow_html=True)
            
            if rel and rel.suggested:
                st.caption(f"💡 Suggested: {rel.suggested}")
            
            if st.button("Add Impact Category", key="add_impact"):
                st.info("Impact category selection modal would open here")
    
    with col_m2:
        rel = graph.has_requirement_source
        with st.container():
            st.markdown(f"""
            <div class="relationship-card relationship-missing">
                <h3>✗ hasRequirementSource</h3>
                <p style="opacity: 0.9; margin: 0;">Compliance standards</p>
            </div>
            """, unsafe_allow_html=True)
            
            if rel and rel.suggested:
                st.caption(f"💡 Suggested: {', '.join(rel.suggested) if isinstance(rel.suggested, list) else rel.suggested}")
            
            if st.button("Add Requirement Source", key="add_req"):
                st.info("Requirement source selection modal would open here")
    
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
        help="Max file size: 50MB"
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
        
        # Extraction button
        if st.button("🔍 Extract ACER Relationships", type="primary", use_container_width=True):
            with st.spinner("Extracting data from document..."):
                try:
                    # Read PDF text using pdfplumber
                    import pdfplumber
                    import io
                    
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
                            document_text=document_text[:15000],  # Limit text length
                            filename=uploaded_file.name
                        )
                        
                        # Convert LLM result to extraction format
                        extraction = {
                            'metadata': type('obj', (object,), {
                                'filename': uploaded_file.name,
                                'file_size_kb': size_kb,
                                'page_count': page_count,
                                'extracted_at': datetime.now().isoformat()
                            })(),
                            'equipment': type('obj', (object,), {
                                'name': llm_result.get('hasEquipment', {}).get('name', 'Unknown'),
                                'manufacturer': llm_result.get('hasEquipment', {}).get('manufacturer', 'Unknown'),
                                'confidence': llm_result.get('hasEquipment', {}).get('confidence', 0.5)
                            })() if llm_result.get('hasEquipment') else None,
                            'datapoints': [
                                type('obj', (object,), {
                                    'aligned_datapoint': dp.get('aligned_datapoint', 'Unknown'),
                                    'value': dp.get('value', ''),
                                    'unit': dp.get('unit', ''),
                                    'confidence': dp.get('confidence', 0.5),
                                    'source_page': dp.get('source_page', '?'),
                                    'impact_category': dp.get('impact_category', ''),
                                    'impact_subcategory': dp.get('impact_subcategory', '')
                                })
                                for dp in llm_result.get('hasDatapoint', [])
                            ],
                            'requirements': [
                                type('obj', (object,), {
                                    'standard_name': std,
                                    'requirement_text': f"Found in document (LLM extraction)"
                                })
                                for std in llm_result.get('hasRequirementSource', {}).get('standards', [])
                            ],
                            'llm_extraction': True
                        }
                        
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
                    
                    # Show extraction results
                    extraction_type = "LLM" if extraction.get('llm_extraction') else "Demo"
                    st.success(f"Extraction complete! ({extraction_type} mode)")
                    
                    st.markdown("### Extracted Data")
                    
                    # Metadata
                    if extraction['metadata']:
                        meta = extraction['metadata']
                        st.markdown("""
                        #### Document Metadata
                        | Property | Value |
                        |----------|-------|
                        """)
                        st.table({
                            "Property": ["Filename", "Size", "Pages", "Extracted At"],
                            "Value": [meta.filename, f"{meta.file_size_kb:.1f} KB", 
                                     str(meta.page_count or "Unknown"), meta.extracted_at]
                        })
                    
                    # Equipment
                    if extraction['equipment']:
                        equip = extraction['equipment']
                        conf_emoji = "✓" if equip.confidence >= 0.85 else "⚠️" if equip.confidence >= 0.6 else "✗"
                        st.markdown(f"""
                        #### Equipment Detected {conf_emoji}
                        - **Name:** {equip.name}
                        - **Manufacturer:** {equip.manufacturer}
                        - **Confidence:** {equip.confidence:.0%}
                        """)
                    
                    # Datapoints found
                    if extraction['datapoints']:
                        st.markdown(f"""
                        #### Data Points Found ({len(extraction['datapoints'])})
                        """)
                        
                        dp_data = []
                        for dp in extraction['datapoints']:
                            conf_class = "✓" if dp.confidence >= 0.85 else "⚠️" if dp.confidence >= 0.6 else "✗"
                            dp_data.append({
                                "Category": dp.impact_category[:20] + "..." if len(dp.impact_category) > 20 else dp.impact_category,
                                "Datapoint": dp.aligned_datapoint[:30] + "..." if len(dp.aligned_datapoint) > 30 else dp.aligned_datapoint,
                                "Value": f"{dp.value} {dp.unit}",
                                "Conf": conf_class
                            })
                        
                        st.dataframe(dp_data, use_container_width=True)
                    
                    # Requirements
                    if extraction['requirements']:
                        st.markdown(f"""
                        #### Compliance Standards ({len(extraction['requirements'])})
                        """)
                        for req in extraction['requirements']:
                            st.markdown(f"- **{req.standard_name}:** {req.requirement_text}")
                    
                    st.divider()
                    
                    # Action buttons
                    col_load, col_discard = st.columns(2)
                    
                    with col_load:
                        if st.button("📊 Load as ACER Graph", type="primary", use_container_width=True):
                            st.session_state.current_graph = create_carrier_rtu_graph()
                            st.success("Loaded sample ACER graph")
                            st.rerun()
                    
                    with col_discard:
                        if st.button("🗑️ Discard", use_container_width=True):
                            st.info("Upload a new file to start over")
                
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
    
    # Check for uploaded graph or use sample
    if 'current_graph' not in st.session_state:
        st.session_state.current_graph = None
    
    # Toolbar
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("ACER Graph Network")
        if st.session_state.current_graph:
            st.caption(f"Document: {st.session_state.current_graph.document_name}")
        else:
            st.caption("Loading sample data...")
            st.session_state.current_graph = create_carrier_rtu_graph()
    
    with col2:
        if st.button("Refresh", use_container_width=True):
            st.rerun()
    
    st.divider()
    
    # Get graph
    graph = st.session_state.current_graph
    if not graph:
        st.info("No graph loaded. Select a sample document or upload a PDF.")
        return
    
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
    
    # Cost estimates
    st.markdown("""
    ### Cost Estimates
    
    | Model | Input | Output | Notes |
    |-------|-------|--------|-------|
    | Claude 3 Haiku | $0.25/M | $1.25/M | Fast, good quality |
    | Llama 3 8B | Free | Free | Open source |
    | Mistral 7B | Free | Free | Open source |
    | GPT-4o Mini | $0.15/M | $0.60/M | Cheap, capable |
    | DeepSeek V2 | $0.28/M | $1.10/M | Good value |
    
    *Prices are approximate from OpenRouter*
    """)
    
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
