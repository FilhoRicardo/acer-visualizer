# ACER Visualizer

**Building Passport Processor** — Extract structured data from building equipment PDFs

```
Drop a PDF → See ACER Graph → Export JSON/Markdown
```

## The ACER Concept

Every document maps to **6 relationships**:

| Relationship | Description | Usually Found? |
|-------------|-------------|----------------|
| `hasEquipment` | What the document describes | ✓ |
| `hasAssetType` | Category of equipment | ✓ |
| `hasDatapoint` | Extracted data values (1-50+) | ✓ |
| `hasMetadata` | Document info (auto-generated) | ✓ |
| `hasImpactCategory` | Sustainability dimension | ✗ Usually missing |
| `hasRequirementSource` | Compliance standards | ✗ Usually missing |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run src/app.py
```

## Sample Output

```
Carrier 40RUS 060-8
│
├── ✓ hasEquipment          Carrier 40RUS 060-8        98%
├── ✓ hasAssetType          Rooftop Unit               95%
├── ✓ hasDatapoint          24 datapoints              89%
│   ├── Primary Energy Demand [ID:80]     175,000 BTU/h  94%
│   ├── COP [ID:152]                     3.8           96%
│   └── ...
├── ✓ hasMetadata          auto-generated             100%
├── ✗ hasImpactCategory     NOT FOUND                  [Add →]
└── ✗ hasRequirementSource NOT FOUND                  [Add →]
```

## Project Structure

```
ACER-Visualizer/
├── src/
│   ├── app.py              # Streamlit web app
│   └── models/
│       ├── acer_graph.py   # Core data models
│       └── sample_data.py  # Sample data for demos
├── data/                   # BPalig.csv alignment file
├── tests/
└── requirements.txt
```

## Features

- [x] ACER Graph visualization
- [x] Confidence scoring
- [x] JSON export
- [x] Markdown export (Obsidian-ready)
- [x] Sample data
- [ ] PDF upload + extraction
- [ ] LLM integration
- [ ] Batch processing

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Streamlit |
| PDF Extraction | pdfplumber, PyMuPDF |
| AI Extraction | Anthropic Claude API |
| Visualization | Plotly |
| Data Validation | Pydantic |

---

*Built for the ACER ontology ecosystem*
