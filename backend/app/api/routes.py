from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from app.rag.pdf_engine import pdf_store, download_arxiv_pdf
from app.mcp.arxiv import ArxivMCP
from app.mcp.semantic_scholar import SemanticScholarMCP
from app.mcp.github import GitHubMCP
from app.mcp.huggingface import HuggingFaceMCP
from app.services.graph import build_knowledge_graph, build_citation_graph
from app.rag.vectorstore import add_papers, query as rag_query, count as rag_count
from app.agents import research_agent as agent
from app.db.database import (
    save_report, save_search, get_reports, get_searches,
    get_report_by_id
)
from app.db import neo4j_client, mongo_client
from app.analytics.graph_analytics import compute_graph_analytics, write_metrics_to_neo4j

router = APIRouter(prefix="/api")

arxiv   = ArxivMCP()
scholar = SemanticScholarMCP()
github  = GitHubMCP()
hf      = HuggingFaceMCP()


# ── Request models ────────────────────────────────────────────────────────
class SearchReq(BaseModel):
    query: str
    sources: list = ["arxiv", "semantic_scholar"]
    max_results: int = 10

class TopicReq(BaseModel):
    topic: str

class CompareReq(BaseModel):
    paper_a: dict
    paper_b: dict

class ChatReq(BaseModel):
    question: str
    use_rag: bool = False

class CitationReq(BaseModel):
    title: str

class MultiHopReq(BaseModel):
    title: str
    hops: int = 2

class ArxivPdfReq(BaseModel):
    arxiv_id: str

class PdfChatReq(BaseModel):
    question: str


# ── Helpers ───────────────────────────────────────────────────────────────
def _merge(lists):
    seen, out = set(), []
    for p in (p for lst in lists for p in lst):
        k = (p.get("title") or "").lower()[:60]
        if k and k not in seen:
            seen.add(k); out.append(p)
    return out


# ── Search ────────────────────────────────────────────────────────────────
@router.post("/search")
async def search(req: SearchReq):
    arxiv_res, scholar_res, gh_res = [], [], []
    if "arxiv" in req.sources:
        arxiv_res = await arxiv.search(req.query, req.max_results)
    if "semantic_scholar" in req.sources:
        scholar_res = await scholar.search(req.query, req.max_results)
    # Always fetch GitHub repos and Hugging Face models & datasets
    gh_res = await github.search(req.query, max_results=8)
    hf_res = await hf.search_all(req.query, max_models=6, max_datasets=6)
    models = hf_res.get("models", [])
    datasets = hf_res.get("datasets", [])

    papers = _merge([arxiv_res, scholar_res])
    add_papers(papers)
    save_search(req.query, papers, gh_res)

    # Persist knowledge graph in Neo4j (Papers, Authors, Repos, HF Models, Datasets)
    neo4j_client.save_knowledge_graph_to_neo4j(req.query, papers, gh_res, models, datasets)

    # Retrieve from Neo4j if available, otherwise fallback to NetworkX in-memory
    neo4j_graph = neo4j_client.get_knowledge_graph_from_neo4j(req.query)
    graph = neo4j_graph or build_knowledge_graph(req.query, papers, gh_res, models, datasets)

    return {
        "papers": papers, "repos": gh_res, "models": models, "datasets": datasets,
        "graph": graph, "total": len(papers), "rag_count": rag_count(),
        "graph_source": "neo4j" if neo4j_graph else "networkx"
    }


# ── Citation Network ──────────────────────────────────────────────────────
@router.post("/citations")
async def get_citations(req: CitationReq):
    data = await scholar.get_citations(req.title)
    neo4j_client.save_citations_to_neo4j(req.title, data)
    graph = build_citation_graph(req.title, data)
    return {"data": data, "graph": graph}


# ── Literature Review ─────────────────────────────────────────────────────
@router.post("/review")
async def literature_review(req: TopicReq):
    papers = _merge([
        await arxiv.search(req.topic, 10),
        await scholar.search(req.topic, 8),
    ])
    repos = await github.search(req.topic, max_results=6)
    add_papers(papers)
    review = await agent.generate_literature_review(req.topic, papers)
    save_report(req.topic, "literature_review", review, repos=repos, papers=papers[:10])
    return {"review": review, "papers": papers[:10], "repos": repos}


# ── Literature Survey ─────────────────────────────────────────────────────
@router.post("/survey")
async def survey(req: TopicReq):
    papers = _merge([
        await arxiv.search(req.topic, 10),
        await scholar.search(req.topic, 8),
    ])
    repos = await github.search(req.topic, max_results=6)
    add_papers(papers)
    result = await agent.generate_survey(req.topic, papers)
    graph  = build_knowledge_graph(req.topic, papers, repos)
    save_report(req.topic, "survey", str(result), repos=repos, papers=papers[:10])
    return {"survey": result, "papers": papers[:10], "repos": repos, "graph": graph}


# ── Research Gaps ─────────────────────────────────────────────────────────
@router.post("/gaps")
async def gaps(req: TopicReq):
    papers = _merge([
        await arxiv.search(req.topic, 10),
        await scholar.search(req.topic, 8),
    ])
    repos = await github.search(req.topic, max_results=6)
    add_papers(papers)
    result = await agent.detect_research_gaps(req.topic, papers)
    save_report(req.topic, "gaps", str(result), repos=repos, papers=papers)
    return {"gaps": result, "papers_analysed": len(papers), "repos": repos}


# ── Compare Papers ────────────────────────────────────────────────────────
@router.post("/compare")
async def compare(req: CompareReq):
    return await agent.compare_papers(req.paper_a, req.paper_b)


# ── Chat / Q&A ────────────────────────────────────────────────────────────
@router.post("/chat")
async def chat(req: ChatReq):
    if req.use_rag and rag_count() > 0:
        papers = rag_query(req.question, n_results=8)
    else:
        papers = _merge([
            await arxiv.search(req.question, 6),
            await scholar.search(req.question, 4),
        ])
        add_papers(papers)
    answer = await agent.answer_question(req.question, papers)
    return {"answer": answer, "sources": papers[:6]}


# ── Research Roadmap ──────────────────────────────────────────────────────
@router.post("/roadmap")
async def roadmap(req: TopicReq):
    papers = _merge([
        await arxiv.search(req.topic, 8),
        await scholar.search(req.topic, 6),
    ])
    repos = await github.search(req.topic, max_results=6)
    add_papers(papers)
    result = await agent.generate_roadmap(req.topic, papers)
    save_report(req.topic, "roadmap", str(result), repos=repos, papers=papers)
    return {"roadmap": result, "papers": papers, "repos": repos}


# ── History / Reports ─────────────────────────────────────────────────────
@router.get("/reports")
def reports():
    return get_reports()

@router.get("/reports/{rid}")
def report(rid: str):
    r = get_report_by_id(rid)
    if not r:
        raise HTTPException(404, "Not found")
    return r

@router.get("/searches")
def searches():
    return get_searches()

@router.get("/rag/count")
def rag_size():
    return {"count": rag_count()}


# ── Neo4j Graph Database ──────────────────────────────────────────────────
@router.get("/neo4j/status")
def neo4j_status():
    return neo4j_client.get_neo4j_stats()

@router.post("/neo4j/citations/multihop")
def neo4j_multihop(req: MultiHopReq):
    graph = neo4j_client.get_multi_hop_citations_from_neo4j(req.title, req.hops)
    if not graph:
        raise HTTPException(404, "No citation paths found in Neo4j for this paper")
    return graph

@router.get("/neo4j/graph/{topic}")
def neo4j_topic_graph(topic: str):
    g = neo4j_client.get_knowledge_graph_from_neo4j(topic)
    if not g:
        raise HTTPException(404, f"No graph found in Neo4j for topic: {topic}")
    return g


# ── MongoDB Document Store & Polyglot NoSQL ──────────────────────────────
@router.get("/mongodb/status")
def mongodb_status():
    return mongo_client.get_mongo_stats()

@router.get("/nosql/status")
def nosql_status():
    return {
        "architecture": "Polyglot NoSQL Architecture",
        "document_store": {
            "engine": "MongoDB",
            "role": "Semi-structured papers, searches, reports, and chat sessions",
            **mongo_client.get_mongo_stats()
        },
        "graph_store": {
            "engine": "Neo4j",
            "role": "Citation networks, co-authorship links, and knowledge graphs",
            **neo4j_client.get_neo4j_stats()
        },
        "relational_baseline": {
            "engine": "SQLite",
            "role": "Local baseline persistence and offline fallback"
        }
    }


# ── Full PDF Deep RAG ─────────────────────────────────────────────────────
@router.post("/pdf/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported")
    content = await file.read()
    try:
        info = pdf_store.add_pdf_bytes(content, file.filename)
        return {"success": True, "info": info, "stats": pdf_store.get_stats()}
    except Exception as e:
        raise HTTPException(500, f"Error processing PDF: {e}")

@router.post("/pdf/fetch_arxiv")
async def fetch_arxiv_pdf(req: ArxivPdfReq):
    pdf_bytes = await download_arxiv_pdf(req.arxiv_id)
    if not pdf_bytes:
        raise HTTPException(404, f"Could not fetch PDF for ArXiv ID: {req.arxiv_id}")
    filename = f"{req.arxiv_id.strip().split('/')[-1]}.pdf"
    info = pdf_store.add_pdf_bytes(pdf_bytes, filename)
    return {"success": True, "info": info, "stats": pdf_store.get_stats()}

@router.post("/pdf/chat")
async def chat_pdf(req: PdfChatReq):
    chunks = pdf_store.search(req.question, top_k=6)
    if not chunks:
        return {
            "answer": "No relevant sections found in the loaded PDF(s). Please make sure a PDF is uploaded or try another question.",
            "chunks": []
        }
    answer = await agent.answer_pdf_question(req.question, chunks)
    return {
        "answer": answer,
        "chunks": [{"page": c["page"], "paper": c["paper"], "text": c["text"][:300]} for c in chunks]
    }

@router.get("/pdf/status")
def get_pdf_status():
    return pdf_store.get_stats()

@router.delete("/pdf/clear")
def clear_pdfs():
    pdf_store.clear()
    return {"success": True, "stats": pdf_store.get_stats()}


# ── Graph Algorithms & Centrality Analytics ───────────────────────────────
@router.get("/graph/analytics")
def get_graph_analytics(topic: str = None, metric: str = "pagerank", limit: int = 30):
    return compute_graph_analytics(topic=topic, metric=metric, limit=limit)

@router.post("/graph/sync_metrics")
def sync_graph_metrics():
    return write_metrics_to_neo4j()


# ── Hugging Face Hub MCP Endpoints ────────────────────────────────────────
@router.get("/hf/models")
async def get_hf_models(query: str, limit: int = 8):
    return await hf.search_models(query, limit)

@router.get("/hf/datasets")
async def get_hf_datasets(query: str, limit: int = 8):
    return await hf.search_datasets(query, limit)





