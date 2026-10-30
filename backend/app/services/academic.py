import asyncio
import logging
import os
import urllib.parse
import urllib.request
import json
import xml.etree.ElementTree as ET
import networkx as nx
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path, override=True)

from app.mcp.semantic_scholar import SemanticScholarMCP
from app.db import neo4j_client, mongo_client
from app.services.graph import build_citation_graph

logger = logging.getLogger("academic_service")
_scholar = SemanticScholarMCP()

USER_AGENT = "ResearchIQ/1.0 (academic research platform; mailto:researchiq@example.com)"


def _fetch_json(url: str, timeout: int = 12) -> Optional[Dict[str, Any]]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.debug(f"Fetch failed for {url}: {e}")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# 1. PAPER CITATIONS & REFERENCES
# ─────────────────────────────────────────────────────────────────────────────

async def get_paper_citations(title: str, limit: int = 15) -> Dict[str, Any]:
    """
    Retrieve citations (papers citing this paper) and references (papers cited by this paper).
    Tries:
      1. OpenAlex (comprehensive, real-time, free citation graph)
      2. Semantic Scholar (if available/not rate limited)
      3. Neo4j local graph store
    Ingests retrieved nodes and edges into Neo4j and MongoDB, and builds a D3 citation graph.
    """
    clean_title = (title or "").strip()
    if not clean_title:
        return {"paper": {}, "citations": [], "references": [], "citation_count": 0, "graph": {"nodes": [], "links": []}}

    citing_papers = []
    referenced_papers = []
    root_paper = {"title": clean_title, "citations": 0, "year": "", "authors": [], "url": ""}
    source_used = "openalex"

    # 1. Try OpenAlex first for rich real-time citation network
    try:
        encoded_title = urllib.parse.quote(clean_title)
        oa_work_url = f"https://api.openalex.org/works?filter=title.search:{encoded_title}&per-page=1"
        data = _fetch_json(oa_work_url, timeout=10)

        if data and data.get("results"):
            w = data["results"][0]
            wid = w.get("id", "").split("/")[-1]
            root_paper = {
                "id": w.get("id"),
                "title": w.get("title") or clean_title,
                "year": str(w.get("publication_year") or ""),
                "citations": int(w.get("cited_by_count") or 0),
                "url": (w.get("primary_location") or {}).get("landing_page_url") or (w.get("ids") or {}).get("doi") or w.get("id"),
                "authors": [a.get("author", {}).get("display_name") for a in w.get("authorships", []) if a.get("author", {}).get("display_name")],
                "abstract": w.get("abstract") or "",
                "source": "openalex"
            }

            # Fetch citing papers (who cites this work)
            if wid:
                cites_url = f"https://api.openalex.org/works?filter=cites:{wid}&sort=cited_by_count:desc&per-page={limit}"
                c_data = _fetch_json(cites_url, timeout=10)
                if c_data and c_data.get("results"):
                    for cp in c_data["results"]:
                        citing_papers.append({
                            "id": cp.get("id"),
                            "title": cp.get("title") or "",
                            "year": str(cp.get("publication_year") or ""),
                            "citations": int(cp.get("cited_by_count") or 0),
                            "url": (cp.get("primary_location") or {}).get("landing_page_url") or cp.get("id"),
                            "authors": [a.get("author", {}).get("display_name") for a in cp.get("authorships", [])[:4] if a.get("author", {}).get("display_name")],
                            "source": "openalex"
                        })

                # Fetch references (works cited by this paper)
                ref_ids = [ref.split("/")[-1] for ref in (w.get("referenced_works") or [])[:limit]]
                if ref_ids:
                    pipe_refs = "|".join(ref_ids[:15])
                    ref_url = f"https://api.openalex.org/works?filter=openalex_id:{pipe_refs}&per-page={len(ref_ids)}"
                    r_data = _fetch_json(ref_url, timeout=10)
                    if r_data and r_data.get("results"):
                        for rp in r_data["results"]:
                            referenced_papers.append({
                                "id": rp.get("id"),
                                "title": rp.get("title") or "",
                                "year": str(rp.get("publication_year") or ""),
                                "citations": int(rp.get("cited_by_count") or 0),
                                "url": (rp.get("primary_location") or {}).get("landing_page_url") or rp.get("id"),
                                "authors": [a.get("author", {}).get("display_name") for a in rp.get("authorships", [])[:4] if a.get("author", {}).get("display_name")],
                                "source": "openalex"
                            })
    except Exception as e:
        logger.warning(f"OpenAlex citations query failed: {e}")

    # 2. Fallback to Semantic Scholar if OpenAlex returned nothing
    if not citing_papers and not referenced_papers:
        try:
            ss_data = await _scholar.get_citations(clean_title)
            if ss_data and (ss_data.get("citations") or ss_data.get("references")):
                source_used = "semantic_scholar"
                root_paper["citations"] = ss_data.get("citationCount", root_paper["citations"])
                for c in (ss_data.get("citations") or [])[:limit]:
                    if c.get("title"):
                        citing_papers.append({
                            "title": c.get("title"),
                            "year": str(c.get("year") or ""),
                            "citations": c.get("citationCount", 0),
                            "authors": [a.get("name") for a in c.get("authors", []) if a.get("name")],
                            "source": "semantic_scholar"
                        })
                for r in (ss_data.get("references") or [])[:limit]:
                    if r.get("title"):
                        referenced_papers.append({
                            "title": r.get("title"),
                            "year": str(r.get("year") or ""),
                            "citations": r.get("citationCount", 0),
                            "authors": [a.get("name") for a in r.get("authors", []) if a.get("name")],
                            "source": "semantic_scholar"
                        })
        except Exception as e:
            logger.warning(f"Semantic Scholar fallback failed: {e}")

    # 3. Fallback to Neo4j local graph store
    if not citing_papers and not referenced_papers:
        driver = neo4j_client.get_neo4j_driver()
        if driver:
            try:
                with neo4j_client._get_session(driver) as session:
                    # Papers citing root
                    c_res = session.run("""
                        MATCH (c:Paper)-[:CITES]->(root:Paper)
                        WHERE toLower(root.title) = toLower($title) OR root.title CONTAINS $title
                        RETURN c.title AS title, c.year AS year, c.citations AS citations, c.url AS url LIMIT $limit
                    """, {"title": clean_title, "limit": limit}).data()
                    for rec in c_res:
                        if rec.get("title"):
                            citing_papers.append({
                                "title": rec["title"],
                                "year": str(rec.get("year") or ""),
                                "citations": int(rec.get("citations") or 0),
                                "url": rec.get("url") or "",
                                "source": "neo4j"
                            })

                    # Papers cited by root (references)
                    r_res = session.run("""
                        MATCH (root:Paper)-[:CITES]->(ref:Paper)
                        WHERE toLower(root.title) = toLower($title) OR root.title CONTAINS $title
                        RETURN ref.title AS title, ref.year AS year, ref.citations AS citations, ref.url AS url LIMIT $limit
                    """, {"title": clean_title, "limit": limit}).data()
                    for rec in r_res:
                        if rec.get("title"):
                            referenced_papers.append({
                                "title": rec["title"],
                                "year": str(rec.get("year") or ""),
                                "citations": int(rec.get("citations") or 0),
                                "url": rec.get("url") or "",
                                "source": "neo4j"
                            })
                    if citing_papers or referenced_papers:
                        source_used = "neo4j"
            except Exception as e:
                logger.warning(f"Neo4j citation query error: {e}")

    # 4. Save to Neo4j for persistent knowledge graph expansion
    citation_payload = {
        "citations": [{"title": p["title"]} for p in citing_papers],
        "references": [{"title": p["title"]} for p in referenced_papers]
    }
    try:
        neo4j_client.save_citations_to_neo4j(clean_title, citation_payload)
    except Exception as e:
        logger.debug(f"Save citations to Neo4j skipped: {e}")

    # 5. Build D3 Citation Graph
    graph = _build_rich_citation_graph(root_paper, citing_papers, referenced_papers)

    total_citations = root_paper.get("citations") or len(citing_papers)

    return {
        "success": True,
        "paper": root_paper,
        "citations": citing_papers,
        "references": referenced_papers,
        "citation_count": total_citations,
        "graph": graph,
        "source": source_used
    }


def _build_rich_citation_graph(root_paper: dict, citing_papers: list, referenced_papers: list) -> dict:
    G = nx.DiGraph()
    root_title = root_paper.get("title") or "Selected Paper"
    G.add_node(
        root_title,
        type="root",
        label=root_title[:60],
        citations=root_paper.get("citations", 0),
        year=root_paper.get("year", ""),
        size=18,
        is_top_influential=True
    )

    # Citing papers (pointing TO root paper)
    for c in citing_papers[:15]:
        ctitle = c.get("title")
        if ctitle and ctitle != root_title:
            G.add_node(
                ctitle,
                type="cited_by",
                label=ctitle[:50],
                citations=c.get("citations", 0),
                year=c.get("year", ""),
                size=11
            )
            G.add_edge(ctitle, root_title, relation="cited_by")

    # References (cited BY root paper)
    for r in referenced_papers[:15]:
        rtitle = r.get("title")
        if rtitle and rtitle != root_title:
            G.add_node(
                rtitle,
                type="reference",
                label=rtitle[:50],
                citations=r.get("citations", 0),
                year=r.get("year", ""),
                size=10
            )
            G.add_edge(root_title, rtitle, relation="reference")

    data = nx.node_link_data(G)
    edges = data.get("edges", []) or data.get("links", [])
    data["links"] = edges
    data["edges"] = edges
    return data


# ─────────────────────────────────────────────────────────────────────────────
# 2. AUTHOR SEARCH & RESEARCH PORTFOLIO
# ─────────────────────────────────────────────────────────────────────────────

async def search_author_portfolio(author_name: str, max_results: int = 20) -> Dict[str, Any]:
    """
    Search for a researcher/author across OpenAlex, ArXiv, and local Neo4j.
    Returns:
      - Author Profile (affiliations, h-index, works count, citations)
      - Papers list authored by them (with citations, year, co-authors, PDF links)
      - Co-authors list
      - Interactive Author-Paper-Collaboration Knowledge Graph
    """
    clean_name = (author_name or "").strip()
    if not clean_name:
        return {"author": {}, "papers": [], "co_authors": [], "graph": {"nodes": [], "links": []}}

    author_info = {
        "name": clean_name,
        "affiliations": [],
        "works_count": 0,
        "citation_count": 0,
        "h_index": 0,
        "orcid": ""
    }

    papers_map = {}
    co_author_counts = {}

    # 1. Query OpenAlex Author API
    try:
        encoded_name = urllib.parse.quote(clean_name)
        author_search_url = f"https://api.openalex.org/authors?search={encoded_name}&per-page=3"
        oa_author_data = _fetch_json(author_search_url, timeout=10)

        if oa_author_data and oa_author_data.get("results"):
            best = oa_author_data["results"][0]
            aid = best.get("id", "").split("/")[-1]
            affiliations = [
                aff.get("institution", {}).get("display_name")
                for aff in best.get("affiliations", [])[:3]
                if aff.get("institution", {}).get("display_name")
            ]
            author_info = {
                "name": best.get("display_name") or clean_name,
                "affiliations": affiliations,
                "works_count": int(best.get("works_count") or 0),
                "citation_count": int(best.get("cited_by_count") or 0),
                "h_index": int(best.get("summary_stats", {}).get("h_index") or 0),
                "orcid": best.get("orcid") or ""
            }

            if aid:
                works_url = f"https://api.openalex.org/works?filter=author.id:{aid}&sort=cited_by_count:desc&per-page={max_results}"
                works_data = _fetch_json(works_url, timeout=12)
                if works_data and works_data.get("results"):
                    for w in works_data["results"]:
                        title = (w.get("title") or "").strip()
                        if not title:
                            continue
                        all_authors = [
                            auth.get("author", {}).get("display_name")
                            for auth in w.get("authorships", [])
                            if auth.get("author", {}).get("display_name")
                        ]
                        co_authors = [a for a in all_authors if a.lower() != author_info["name"].lower()]
                        for ca in co_authors:
                            co_author_counts[ca] = co_author_counts.get(ca, 0) + 1

                        pid = (w.get("primary_location") or {}).get("landing_page_url") or (w.get("ids") or {}).get("doi") or w.get("id")
                        papers_map[title.lower()[:70]] = {
                            "id": pid,
                            "title": title,
                            "year": str(w.get("publication_year") or ""),
                            "citations": int(w.get("cited_by_count") or 0),
                            "authors": all_authors,
                            "co_authors": co_authors[:4],
                            "url": pid,
                            "source": "openalex",
                            "summary": ""
                        }
    except Exception as e:
        logger.warning(f"OpenAlex author query error: {e}")

    # 2. Query ArXiv for Author Preprints
    try:
        encoded_arxiv_author = urllib.parse.quote(f'"{clean_name}"')
        arxiv_url = f"http://export.arxiv.org/api/query?search_query=au:{encoded_arxiv_author}&start=0&max_results=10&sortBy=submittedDate&sortOrder=descending"
        req = urllib.request.Request(arxiv_url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                xml = resp.read().decode("utf-8")
                root = ET.fromstring(xml)
                NS = "{http://www.w3.org/2005/Atom}"
                for e in root.findall(f"{NS}entry"):
                    t = e.find(f"{NS}title")
                    title = t.text.strip().replace("\n", " ") if t is not None else ""
                    if not title:
                        continue
                    k = title.lower()[:70]
                    s2 = e.find(f"{NS}summary")
                    summary = s2.text.strip().replace("\n", " ") if s2 is not None else ""
                    i = e.find(f"{NS}id")
                    aid = i.text.strip() if i is not None else ""
                    pub = e.find(f"{NS}published")
                    year = pub.text[:4] if pub is not None else ""
                    authors = [a.find(f"{NS}name").text for a in e.findall(f"{NS}author") if a.find(f"{NS}name") is not None]

                    co_authors = [a for a in authors if clean_name.lower() not in a.lower()]
                    for ca in co_authors:
                        co_author_counts[ca] = co_author_counts.get(ca, 0) + 1

                    if k not in papers_map:
                        papers_map[k] = {
                            "id": aid,
                            "title": title,
                            "year": year,
                            "citations": 0,
                            "authors": authors,
                            "co_authors": co_authors[:4],
                            "url": aid,
                            "source": "arxiv",
                            "summary": summary
                        }
                    else:
                        # Enhance existing with summary if missing
                        if not papers_map[k].get("summary") and summary:
                            papers_map[k]["summary"] = summary
    except Exception as e:
        logger.debug(f"ArXiv author query error: {e}")

    # 3. Check Neo4j Local Graph for already stored papers of this author
    driver = neo4j_client.get_neo4j_driver()
    if driver:
        try:
            with neo4j_client._get_session(driver) as session:
                local_res = session.run("""
                    MATCH (a:Author)-[:AUTHORED]->(p:Paper)
                    WHERE toLower(a.name) CONTAINS toLower($name)
                    OPTIONAL MATCH (co:Author)-[:AUTHORED]->(p) WHERE co.name <> a.name
                    RETURN p.title AS title, p.year AS year, p.citations AS citations,
                           p.url AS url, p.source AS source, collect(DISTINCT co.name) AS coauthors
                    LIMIT 20
                """, {"name": clean_name}).data()

                for row in local_res:
                    title = row.get("title") or ""
                    if not title:
                        continue
                    k = title.lower()[:70]
                    co_auths = [ca for ca in (row.get("coauthors") or []) if ca]
                    for ca in co_auths:
                        co_author_counts[ca] = co_author_counts.get(ca, 0) + 1

                    if k not in papers_map:
                        papers_map[k] = {
                            "id": row.get("url") or title,
                            "title": title,
                            "year": str(row.get("year") or ""),
                            "citations": int(row.get("citations") or 0),
                            "authors": [clean_name] + co_auths,
                            "co_authors": co_auths[:4],
                            "url": row.get("url") or "",
                            "source": row.get("source") or "neo4j",
                            "summary": ""
                        }
        except Exception as e:
            logger.debug(f"Neo4j author lookup error: {e}")

    papers_list = list(papers_map.values())
    # Sort papers by citations desc, then year desc
    papers_list.sort(key=lambda x: (x.get("citations") or 0, x.get("year") or "0"), reverse=True)

    # Top co-authors
    top_co_authors = [
        {"name": name, "collaborations": count}
        for name, count in sorted(co_author_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    ]

    # If works_count or citation_count wasn't available from OpenAlex, derive from found papers
    if not author_info["works_count"]:
        author_info["works_count"] = len(papers_list)
    if not author_info["citation_count"]:
        author_info["citation_count"] = sum(p.get("citations") or 0 for p in papers_list)

    # Ingest into Neo4j & MongoDB
    try:
        neo4j_client.save_knowledge_graph_to_neo4j(
            f"Author:{author_info['name']}",
            papers_list,
            repos=[]
        )
        mongo_client.save_papers_mongo(papers_list)
    except Exception as e:
        logger.debug(f"Persistence of author search skipped: {e}")

    # Build Author Collaboration Graph
    author_graph = _build_author_graph(author_info, papers_list, top_co_authors)

    return {
        "success": True,
        "author": author_info,
        "papers": papers_list,
        "co_authors": top_co_authors,
        "total_papers": len(papers_list),
        "graph": author_graph
    }


def _build_author_graph(author_info: dict, papers: list, co_authors: list) -> dict:
    G = nx.DiGraph()
    author_node = author_info["name"]
    G.add_node(
        author_node,
        type="author",
        label=author_node,
        size=18,
        is_top_influential=True
    )

    # Top papers
    for p in papers[:15]:
        title = p.get("title") or ""
        if title:
            short_title = title[:60]
            G.add_node(
                title,
                type="paper",
                label=short_title,
                year=p.get("year", ""),
                citations=p.get("citations", 0),
                size=11
            )
            G.add_edge(author_node, title, relation="authored")

    # Top co-authors
    for ca in co_authors[:8]:
        caname = ca.get("name")
        if caname and caname != author_node:
            G.add_node(
                caname,
                type="author",
                label=caname,
                size=9
            )
            G.add_edge(author_node, caname, relation="co_authored")

    data = nx.node_link_data(G)
    edges = data.get("edges", []) or data.get("links", [])
    data["links"] = edges
    data["edges"] = edges
    return data
