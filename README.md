# Biotech Deal Network

A graph-first, asset-aware biotech deal network explorer focused on clinical trial data and competitive landscape analysis.

## Overview

This proof-of-concept application allows you to:

1. **Explore a Network Graph** - Visualize relationships between Companies, Assets, and Clinical Trials for a specific indication (default: MuM - Mucosal Melanoma)
2. **View Company Details** - See a company's MuM-related assets, trials, and connections
3. **View Asset Details** - See intervention details, linked trials, sponsors, and inferred ownership
4. **Analyze the Landscape** - View competition summary with phase distribution, top sponsors, modalities, and standard of care information

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- (Optional) Docker for Neo4j mode

### Option A: Local Development (SQLite - Recommended)

```bash
# 1. Install dependencies (one-time)
cd backend && pip install -r requirements.txt && cd ..
cd frontend && npm install && cd ..

# 2. Start Backend (Terminal 1)
cd backend
USE_SQLITE=true python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# 3. Start Frontend (Terminal 2)
cd frontend
NEXT_PUBLIC_API_URL=http://localhost:8001 npm run dev

# 4. Open http://localhost:3000
```

**Note:** The repository includes a pre-populated SQLite database with MuM trial data, so the app works immediately after starting the servers.

### Option B: Docker (Neo4j mode)

```bash
# Using Make (recommended)
make up

# Or using Docker Compose directly
docker compose up -d --build
```

Wait ~30 seconds for all services to initialize.

### Ingest Data (Optional)

The repository includes a pre-populated database. To refresh data or load a different indication:

```bash
# For SQLite mode (port 8001)
curl -X POST "http://localhost:8001/api/ingest/clinicaltrials" \
  -H "Content-Type: application/json" \
  -d '{"indication": "MuM", "max_trials": 150}'

# For Docker mode (port 8000)
curl -X POST "http://localhost:8000/api/ingest/clinicaltrials" \
  -H "Content-Type: application/json" \
  -d '{"indication": "MuM", "max_trials": 150}'
```

### Open the Application

- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8001/docs (SQLite) or http://localhost:8000/docs (Docker)
- **Neo4j Browser** (Docker only): http://localhost:7474 (login: neo4j/biotech123)

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────────┐
│   Frontend  │────▶│   Backend   │────▶│  SQLite / Neo4j     │
│  (Next.js)  │     │  (FastAPI)  │     │  (Graph Storage)    │
│  Port 3000  │     │  Port 8001  │     │                     │
└─────────────┘     └─────────────┘     └─────────────────────┘
```

### Tech Stack

- **Frontend**: Next.js 14, TypeScript, React, Tailwind CSS, react-force-graph-2d
- **Backend**: Python 3.11, FastAPI, Pydantic
- **Database**: SQLite (default, local file) or Neo4j 5.x (Docker mode)
- **Infrastructure**: Local Python/Node or Docker Compose

## Data Model

### Nodes

| Node Type | Key Properties |
|-----------|---------------|
| **Company** | company_id, name, aliases, country, tickers, cik |
| **Asset** | asset_id, name, synonyms, modality, targets, indications, stage_current |
| **Trial** | trial_id (NCT), title, phase, status, interventions, conditions, sponsors |
| **Deal** | deal_id, deal_type, announce_date, summary, status |
| **Document** | doc_id, doc_type, url, published_at, text_hash |

### Relationships

```
(Company)-[:SPONSORS_TRIAL {role}]->(Trial)
(Company)-[:OWNS {confidence, source}]->(Asset)
(Company)-[:PARTY_TO {role}]->(Deal)
(Asset)-[:HAS_TRIAL]->(Trial)
(Deal)-[:COVERS]->(Asset)
(Deal)-[:SUPPORTED_BY]->(Document)
```

## Company/Sponsor Classification

When ingesting data from ClinicalTrials.gov, sponsors are automatically classified into types to help filter industry sponsors from academic sites and investigators.

### Classification Types

| Type | Description | Examples |
|------|-------------|----------|
| **industry** | Pharmaceutical and biotech companies | Pfizer, Novartis, IDEAYA Biosciences |
| **academic** | Universities, hospitals, research centers | MD Anderson, Mayo Clinic, Memorial Sloan Kettering |
| **nonprofit** | Research consortia, patient groups | EORTC, Alliance for Clinical Trials |
| **investigator** | Individual researchers (identified by MD, PhD, Prof.) | "Jose Lutzky, MD", "Prof. Dr. med. Dirk Schadendorf" |
| **government** | Government agencies | NCI, NIH, Department of Defense |
| **other** | Unclassified (usually investigators without titles) | Names without institutional affiliation |

### Classification Logic

The classification is performed in `backend/app/models/nodes.py` in the `Company.infer_type_from_name()` method. The logic uses:

1. **ClinicalTrials.gov Sponsor Class** (most reliable)
   - `INDUSTRY` → industry
   - `NIH`, `FED`, `OTHER_GOV` → government

2. **Name Pattern Matching** (in order of priority):
   - **Investigator patterns**: ", MD", ", PhD", "Prof. Dr.", etc.
   - **Government patterns**: "National Institutes of Health", "Department of Defense", etc.
   - **Nonprofit patterns**: "EORTC", "Alliance for Clinical", "Research Network", etc.
   - **Academic patterns**: "University", "Hospital", "Cancer Center", "Institute", "Clinic", etc.
   - **Industry patterns**: "Inc.", "Ltd.", "GmbH", "Pharmaceuticals", "Therapeutics", "Biosciences", etc.
   - **Known pharma companies**: "AstraZeneca", "Bristol-Myers", "Novartis", "Servier", etc.

3. **Default**: If no patterns match, defaults to "other"

### Updating Classifications

When adding new data sources or if classifications are incorrect:

1. **Add new patterns** to the appropriate list in `Company.infer_type_from_name()`
2. **Re-ingest data** to apply new classifications:
   ```bash
   curl -X POST "http://localhost:8001/api/ingest/clinicaltrials" \
     -H "Content-Type: application/json" \
     -d '{"indication": "MuM", "max_trials": 150}'
   ```
3. **Verify classifications** by checking the graph data or querying the database

### Frontend Filtering

The UI includes an "Industry Sponsors Only" toggle (default: ON) that filters the graph to show only `industry` type companies. This helps focus on competitive intelligence without academic sites cluttering the view.

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/health` | Health check with database stats |
| `POST /api/ingest/clinicaltrials` | Ingest trials for an indication |
| `GET /api/search?q=` | Search companies, assets, trials |
| `GET /api/graph/indication?name=MuM` | Get network graph data |
| `GET /api/company/{id}` | Get company details |
| `GET /api/asset/{id}` | Get asset details |
| `GET /api/trial/{id}` | Get trial details |
| `GET /api/landscape?indication=MuM` | Get landscape statistics |

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NEO4J_URI` | bolt://neo4j:7687 | Neo4j connection URI |
| `NEO4J_USER` | neo4j | Neo4j username |
| `NEO4J_PASSWORD` | biotech123 | Neo4j password |
| `DEFAULT_INDICATION` | MuM | Default indication to display |
| `LLM_ENRICHMENT_ENABLED` | false | Enable LLM-based asset enrichment |
| `OPENAI_API_KEY` | - | OpenAI API key (if LLM enrichment enabled) |

### Adding New Indications

Edit `backend/app/config.py` to add new indication terms:

```python
indication_terms: dict = {
    "MuM": [
        "mucosal melanoma",
        "metastatic uveal melanoma",
        # ...
    ],
    "NSCLC": [
        "non-small cell lung cancer",
        "NSCLC",
        # ...
    ],
}
```

## Development

### Running in Development Mode

```bash
# Terminal 1: Start Neo4j
docker compose up neo4j

# Terminal 2: Start Backend
make dev-backend

# Terminal 3: Start Frontend
make dev-frontend
```

### Running Tests

```bash
make test

# Or directly
cd backend && python -m pytest tests/ -v
```

## Data Quality & Provenance

- **Evidence Tracking**: Every extracted fact includes evidence pointers to source documents
- **Confidence Scores**: Inferred relationships (like ownership) include confidence scores
- **Source URLs**: All data links back to ClinicalTrials.gov records
- **No Fabrication**: The system never invents sources or citations

## Drug Ownership & Asset Attribution

### The Problem

Clinical trials often include drugs from multiple sources:
- **Proprietary drugs**: The sponsor's own drug being tested
- **Comparator drugs**: Standard-of-care drugs from other companies used as control arms
- **Combination partners**: Other companies' drugs used in combination therapy

Naively attributing all drugs in a trial to the trial sponsor creates incorrect ownership relationships.

### Our Solution

The normalization service (`backend/app/services/normalization_service.py`) maintains:

1. **`DRUG_ALIASES`** - Maps drug code names to canonical names (e.g., IDE196 → darovasertib, IMCgp100 → tebentafusp)

2. **`KNOWN_DRUG_OWNERS`** - Database of known drug owners with metadata:
   ```python
   "darovasertib": {
       "owner": "IDEAYA Biosciences",
       "modality": "small_molecule",
       "targets": ["PKC"],
       "fda_approved": False
   },
   "tebentafusp": {
       "owner": "Immunocore",
       "modality": "bispecific",
       "targets": ["gp100", "CD3"],
       "fda_approved": True,
       "brand_name": "KIMMTRAK"
   }
   ```

3. **`is_proprietary_to_sponsor()`** - Logic to determine if a drug belongs to a sponsor:
   - Checks `KNOWN_DRUG_OWNERS` first
   - Falls back to company code prefix matching (e.g., IDE* drugs → IDEAYA)
   - Generic drugs are never attributed to any sponsor

### Adding New Drugs

When ingesting data for a new indication or company, update `KNOWN_DRUG_OWNERS`:

```python
# In backend/app/services/normalization_service.py

KNOWN_DRUG_OWNERS = {
    # Add new drug with known owner
    "my_new_drug": {
        "owner": "Company Name",
        "modality": "antibody",  # or small_molecule, bispecific, etc.
        "targets": ["TARGET1", "TARGET2"],
        "fda_approved": True,
        "brand_name": "BRAND_NAME"  # optional
    },
    # ...
}

# Also add aliases if the drug has code names
DRUG_ALIASES = {
    "my_new_drug": ["mnd-001", "code-name"],
    # ...
}
```

### Merging Duplicate Assets

The alias system automatically merges duplicates during normalization. For example:
- "IDE196" and "darovasertib" both normalize to "darovasertib"
- "IMCgp100" and "tebentafusp" both normalize to "tebentafusp"

To add a new alias mapping:
```python
DRUG_ALIASES = {
    "canonical_name": ["alias1", "alias2", "code-name"],
}
```

### Verification Workflow

When preparing for a demo or verifying data accuracy:

1. **Query the companies of interest**:
   ```bash
   curl "http://localhost:8001/api/company/company_547c050bb7f8" | jq
   ```

2. **Check for misattributed assets** - look for common drugs like pembrolizumab, nivolumab that shouldn't be "owned" by the company

3. **Research and update** `KNOWN_DRUG_OWNERS` with correct ownership data

4. **Re-ingest** to apply fixes:
   ```bash
   curl -X POST "http://localhost:8001/api/ingest/clinicaltrials" \
     -H "Content-Type: application/json" \
     -d '{"indication": "MuM", "max_trials": 150}'
   ```

5. **Verify** the assets now show correct ownership

## Limitations (POC)

- Deal ingestion from SEC filings is stubbed (architecture ready, implementation pending)
- Standard of Care information is placeholder text with disclaimers
- LLM enrichment is optional and requires OpenAI API key
- Asset normalization uses pattern matching; complex cases may need manual curation

## Troubleshooting

### Services not starting?

```bash
# Check container status
docker compose ps

# View logs
docker compose logs backend
docker compose logs neo4j
```

### No data showing?

1. Wait for Neo4j to be healthy (check `make health`)
2. Run ingestion: `make ingest`
3. Refresh the frontend

### Reset everything?

```bash
make clean  # Removes all containers and data volumes
make up     # Start fresh
make ingest # Re-ingest data
```

## License

MIT License - See LICENSE file for details.

## Disclaimer

This application is for informational purposes only. It does not provide medical advice. The landscape analysis and standard of care information should not be used for clinical decision-making. Always consult qualified healthcare professionals and current clinical guidelines.
