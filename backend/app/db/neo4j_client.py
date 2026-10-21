import os
import logging
from typing import Dict, Any, List, Optional
from neo4j import GraphDatabase, Driver

logger = logging.getLogger("neo4j_client")

_driver: Optional[Driver] = None

def _get_config():
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USERNAME") or os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    database = os.getenv("NEO4J_DATABASE")
    return uri, user, password, database

def get_neo4j_driver() -> Optional[Driver]:
    global _driver
    if _driver is not None:
        return _driver
    uri, user, password, _ = _get_config()
    try:
        _driver = GraphDatabase.driver(
            uri,
            auth=(user, password),
            max_connection_lifetime=300,
            max_connection_pool_size=50,
            connection_acquisition_timeout=10,
        )
        return _driver
    except Exception as e:
        logger.warning(f"Could not initialize Neo4j driver: {e}")
        return None

def _get_session(driver: Driver):
    _, _, _, database = _get_config()
    if database:
        return driver.session(database=database)
    return driver.session()

def check_neo4j_connection() -> Dict[str, Any]:
    """Test connectivity to Neo4j instance."""
    uri, _, _, _ = _get_config()
    driver = get_neo4j_driver()
    if not driver:
        return {"connected": False, "uri": uri, "error": "Driver not initialized"}
    try:
        driver.verify_connectivity()
        with _get_session(driver) as session:
            result = session.run("RETURN 1 AS test").single()
            if result and result["test"] == 1:
                return {"connected": True, "uri": uri, "error": None}
    except Exception as e:
        return {"connected": False, "uri": uri, "error": str(e)}
    return {"connected": False, "uri": uri, "error": "Unknown connectivity failure"}

def init_neo4j_schema():
    """Create constraints and indexes for high-performance lookups."""
    driver = get_neo4j_driver()
    if not driver:
        return
    try:
        with _get_session(driver) as session:
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (p:Paper) REQUIRE p.id IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (t:Topic) REQUIRE t.name IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (a:Author) REQUIRE a.name IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (r:Repository) REQUIRE r.name IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (m:Model) REQUIRE m.id IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (d:Dataset) REQUIRE d.id IS UNIQUE")
            logger.info("Neo4j schema constraints ensured.")
    except Exception as e:
        logger.debug(f"Neo4j schema init skipped (likely offline): {e}")

def save_knowledge_graph_to_neo4j(topic: str, papers: List[Dict[str, Any]], repos: List[Dict[str, Any]] = None,
                                  models: List[Dict[str, Any]] = None, datasets: List[Dict[str, Any]] = None) -> bool:
    """
    Ingest a research topic, its retrieved papers, authors, GitHub implementations,
    Hugging Face models, and datasets into the Neo4j graph database.
    """
    driver = get_neo4j_driver()
    if not driver:
        return False
    repos = repos or []
    models = models or []
    datasets = datasets or []
    try:
        with _get_session(driver) as session:
            # 1. Merge Topic
            session.run(
                "MERGE (t:Topic {name: $topic}) ON CREATE SET t.created_at = datetime()",
                {"topic": topic}
            )

            # 2. Merge Papers and Authors
            for p in papers:
                pid = p.get("id") or p.get("url") or p.get("title", "")
                if not pid:
                    continue
                title = (p.get("title") or "")[:200]
                year = str(p.get("year") or "")
                summary = (p.get("summary") or "")[:500]
                citations = int(p.get("citations") or 0)
                source = p.get("source") or "arxiv"
                url = p.get("url") or pid

                session.run(
                    """
                    MATCH (t:Topic {name: $topic})
                    MERGE (p:Paper {id: $pid})
                    ON CREATE SET p.title = $title, p.year = $year, p.summary = $summary,
                                  p.citations = $citations, p.source = $source, p.url = $url,
                                  p.created_at = datetime()
                    ON MATCH SET p.title = $title, p.year = $year, p.citations = $citations, p.url = $url
                    MERGE (t)-[:COVERS]->(p)
                    """,
                    {
                        "topic": topic, "pid": pid, "title": title, "year": year,
                        "summary": summary, "citations": citations, "source": source, "url": url
                    }
                )

                for author_name in (p.get("authors") or [])[:5]:
                    if not author_name or not author_name.strip():
                        continue
                    session.run(
                        """
                        MATCH (p:Paper {id: $pid})
                        MERGE (a:Author {name: $name})
                        MERGE (a)-[:AUTHORED]->(p)
                        """,
                        {"pid": pid, "name": author_name.strip()}
                    )

            # 3. Merge Repositories
            for r in repos:
                rname = r.get("name")
                if not rname:
                    continue
                rurl = r.get("url") or ""
                stars = int(r.get("stars") or 0)
                language = r.get("language") or ""
                description = (r.get("description") or "")[:300]

                session.run(
                    """
                    MATCH (t:Topic {name: $topic})
                    MERGE (repo:Repository {name: $name})
                    ON CREATE SET repo.url = $url, repo.stars = $stars, repo.language = $language,
                                  repo.description = $description, repo.created_at = datetime()
                    ON MATCH SET repo.stars = $stars, repo.url = $url
                    MERGE (t)-[:HAS_IMPLEMENTATION]->(repo)
                    """,
                    {
                        "topic": topic, "name": rname, "url": rurl,
                        "stars": stars, "language": language, "description": description
                    }
                )
            # 4. Merge Hugging Face Models
            for m in models:
                mid = m.get("id")
                if not mid:
                    continue
                mname = m.get("name") or mid
                murl = m.get("url") or f"https://huggingface.co/{mid}"
                downloads = int(m.get("downloads") or 0)
                likes = int(m.get("likes") or 0)
                task = m.get("pipeline_tag") or "general"
                author = m.get("author") or ""

                session.run(
                    """
                    MATCH (t:Topic {name: $topic})
                    MERGE (model:Model {id: $mid})
                    ON CREATE SET model.name = $name, model.url = $url, model.downloads = $downloads,
                                  model.likes = $likes, model.task = $task, model.author = $author,
                                  model.created_at = datetime()
                    ON MATCH SET model.downloads = $downloads, model.likes = $likes, model.url = $url
                    MERGE (t)-[:HAS_MODEL]->(model)
                    """,
                    {
                        "topic": topic, "mid": mid, "name": mname, "url": murl,
                        "downloads": downloads, "likes": likes, "task": task, "author": author
                    }
                )

            # 5. Merge Hugging Face Datasets
            for d in datasets:
                did = d.get("id")
                if not did:
                    continue
                dname = d.get("name") or did
                durl = d.get("url") or f"https://huggingface.co/datasets/{did}"
                downloads = int(d.get("downloads") or 0)
                likes = int(d.get("likes") or 0)

                session.run(
                    """
                    MATCH (t:Topic {name: $topic})
                    MERGE (ds:Dataset {id: $did})
                    ON CREATE SET ds.name = $name, ds.url = $url, ds.downloads = $downloads,
                                  ds.likes = $likes, ds.created_at = datetime()
                    ON MATCH SET ds.downloads = $downloads, ds.likes = $likes, ds.url = $url
                    MERGE (t)-[:USES_DATASET]->(ds)
                    """,
                    {
                        "topic": topic, "did": did, "name": dname, "url": durl,
                        "downloads": downloads, "likes": likes
                    }
                )
        return True
    except Exception as e:
        logger.warning(f"Error saving knowledge graph to Neo4j: {e}")
        return False

def save_citations_to_neo4j(paper_title: str, citation_data: Dict[str, Any]) -> bool:
    """Ingest citation network (citations and references) into Neo4j."""
    driver = get_neo4j_driver()
    if not driver:
        return False
    try:
        with _get_session(driver) as session:
            # Merge root paper
            session.run(
                "MERGE (root:Paper {title: $title})",
                {"title": paper_title}
            )

            # Citations (Papers that cite root)
            for c in (citation_data.get("citations") or [])[:25]:
                ctitle = c.get("title")
                if ctitle:
                    session.run(
                        """
                        MATCH (root:Paper {title: $root_title})
                        MERGE (c:Paper {title: $ctitle})
                        MERGE (c)-[:CITES]->(root)
                        """,
                        {"root_title": paper_title, "ctitle": ctitle}
                    )

            # References (Papers cited by root)
            for r in (citation_data.get("references") or [])[:25]:
                rtitle = r.get("title")
                if rtitle:
                    session.run(
                        """
                        MATCH (root:Paper {title: $root_title})
                        MERGE (ref:Paper {title: $rtitle})
                        MERGE (root)-[:CITES]->(ref)
                        """,
                        {"root_title": paper_title, "rtitle": rtitle}
                    )
        return True
    except Exception as e:
        logger.warning(f"Error saving citations to Neo4j: {e}")
        return False

def get_knowledge_graph_from_neo4j(topic: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve knowledge graph for a topic from Neo4j formatted for D3 graph rendering:
    { "nodes": [...], "links": [...] }
    """
    driver = get_neo4j_driver()
    if not driver:
        return None
    try:
        with _get_session(driver) as session:
            result = session.run(
                """
                MATCH (t:Topic {name: $topic})
                OPTIONAL MATCH (t)-[:COVERS]->(p:Paper)
                OPTIONAL MATCH (a:Author)-[:AUTHORED]->(p)
                OPTIONAL MATCH (t)-[:HAS_IMPLEMENTATION]->(r:Repository)
                OPTIONAL MATCH (t)-[:HAS_MODEL]->(m:Model)
                OPTIONAL MATCH (t)-[:USES_DATASET]->(d:Dataset)
                RETURN t, collect(DISTINCT p) as papers, collect(DISTINCT a) as authors,
                       collect(DISTINCT r) as repos, collect(DISTINCT m) as models,
                       collect(DISTINCT d) as datasets
                """,
                {"topic": topic}
            ).single()

            if not result or not result["t"]:
                return None

            nodes = []
            links = []
            node_ids = set()

            topic_id = f"TOPIC:{topic}"
            nodes.append({"id": topic_id, "type": "topic", "label": topic, "centrality": 1.0})
            node_ids.add(topic_id)

            for p in result["papers"]:
                if not p:
                    continue
                pid = p.get("title", "")[:80] or p.get("id")
                if pid and pid not in node_ids:
                    node_ids.add(pid)
                    nodes.append({
                        "id": pid,
                        "type": "paper",
                        "year": p.get("year", ""),
                        "url": p.get("url", ""),
                        "citations": p.get("citations", 0),
                        "source": p.get("source", "arxiv")
                    })
                    links.append({"source": topic_id, "target": pid, "relation": "related"})

            for a in result["authors"]:
                if not a:
                    continue
                aname = a.get("name")
                if aname and aname not in node_ids:
                    node_ids.add(aname)
                    nodes.append({"id": aname, "type": "author"})

            # Fetch author relationships
            author_rel_res = session.run(
                """
                MATCH (a:Author)-[:AUTHORED]->(p:Paper)<-[:COVERS]-(t:Topic {name: $topic})
                RETURN a.name as author, p.title as paper
                """,
                {"topic": topic}
            )
            for rec in author_rel_res:
                auth = rec["author"]
                paper_id = (rec["paper"] or "")[:80]
                if auth in node_ids and paper_id in node_ids:
                    links.append({"source": auth, "target": paper_id, "relation": "authored"})

            for r in result["repos"]:
                if not r:
                    continue
                rname = r.get("name")
                if rname and rname not in node_ids:
                    node_ids.add(rname)
                    nodes.append({
                        "id": rname,
                        "type": "repo",
                        "url": r.get("url", ""),
                        "stars": r.get("stars", 0)
                    })
                    links.append({"source": topic_id, "target": rname, "relation": "implementation"})

            for m in (result.get("models") or []):
                if not m:
                    continue
                mid = m.get("id") or m.get("name")
                if mid and mid not in node_ids:
                    node_ids.add(mid)
                    nodes.append({
                        "id": mid,
                        "label": m.get("name") or mid,
                        "type": "model",
                        "url": m.get("url", ""),
                        "downloads": m.get("downloads", 0),
                        "likes": m.get("likes", 0)
                    })
                    links.append({"source": topic_id, "target": mid, "relation": "model"})

            for d in (result.get("datasets") or []):
                if not d:
                    continue
                did = d.get("id") or d.get("name")
                if did and did not in node_ids:
                    node_ids.add(did)
                    nodes.append({
                        "id": did,
                        "label": d.get("name") or did,
                        "type": "dataset",
                        "url": d.get("url", ""),
                        "downloads": d.get("downloads", 0)
                    })
                    links.append({"source": topic_id, "target": did, "relation": "dataset"})

            return {"directed": True, "multigraph": False, "graph": {}, "nodes": nodes, "links": links}
    except Exception as e:
        logger.warning(f"Error fetching knowledge graph from Neo4j: {e}")
        return None

def get_multi_hop_citations_from_neo4j(paper_title: str, hops: int = 2) -> Optional[Dict[str, Any]]:
    """
    Perform multi-hop citation graph traversal in Neo4j.
    Returns { "nodes": [...], "links": [...], "hops": hops }
    """
    driver = get_neo4j_driver()
    if not driver:
        return None
    try:
        with _get_session(driver) as session:
            query = f"""
            MATCH path = (root:Paper)-[r:CITES*1..{min(max(hops, 1), 3)}]-(related:Paper)
            WHERE root.title = $title OR root.title CONTAINS $title
            RETURN path LIMIT 60
            """
            result = session.run(query, {"title": paper_title})

            nodes = {}
            links = []
            seen_edges = set()

            for record in result:
                path = record["path"]
                for node in path.nodes:
                    title = node.get("title", "")
                    if title and title not in nodes:
                        nodes[title] = {
                            "id": title,
                            "type": "paper" if title != paper_title else "root",
                            "citations": node.get("citations", 0),
                            "year": node.get("year", ""),
                        }
                for rel in path.relationships:
                    start_title = rel.start_node.get("title", "")
                    end_title = rel.end_node.get("title", "")
                    edge_key = (start_title, end_title)
                    if start_title and end_title and edge_key not in seen_edges:
                        seen_edges.add(edge_key)
                        links.append({
                            "source": start_title,
                            "target": end_title,
                            "relation": "cites"
                        })

            if not nodes:
                return None

            return {
                "nodes": list(nodes.values()),
                "links": links,
                "hops": hops,
                "root": paper_title
            }
    except Exception as e:
        logger.warning(f"Error executing multi-hop citation query in Neo4j: {e}")
        return None

def get_neo4j_stats() -> Dict[str, Any]:
    """Retrieve node and relationship statistics from Neo4j."""
    status = check_neo4j_connection()
    if not status["connected"]:
        return {
            "connected": False,
            "uri": status["uri"],
            "error": status["error"],
            "stats": {"papers": 0, "authors": 0, "topics": 0, "repos": 0, "relationships": 0}
        }
    driver = get_neo4j_driver()
    stats = {}
    try:
        with _get_session(driver) as session:
            stats["papers"] = session.run("MATCH (p:Paper) RETURN count(p) as c").single()["c"]
            stats["authors"] = session.run("MATCH (a:Author) RETURN count(a) as c").single()["c"]
            stats["topics"] = session.run("MATCH (t:Topic) RETURN count(t) as c").single()["c"]
            stats["repos"] = session.run("MATCH (r:Repository) RETURN count(r) as c").single()["c"]
            stats["relationships"] = session.run("MATCH ()-[r]->() RETURN count(r) as c").single()["c"]
            return {"connected": True, "uri": status["uri"], "stats": stats}
    except Exception as e:
        return {"connected": False, "uri": status["uri"], "error": str(e), "stats": {}}
