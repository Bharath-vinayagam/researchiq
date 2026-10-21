import os
import logging
from typing import Dict, Any, List, Optional
import networkx as nx
from app.db.neo4j_client import get_neo4j_driver, _get_session

logger = logging.getLogger("graph_analytics")

def compute_graph_analytics(topic: Optional[str] = None, metric: str = "pagerank", limit: int = 30) -> Dict[str, Any]:
    """
    Computes graph centrality algorithms (PageRank, Betweenness, In-Degree, HITS Authorities)
    and community detection across research papers and authors in Neo4j.
    """
    driver = get_neo4j_driver()
    if not driver:
        return _fallback_analytics(topic, metric, limit)

    try:
        with _get_session(driver) as session:
            # 1. Fetch Papers & Citations
            if topic:
                query_cites = """
                MATCH (t:Topic {name: $topic})-[:COVERS]->(p1:Paper)
                OPTIONAL MATCH (p1)-[r:CITES]->(p2:Paper)
                RETURN p1.title AS src, p2.title AS tgt
                """
                query_papers = """
                MATCH (t:Topic {name: $topic})-[:COVERS]->(p:Paper)
                OPTIONAL MATCH (a:Author)-[:AUTHORED]->(p)
                RETURN p.title AS title, p.year AS year, p.url AS url,
                       p.citations AS citations, p.source AS source,
                       collect(DISTINCT a.name) AS authors
                """
                params = {"topic": topic}
            else:
                query_cites = """
                MATCH (p1:Paper)-[r:CITES]->(p2:Paper)
                RETURN p1.title AS src, p2.title AS tgt
                """
                query_papers = """
                MATCH (p:Paper)
                OPTIONAL MATCH (a:Author)-[:AUTHORED]->(p)
                RETURN p.title AS title, p.year AS year, p.url AS url,
                       p.citations AS citations, p.source AS source,
                       collect(DISTINCT a.name) AS authors
                """
                params = {}

            cite_records = session.run(query_cites, params).data()
            paper_records = session.run(query_papers, params).data()

        # Build NetworkX DiGraph
        G = nx.DiGraph()
        paper_metadata = {}

        for p in paper_records:
            title = p.get("title")
            if not title:
                continue
            paper_metadata[title] = {
                "title": title,
                "year": p.get("year") or "",
                "url": p.get("url") or "",
                "citations": int(p.get("citations") or 0),
                "source": p.get("source") or "arxiv",
                "authors": [a for a in (p.get("authors") or []) if a]
            }
            G.add_node(title)

        for c in cite_records:
            src = c.get("src")
            tgt = c.get("tgt")
            if src and tgt:
                G.add_edge(src, tgt)
                if src not in paper_metadata:
                    paper_metadata[src] = {"title": src, "citations": 0, "authors": []}
                if tgt not in paper_metadata:
                    paper_metadata[tgt] = {"title": tgt, "citations": 0, "authors": []}

        if G.number_of_nodes() == 0:
            return _fallback_analytics(topic, metric, limit)

        # 2. Compute Graph Centrality Algorithms
        # PageRank (Recursive prestige - foundational papers)
        try:
            pagerank_scores = nx.pagerank(G, alpha=0.85, max_iter=200)
        except Exception:
            pagerank_scores = {n: 1.0 / len(G) for n in G.nodes}

        # Betweenness Centrality (Bridge papers connecting sub-fields)
        try:
            betweenness_scores = nx.betweenness_centrality(G)
        except Exception:
            betweenness_scores = {n: 0.0 for n in G.nodes}

        # In-degree Centrality (Direct citation dominance)
        try:
            in_degree_scores = nx.in_degree_centrality(G)
        except Exception:
            in_degree_scores = {n: 0.0 for n in G.nodes}

        # HITS Hubs & Authorities
        try:
            hubs, authorities = nx.hits(G, max_iter=150)
        except Exception:
            authorities = pagerank_scores
            hubs = {n: 0.0 for n in G.nodes}

        # 3. Community Detection (Sub-topic Clustering)
        try:
            undirected_G = G.to_undirected()
            communities = list(nx.community.greedy_modularity_communities(undirected_G))
            node_community = {}
            for cid, comm in enumerate(communities):
                for node in comm:
                    node_community[node] = cid + 1
        except Exception:
            node_community = {n: 1 for n in G.nodes}

        # 4. Synthesize Influential Authors
        author_scores = {}
        author_paper_counts = {}
        author_top_papers = {}

        for title, pr_val in pagerank_scores.items():
            meta = paper_metadata.get(title, {})
            for auth in meta.get("authors", []):
                if not auth:
                    continue
                author_scores[auth] = author_scores.get(auth, 0.0) + pr_val
                author_paper_counts[auth] = author_paper_counts.get(auth, 0) + 1
                if auth not in author_top_papers or pr_val > author_top_papers[auth]["score"]:
                    author_top_papers[auth] = {"title": title, "score": pr_val}

        influential_authors = []
        for auth, score in sorted(author_scores.items(), key=lambda x: x[1], reverse=True)[:limit]:
            influential_authors.append({
                "name": auth,
                "score": round(score, 5),
                "papers_count": author_paper_counts.get(auth, 1),
                "top_paper": author_top_papers.get(auth, {}).get("title", "")
            })

        # 5. Build Ranked Influential Papers List
        influential_papers = []
        for node in G.nodes:
            meta = paper_metadata.get(node, {})
            pr = pagerank_scores.get(node, 0.0)
            bc = betweenness_scores.get(node, 0.0)
            deg = in_degree_scores.get(node, 0.0)
            auth = authorities.get(node, 0.0)
            hub = hubs.get(node, 0.0)
            cid = node_community.get(node, 1)

            influential_papers.append({
                "title": node,
                "year": meta.get("year", ""),
                "url": meta.get("url", ""),
                "citations": meta.get("citations", 0),
                "authors": meta.get("authors", [])[:4],
                "pagerank": round(pr, 5),
                "betweenness": round(bc, 5),
                "degree_centrality": round(deg, 5),
                "authority_score": round(auth, 5),
                "hub_score": round(hub, 5),
                "community": cid
            })

        # Sort according to selected metric
        metric_key = {
            "pagerank": "pagerank",
            "betweenness": "betweenness",
            "degree": "degree_centrality",
            "authority": "authority_score"
        }.get(metric.lower(), "pagerank")

        influential_papers.sort(key=lambda x: x.get(metric_key, 0.0), reverse=True)
        top_papers = influential_papers[:limit]

        # 6. D3 Visual Graph Data Generation
        # Node sizing scaled to centrality for visually stunning rendering
        max_pr = max((p["pagerank"] for p in influential_papers), default=1.0) or 1.0

        d3_nodes = []
        node_id_map = set()

        for p in influential_papers:
            nid = p["title"]
            node_id_map.add(nid)
            # Dynamic size based on PageRank (9px minimum, up to 26px for highest PageRank)
            size = 9 + int((p["pagerank"] / max_pr) * 17)
            d3_nodes.append({
                "id": nid,
                "label": nid,
                "type": "paper",
                "year": p["year"],
                "url": p["url"],
                "citations": p["citations"],
                "pagerank": p["pagerank"],
                "betweenness": p["betweenness"],
                "community": p["community"],
                "size": size,
                "is_top_influential": p in top_papers[:5]
            })

        d3_links = []
        for src, tgt in G.edges():
            if src in node_id_map and tgt in node_id_map:
                d3_links.append({
                    "source": src,
                    "target": tgt,
                    "relation": "cites"
                })

        # Overall Topology Summary
        topology = {
            "total_nodes": G.number_of_nodes(),
            "total_edges": G.number_of_edges(),
            "density": round(nx.density(G), 5),
            "num_communities": len(set(node_community.values())),
            "top_metric": metric_key,
            "connected_database": "Neo4j AuraDB"
        }

        return {
            "success": True,
            "metric": metric,
            "topology": topology,
            "influential_papers": top_papers,
            "influential_authors": influential_authors,
            "graph": {
                "nodes": d3_nodes,
                "links": d3_links
            }
        }

    except Exception as e:
        logger.error(f"Error computing Neo4j graph analytics: {e}", exc_info=True)
        return _fallback_analytics(topic, metric, limit)

def write_metrics_to_neo4j() -> Dict[str, Any]:
    """
    Computes PageRank and Betweenness Centrality on the full citation graph
    and writes the calculated scores back onto Neo4j (p:Paper) nodes.
    """
    driver = get_neo4j_driver()
    if not driver:
        return {"success": False, "error": "Neo4j driver offline"}

    try:
        with _get_session(driver) as session:
            cites = session.run("MATCH (s:Paper)-[:CITES]->(t:Paper) RETURN s.title AS src, t.title AS tgt").data()

            G = nx.DiGraph()
            for c in cites:
                if c.get("src") and c.get("tgt"):
                    G.add_edge(c["src"], c["tgt"])

            if G.number_of_nodes() == 0:
                return {"success": False, "message": "No paper citation relationships found to score"}

            pr_scores = nx.pagerank(G, alpha=0.85, max_iter=200)
            bc_scores = nx.betweenness_centrality(G)

            updates = []
            for node in G.nodes:
                updates.append({
                    "title": node,
                    "pagerank": round(pr_scores.get(node, 0.0), 6),
                    "betweenness": round(bc_scores.get(node, 0.0), 6)
                })

            session.run("""
            UNWIND $updates AS item
            MATCH (p:Paper {title: item.title})
            SET p.pagerank = item.pagerank,
                p.betweenness = item.betweenness,
                p.metrics_updated_at = datetime()
            """, {"updates": updates})

        return {
            "success": True,
            "nodes_updated": len(updates),
            "message": f"Successfully updated {len(updates)} papers with PageRank & Betweenness scores in Neo4j AuraDB."
        }
    except Exception as e:
        logger.error(f"Error writing graph metrics to Neo4j: {e}")
        return {"success": False, "error": str(e)}

def _fallback_analytics(topic: Optional[str], metric: str, limit: int) -> Dict[str, Any]:
    """Fallback when Neo4j is empty or offline."""
    return {
        "success": False,
        "metric": metric,
        "topology": {"total_nodes": 0, "total_edges": 0, "density": 0.0, "num_communities": 0},
        "influential_papers": [],
        "influential_authors": [],
        "graph": {"nodes": [], "links": []}
    }
