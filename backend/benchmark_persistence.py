"""
Benchmark Suite: Relational (SQLite) vs Graph (Neo4j)
Protocol as defined in ResearchIQ Review II Report:
- Ingestion Latency & Throughput (100 to 500+ papers)
- 1-Hop, 2-Hop, and 3-Hop Citation Traversal
- Subgraph Extraction for Knowledge Graph Visualizations
"""

import os
import sys
import time
import json
import sqlite3

# Ensure backend root is on python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

from app.db import neo4j_client
from app.db.database import DB_PATH, _con

def generate_synthetic_dataset(num_papers=100):
    papers = []
    for i in range(1, num_papers + 1):
        papers.append({
            "id": f"arxiv:2401.{10000 + i}",
            "title": f"Paper {i}: Advances in Research Intelligence Part {i}",
            "year": str(2020 + (i % 5)),
            "summary": f"This is the abstract summary for paper {i} focusing on neural graphs.",
            "citations": (i * 7) % 150,
            "source": "arxiv",
            "url": f"https://arxiv.org/abs/2401.{10000 + i}",
            "authors": [f"Author_{(i % 15) + 1}", f"Author_{((i + 3) % 15) + 1}"]
        })
    return papers

def generate_citation_network(papers):
    citations = {}
    for i, p in enumerate(papers):
        # Cite previous papers to form paths
        refs = [papers[j]["title"] for j in range(max(0, i - 4), i)]
        citations[p["title"]] = {
            "citations": [],
            "references": [{"title": r} for r in refs]
        }
    return citations

def benchmark_sqlite(papers, citations, runs=5):
    con = _con()
    # Ingestion benchmark
    t0 = time.perf_counter()
    con.execute("CREATE TABLE IF NOT EXISTS bench_citations (paper TEXT, ref TEXT)")
    con.execute("DELETE FROM bench_citations")
    for title, data in citations.items():
        for r in data.get("references", []):
            con.execute("INSERT INTO bench_citations VALUES (?, ?)", (title, r["title"]))
    con.commit()
    t_ingest = (time.perf_counter() - t0) * 1000

    # 1-Hop query
    t0 = time.perf_counter()
    for _ in range(runs):
        con.execute("SELECT ref FROM bench_citations WHERE paper = ?", (papers[-1]["title"],)).fetchall()
    t_1hop = ((time.perf_counter() - t0) / runs) * 1000

    # 2-Hop recursive query
    t0 = time.perf_counter()
    for _ in range(runs):
        con.execute("""
            SELECT b2.ref FROM bench_citations b1
            JOIN bench_citations b2 ON b1.ref = b2.paper
            WHERE b1.paper = ?
        """, (papers[-1]["title"],)).fetchall()
    t_2hop = ((time.perf_counter() - t0) / runs) * 1000

    # 3-Hop recursive query
    t0 = time.perf_counter()
    for _ in range(runs):
        con.execute("""
            SELECT b3.ref FROM bench_citations b1
            JOIN bench_citations b2 ON b1.ref = b2.paper
            JOIN bench_citations b3 ON b2.ref = b3.paper
            WHERE b1.paper = ?
        """, (papers[-1]["title"],)).fetchall()
    t_3hop = ((time.perf_counter() - t0) / runs) * 1000

    con.close()
    return {
        "engine": "SQLite",
        "ingestion_ms": round(t_ingest, 2),
        "hop1_ms": round(t_1hop, 3),
        "hop2_ms": round(t_2hop, 3),
        "hop3_ms": round(t_3hop, 3)
    }

def benchmark_neo4j(papers, citations, runs=5):
    status = neo4j_client.check_neo4j_connection()
    if not status["connected"]:
        return {
            "engine": "Neo4j (Offline)",
            "error": status["error"],
            "ingestion_ms": "N/A",
            "hop1_ms": "N/A",
            "hop2_ms": "N/A",
            "hop3_ms": "N/A"
        }

    # Ingestion benchmark
    t0 = time.perf_counter()
    neo4j_client.save_knowledge_graph_to_neo4j("Benchmark Topic", papers, [])
    for title, data in citations.items():
        neo4j_client.save_citations_to_neo4j(title, data)
    t_ingest = (time.perf_counter() - t0) * 1000

    target = papers[-1]["title"]

    # 1-Hop Cypher
    t0 = time.perf_counter()
    for _ in range(runs):
        neo4j_client.get_multi_hop_citations_from_neo4j(target, hops=1)
    t_1hop = ((time.perf_counter() - t0) / runs) * 1000

    # 2-Hop Cypher
    t0 = time.perf_counter()
    for _ in range(runs):
        neo4j_client.get_multi_hop_citations_from_neo4j(target, hops=2)
    t_2hop = ((time.perf_counter() - t0) / runs) * 1000

    # 3-Hop Cypher
    t0 = time.perf_counter()
    for _ in range(runs):
        neo4j_client.get_multi_hop_citations_from_neo4j(target, hops=3)
    t_3hop = ((time.perf_counter() - t0) / runs) * 1000

    return {
        "engine": "Neo4j",
        "ingestion_ms": round(t_ingest, 2),
        "hop1_ms": round(t_1hop, 3),
        "hop2_ms": round(t_2hop, 3),
        "hop3_ms": round(t_3hop, 3)
    }

if __name__ == "__main__":
    count = 100
    print(f"\n==========================================================")
    print(f" ResearchIQ Persistence Benchmark Suite ({count} papers)")
    print(f"==========================================================\n")
    papers = generate_synthetic_dataset(count)
    citations = generate_citation_network(papers)

    print("Running SQLite benchmarks...")
    res_sql = benchmark_sqlite(papers, citations)

    print("Running Neo4j benchmarks...")
    res_neo = benchmark_neo4j(papers, citations)

    print("\n---------------- RESULTS ----------------")
    print(f"{'Metric / Operation':<25} | {'SQLite (Baseline)':<18} | {'Neo4j (Graph NoSQL)':<18}")
    print(f"{'-'*25}-|-{'-'*18}-|-{'-'*18}")
    print(f"{'Ingestion Latency':<25} | {str(res_sql['ingestion_ms'])+' ms':<18} | {str(res_neo['ingestion_ms'])+(' ms' if isinstance(res_neo['ingestion_ms'], (int,float)) else ''):<18}")
    print(f"{'1-Hop Citation Query':<25} | {str(res_sql['hop1_ms'])+' ms':<18} | {str(res_neo['hop1_ms'])+(' ms' if isinstance(res_neo['hop1_ms'], (int,float)) else ''):<18}")
    print(f"{'2-Hop Citation Traversal':<25} | {str(res_sql['hop2_ms'])+' ms':<18} | {str(res_neo['hop2_ms'])+(' ms' if isinstance(res_neo['hop2_ms'], (int,float)) else ''):<18}")
    print(f"{'3-Hop Citation Traversal':<25} | {str(res_sql['hop3_ms'])+' ms':<18} | {str(res_neo['hop3_ms'])+(' ms' if isinstance(res_neo['hop3_ms'], (int,float)) else ''):<18}")
    print("-----------------------------------------\n")
    if "error" in res_neo:
        print(f"[Note] Neo4j Status: {res_neo['error']}. Once Neo4j Desktop or AuraDB is running, rerun this script to capture live numbers.")
