# 🔬 ResearchIQ — MCP-Powered AI Research Intelligence Platform

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)
![Neo4j AuraDB](https://img.shields.io/badge/Neo4j-AuraDB%20Graph-008CC1?logo=neo4j)
![MongoDB Atlas](https://img.shields.io/badge/MongoDB-Atlas%20NoSQL-47A248?logo=mongodb)
![OpenAlex](https://img.shields.io/badge/OpenAlex-Citation%20Index-blueviolet)
![Hugging Face](https://img.shields.io/badge/Hugging%20Face-Hub%20MCP-FFD21E?logo=huggingface)
![Groq](https://img.shields.io/badge/Groq-Inference-F05032)
![Model Context Protocol](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-red)

**ResearchIQ** is a state-of-the-art Research Intelligence Platform that enables researchers, students, and engineers to discover, synthesize, analyze, and cross-examine academic literature using AI.

Powered by the **Model Context Protocol (MCP)** and modern academic graph APIs, ResearchIQ connects Large Language Models to live external research ecosystems: **ArXiv** (2.4M+ preprints), **OpenAlex** (250M+ scientific works & citation index), **Semantic Scholar** (citation networks), **GitHub** (code implementations), and the **Hugging Face Hub** (open-weights models and benchmark datasets).

With a **Tri-Engine Polyglot NoSQL Architecture** (Neo4j AuraDB + MongoDB Atlas + SQLite), an **Interactive Citation & Reference Explorer**, an **Author & Researcher Portfolio Engine**, an **In-Memory Full PDF Deep RAG Engine** with exact page citations, and a **Graph Centrality Engine** (PageRank, Betweenness Centrality, Community Detection), ResearchIQ transforms scattered academic knowledge into actionable intelligence through a unified cockpit.

---

## 🚀 Key Innovations & Features

### 1. 📊 Interactive Paper Citation & Reference Explorer *(New in v2.1)*
Academic papers cannot be understood in isolation; understanding their impact requires examining **who they cite** and **who cites them**.

- **1-Click Citation Modal:** Clicking any paper card or the **`📊 Citations & Network`** button opens an interactive citation drawer.
- **Multi-Source Citation Resolution:** Queries OpenAlex's real-time citation index (`cites:W...`), Semantic Scholar API, and local Neo4j graph relationships.
- **Interactive D3 Citation Graph:** Color-coded directed force simulation showing:
  - 🟢 **Green Root Node:** The inspected paper.
  - 🔴 **Red Nodes:** Citing Papers (incoming influence).
  - 🔵 **Blue Nodes:** References (outgoing foundational bibliography).
- **Categorized Tabs:**
  - **📥 Citing Papers:** High-impact follow-up papers with publication year, authors, and citation counts.
  - **📤 References:** Complete bibliography of prior works cited by the author.
- **Neo4j Continuous Write-Back:** Discovered citation relationships are persisted into Neo4j AuraDB (`save_citations_to_neo4j`), continuously expanding the local graph.

---

### 2. 👤 Author & Researcher Portfolio Engine *(New in v2.1)*
Discover leading researchers in any field, view their publications, and inspect collaboration patterns.

- **Dual-Mode Discovery Cockpit:** Top toggle enables instant switching between:
  - `[ 📄 Search by Topic / Title ]`
  - `[ 👤 Search by Author / Researcher ]`
- **Author Profile Hero Card:** Displays researcher name, verified institutional affiliations (e.g. *USC*, *Google*, *Toronto*), total published works, cumulative citations, and **h-index**.
- **Research Papers Portfolio:** Complete list of papers authored by the researcher, with sorting by **Most Cited** or **Newest (Year)** and instant access to the citation modal.
- **Frequent Co-Authors Grid:** Grid of primary collaborators with joint publication counts and a 1-click **"View Papers →"** shortcut to drill into that collaborator's work.
- **Author Collaboration Graph:** D3 graph placing the researcher in gold (`#e3b341`) at the center, linked to authored papers and co-authors.
- **Universal Click-Through Navigation:** Every author name on ANY paper card across the entire application is a clickable tag that opens their research portfolio.

---

### 3. 🔌 Multi-Source MCP & Academic Ecosystem
ResearchIQ exposes external scientific databases as AI-accessible tool providers via the Model Context Protocol and academic graph APIs:

| Data Provider | Ecosystem | Capabilities |
|---|---|---|
| **OpenAlex API** | 250M+ Scientific Works | Real-time citation tracking (`cites:W...`), referenced works, author h-index, and affiliations. |
| **ArXiv MCP** | 2.4M+ Preprints | Real-time paper discovery, author searches (`au:`), metadata extraction, and in-memory direct full PDF streaming. |
| **Semantic Scholar MCP** | Citation Network | Real-time citation counts, influential citations, reference trees, and author graphs. |
| **GitHub MCP** | Open-Source Code | Discovers star-ranked open-source code repositories implementing the paper methods. |
| **Hugging Face Hub MCP** | AI Artifacts | Discovers pretrained model weights (with download metrics, task pipeline tags, 1-click Python snippets) and benchmark evaluation datasets. |

---

### 4. 🗄️ Tri-Engine Polyglot NoSQL Architecture
Research data is heterogeneous: papers have rich document schemas, citations form directed graphs, and application states need lightweight relational fallbacks.

- **Neo4j AuraDB (Graph NoSQL):** Models scientific relationships.
  - Nodes: `(p:Paper)`, `(t:Topic)`, `(a:Author)`, `(r:Repository)`, `(m:Model)`, `(d:Dataset)`.
  - Relationships: `[:COVERS]`, `[:AUTHORED]`, `[:CITES]`, `[:HAS_IMPLEMENTATION]`, `[:HAS_MODEL]`, `[:USES_DATASET]`.
- **MongoDB Atlas (Document NoSQL):** High-throughput JSON document store for raw paper payloads, multi-section surveys, author profiles, and search history.
- **SQLite 3 (Relational Baseline):** Embedded local persistence ensuring zero-downtime offline fallback and parallel write mirroring.

---

### 5. 📄 "Chat with the Full PDF" (Deep Paper RAG)
Traditional RAG systems index only brief abstracts, losing equations, benchmarks, and hyperparameter tables.

- **Zero-Disk In-Memory Parsing:** Downloads PDFs directly from ArXiv's CDN via `aiohttp` or handles drag-and-drop local uploads via `pypdf` streams in RAM (`io.BytesIO`).
- **Sliding-Window Semantic Chunking:** Slices full text into 700-character windows with 120-character overlapping boundaries to preserve mathematical proofs across chunk edges.
- **Exact Page-Level Citations:** Retains 1-indexed document page numbers (`page: 5`). Answers generated by the Groq LLM explicitly cite source pages:
  > *"The multi-head attention mechanism uses 8 parallel attention heads with dimension $d_k = 64$. `📄 Page 5`"*
- **Retrieved Excerpts Drawer:** Interactive accordion allowing users to inspect the exact grounded excerpts with page tags.

---

### 6. 🕸️ Neo4j Graph Intelligence & Centrality
Located in the dedicated **`🕸️ Graph Intel`** cockpit:

- **PageRank ($\alpha=0.85$):** Calculates recursive scientific prestige (papers cited by other seminal papers).
- **Betweenness Centrality:** Discovers cross-disciplinary "bridge papers" that link disparate research domains.
- **In-Degree Centrality:** Measures raw direct citation density within the active graph.
- **HITS (Hubs & Authorities):** Distinguishes cornerstone foundational literature from survey papers.
- **Greedy Modularity Community Detection:** Automatically partitions the citation graph into distinct sub-topics without manual labeling.
- **Influential Researchers Leaderboard:** Aggregates paper PageRank scores across author edges to identify leading domain scientists.
- **1-Click Neo4j Write-Back:** Persists computed PageRank and Betweenness metrics directly into `(p:Paper)` nodes in Neo4j AuraDB (`POST /api/graph/sync_metrics`).

---

### 7. 🤖 Automated Research Synthesizers
- **📖 Literature Review Generator:** Synthesizes state-of-the-art papers, core methods, and findings with Markdown export.
- **📚 Research Survey Generator:** Multi-section taxonomy, timeline, research gaps, interactive knowledge graph, and Markdown export.
- **💡 Research Gap Detector:** Scans literature to uncover unresolved questions, missing benchmarks, and future opportunities.
- **⚖️ Head-to-Head Comparison:** Side-by-side comparative matrix of two architectures across methodology, datasets, and trade-offs.
- **🗺️ Research Roadmap Generator:** 4-Phase milestone learning curriculum with recommended papers, tasks, and skills.
- **🗂️ Multi-Cloud History Archive:** Persistent storage across MongoDB Atlas and SQLite for all previous reports and queries.

---

## 🏗️ Architecture & Data Flow

```text
                           User Search / Question
                                      │
                                      ▼
                    ┌───────────────────────────────────┐
                    │    React 18 + Vite Cockpit        │
                    │ (D3.js Force Simulation + CSS)    │
                    │  [Topic Search] [Author Search]   │
                    └─────────────────┬─────────────────┘
                                      │
                                      ▼
                    ┌───────────────────────────────────┐
                    │     FastAPI Backend Router        │
                    └─────────────────┬─────────────────┘
                                      │
         ┌────────────────────────────┼────────────────────────────┐
         ▼                            ▼                            ▼
  ┌──────────────┐             ┌──────────────┐             ┌──────────────┐
  │ Academic     │             │  PDF Engine  │             │    Graph     │
  │ Service      │             │(Sliding RAG) │             │  Analytics   │
  │(academic.py) │             │ (pypdf/RAM)  │             │ (PageRank)   │
  └──────┬───────┘             └──────┬───────┘             └──────┬───────┘
         │                            │                            │
         └────────────────────────────┼────────────────────────────┘
                                      │
         ┌────────────────────────────┴────────────────────────────┐
         ▼                                                         ▼
 ┌───────────────┐                                         ┌───────────────┐
 │ Data Providers│                                         │ Polyglot NoSQL│
 ├───────────────┤                                         ├───────────────┤
 │• OpenAlex     │                                         │• Neo4j AuraDB │
 │• ArXiv        │                                         │• Mongo Atlas  │
 │• Scholar      │                                         │• SQLite 3     │
 │• GitHub       │                                         └───────────────┘
 │• Hugging Face │
 └───────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technologies |
|---|---|
| **Frontend** | React 18, Vite, D3.js (v7), Custom Glassmorphic Dark UI |
| **Backend** | FastAPI, Python 3.11, Uvicorn (ASGI), Pydantic v2 |
| **LLM Inference** | Groq Cloud (`openai/gpt-oss-120b` / Llama 3.3 70B), LangChain |
| **Graph NoSQL** | Neo4j AuraDB (Cypher, GDS, Constraints) |
| **Document NoSQL** | MongoDB Atlas (`pymongo`, `dnspython`) |
| **Relational Baseline** | SQLite 3 (Parallel Write Mirror & Fallback) |
| **Academic Graph APIs**| OpenAlex API, ArXiv API, Semantic Scholar Graph API |
| **AI Artifacts & Code**| Hugging Face Hub API, GitHub REST API |
| **PDF Extraction** | `pypdf`, `io.BytesIO` (Zero-disk RAM streams) |
| **Graph Analytics** | NetworkX (PageRank, Betweenness Centrality, Modularity) |
| **Async Networking** | `aiohttp` |

---

## 📂 Project Structure

```text
research-intelligence-platform/
│
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   └── research_agent.py      # LLM reasoning, reviews, surveys, roadmaps
│   │   ├── analytics/
│   │   │   └── graph_analytics.py     # PageRank, Betweenness Centrality, Communities
│   │   ├── api/
│   │   │   └── routes.py              # REST API endpoints (Search, Citations, Authors)
│   │   ├── db/
│   │   │   ├── database.py            # SQLite relational baseline
│   │   │   ├── mongo_client.py        # MongoDB Atlas document NoSQL
│   │   │   └── neo4j_client.py        # Neo4j AuraDB graph NoSQL
│   │   ├── mcp/
│   │   │   ├── arxiv.py               # ArXiv MCP preprint fetcher
│   │   │   ├── semantic_scholar.py    # Semantic Scholar citation graph
│   │   │   ├── github.py              # GitHub repo discovery
│   │   │   └── huggingface.py         # Hugging Face Hub models & datasets
│   │   ├── rag/
│   │   │   ├── pdf_engine.py          # In-memory sliding-window full PDF RAG
│   │   │   └── vectorstore.py         # In-memory TF-IDF / BM25 index
│   │   ├── services/
│   │   │   ├── academic.py            # Multi-source citations & author portfolios
│   │   │   └── graph.py               # NetworkX graph builder
│   │   └── main.py                    # FastAPI application initialization
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── CitationModal.jsx      # Interactive citation network & references modal
│   │   │   ├── Graph.jsx              # D3.js force-directed knowledge graph
│   │   │   ├── HFArtifacts.jsx        # ModelCard & DatasetCard components
│   │   │   ├── PaperCard.jsx          # Academic paper cards with clickable authors
│   │   │   ├── RepoList.jsx           # GitHub repository cards
│   │   │   └── Spinner.jsx            # Loading indicators
│   │   ├── pages/
│   │   │   ├── Discover.jsx           # Topic search + Author portfolio search
│   │   │   ├── GraphAnalytics.jsx     # Neo4j PageRank & Centrality cockpit
│   │   │   ├── Chat.jsx               # Full PDF Deep RAG & ArXiv Q&A
│   │   │   ├── Review.jsx             # Literature review generator
│   │   │   ├── Survey.jsx             # Comprehensive survey generator
│   │   │   ├── Gaps.jsx               # Research gap detector
│   │   │   ├── Compare.jsx            # Head-to-head paper comparison
│   │   │   ├── Roadmap.jsx            # Research learning roadmap generator
│   │   │   └── History.jsx            # Dual-database report archive
│   │   ├── services/
│   │   │   └── api.js                 # Frontend API client
│   │   ├── App.jsx                    # Root layout & navigation
│   │   └── index.css                  # Custom dark design system tokens
│   ├── package.json
│   └── vite.config.js
│
├── run.py                             # Full-stack server runner
├── README.md                          # Platform documentation
├── RESEARCHIQ_PROJECT_REPORT.md       # Comprehensive System & Architectural Report
├── .env.example
└── .gitignore
```

---

## ⚙️ Quickstart Installation

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/Bharath-vinayagam/researchiq.git
cd researchiq
```

### 2️⃣ Create & Activate Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3️⃣ Install Dependencies
```bash
pip install -r backend/requirements.txt
cd frontend
npm install
npm run build
cd ..
```

### 4️⃣ Configure Environment Variables
Copy `.env.example` to `.env`:
```env
# Groq LLM
GROQ_API_KEY=gsk_your_groq_api_key
GROQ_MODEL=openai/gpt-oss-120b

# Neo4j AuraDB (Cloud Graph NoSQL)
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_neo4j_password

# MongoDB Atlas (Cloud Document NoSQL)
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
MONGODB_DATABASE=researchiq

# External MCP Tokens (100% Optional - Public APIs work out-of-the-box without keys)
GITHUB_TOKEN=your_github_token_here_optional
HUGGINGFACE_TOKEN=your_hf_token_here_optional
SEMANTIC_SCHOLAR_API_KEY=your_key_here_optional
```

### 5️⃣ Run the Application
```bash
python run.py
```
Open **`http://127.0.0.1:8000`** in your browser.

---

## 👨‍💻 Author

**Bharath**  
B.Tech Computer Science and Engineering  
VIT Chennai  
- **GitHub:** [@Bharath-vinayagam](https://github.com/Bharath-vinayagam)  
- **Repository:** [researchiq](https://github.com/Bharath-vinayagam/researchiq.git)  

---

⭐ *If you find ResearchIQ helpful, give it a star on GitHub!*
