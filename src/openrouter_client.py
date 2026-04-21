"""
OpenRouter API Client for ACER Visualizer

Allows users to configure their own OpenRouter API key and select from
available models for PDF extraction.
"""
import json
import requests
from typing import Optional
import streamlit as st


# OpenRouter API configuration
OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"
OPENROUTER_MODELS_URL = f"{OPENROUTER_API_BASE}/models"

# Popular models for document extraction (curated for quality/speed/cost balance)
RECOMMENDED_MODELS = [
    "anthropic/claude-3-haiku",
    "anthropic/claude-3-sonnet",
    "meta-llama/llama-3-8b-instruct",
    "mistralai/mistral-7b-instruct",
    "openai/gpt-4o-mini",
    "google/gemini-pro-1.5",
    "deepseek/deepseek-chat-v2",
]

# Model display names for better UX
MODEL_DISPLAY_NAMES = {
    "anthropic/claude-3-haiku": "Claude 3 Haiku (Fast, Cheap)",
    "anthropic/claude-3-sonnet": "Claude 3 Sonnet (Balanced)",
    "meta-llama/llama-3-8b-instruct": "Llama 3 8B (Open Source)",
    "mistralai/mistral-7b-instruct": "Mistral 7B (Open Source)",
    "openai/gpt-4o-mini": "GPT-4o Mini (Fast)",
    "google/gemini-pro-1.5": "Gemini Pro 1.5 (Long Context)",
    "deepseek/deepseek-chat-v2": "DeepSeek V2 (Cheap)",
}


def get_display_name(model_id: str) -> str:
    """Get human-readable model name."""
    return MODEL_DISPLAY_NAMES.get(model_id, model_id)


def fetch_available_models(api_key: str) -> list[dict]:
    """
    Fetch available models from OpenRouter API.
    
    Returns list of dicts with 'id' and 'name' keys.
    """
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://acer-visualizer.app",
            "X-Title": "ACER Visualizer",
        }
        
        response = requests.get(
            OPENROUTER_MODELS_URL,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        models = data.get("data", [])
        
        # Return list of (id, name) tuples sorted by popularity
        # Filter: include models that are NOT GPT OR are Claude (avoid cheap/noisy GPT variants, keep Claude family)
        return [
            {"id": m["id"], "name": m.get("name", m["id"])}
            for m in models
            if m.get("id") and ("gpt" not in m.get("id", "").lower() or "claude" in m.get("id", "").lower())
        ][:50]  # Limit to top 50 to avoid dropdown overflow
        
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch models: {str(e)}")
        return []


def extract_with_openrouter(
    api_key: str,
    model_id: str,
    document_text: str,
    page_texts: list[str],
    filename: str,
) -> dict:
    """
    Extract ACER relationships from document text using OpenRouter.
    
    Args:
        api_key: OpenRouter API key
        model_id: Model ID (e.g., 'anthropic/claude-3-haiku')
        document_text: Combined extracted text from PDF
        page_texts: List of text per page, for line-number tracking
        filename: Original filename for context
    
    Returns:
        Dict with extracted ACER data
    """
    # Build the extraction prompt
    system_prompt = """You are an expert at extracting structured data from building equipment specification documents.

Extract the following ACER (Asset Carbon and Energy Reporting) relationships from the document:

1. **hasEquipment**: What equipment does this document describe? (manufacturer, model, full name)
2. **hasAssetType**: What category of equipment? (e.g., Rooftop Unit, Chiller, Boiler, Heat Pump)
3. **hasDatapoint**: Extract ALL measurable data points with:
   - aligned_datapoint: The ACER datapoint name (e.g., "Primary Energy Demand", "COP", "Capacity")
   - value: The extracted value
   - unit: The unit of measurement
   - impact_category: Climate Health, Asset Integrity, or Human Health
   - impact_subcategory: Energy, Greenhouse Gas Emissions, Physical Characteristics, etc.
   - confidence: How confident are you? (0.0-1.0)
   - source_page: Which page number this was found on
   - source_line: The approximate line number on that page (count lines within the page)
   - source_location: Table name, section name, or specific location description

4. **hasMetadata**: Document metadata (page count if known, file info)
5. **hasImpactCategory**: Suggested sustainability dimension if not explicit
6. **hasRequirementSource**: Any compliance standards mentioned (ASHRAE, LEED, Energy Star, etc.)

Return your response as a JSON object with these exact keys:
{
  "hasEquipment": {"name": "...", "manufacturer": "...", "confidence": 0.0-1.0},
  "hasAssetType": {"type": "...", "confidence": 0.0-1.0},
  "hasDatapoint": [
    {"aligned_datapoint": "...", "value": "...", "unit": "...", "impact_category": "...", "impact_subcategory": "...", "confidence": 0.0-1.0, "source_page": "...", "source_line": 42, "source_location": "..."}
  ],
  "hasMetadata": {"pageCount": N, "filename": "..."},
  "hasImpactCategory": {"suggested": "...", "confidence": 0.0-1.0},
  "hasRequirementSource": {"standards": ["..."], "confidence": 0.0-1.0}
}

Only extract datapoints you are confident about. If you cannot find a value, omit it or set confidence to low."""

    # Format document text with page + line markers so the LLM can track source_page and source_line
    formatted_pages = []
    for page_num, page_text in enumerate(document_text_list, start=1):
        lines = page_text.split('\n')
        numbered_lines = [f"[L{i+1}] {line}" for i, line in enumerate(lines) if line.strip()]
        formatted_pages.append(f"[PAGE {page_num}]\n" + "\n".join(numbered_lines))
    formatted_document = "\n\n".join(formatted_pages)

    user_prompt = f"""Extract ACER data from this document:

Filename: {filename}

--- DOCUMENT CONTENT ---
{formatted_document}
--- END DOCUMENT ---

Return only the JSON object, no additional text. Use the PAGE numbers in your source_page fields."""

    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://acer-visualizer.app",
            "X-Title": "ACER Visualizer",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1,  # Low temperature for consistent extraction
            "max_tokens": 4096,
        }
        
        response = requests.post(
            f"{OPENROUTER_API_BASE}/chat/completions",
            headers=headers,
            json=payload,
            timeout=120  # Longer timeout for extraction
        )
        response.raise_for_status()
        
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        
        # Parse JSON from response (handle potential markdown code blocks)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        return json.loads(content.strip())
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"OpenRouter API error: {str(e)}")
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse LLM response as JSON: {str(e)}")


def validate_api_key(api_key: str) -> bool:
    """Check if an API key is valid by making a simple request."""
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://acer-visualizer.app",
            "X-Title": "ACER Visualizer",
        }
        
        response = requests.get(
            f"{OPENROUTER_API_BASE}/models",
            headers=headers,
            timeout=10
        )
        return response.status_code == 200
        
    except Exception:
        return False


# Streamlit session state helpers
def get_openrouter_config() -> dict:
    """Get OpenRouter config from session state."""
    return {
        "api_key": st.session_state.get("openrouter_api_key", ""),
        "model": st.session_state.get("openrouter_model", ""),
        "enabled": st.session_state.get("openrouter_enabled", False),
    }


def set_openrouter_config(api_key: str = None, model: str = None, enabled: bool = None):
    """Set OpenRouter config in session state."""
    if api_key is not None:
        st.session_state["openrouter_api_key"] = api_key
    if model is not None:
        st.session_state["openrouter_model"] = model
    if enabled is not None:
        st.session_state["openrouter_enabled"] = enabled
