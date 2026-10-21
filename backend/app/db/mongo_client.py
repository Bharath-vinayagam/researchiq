import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pymongo import MongoClient
from pymongo.collection import Collection

logger = logging.getLogger("mongo_client")

_client: Optional[MongoClient] = None

def _get_config():
    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGODB_DB_NAME", "researchiq")
    return uri, db_name

def get_mongo_client() -> Optional[MongoClient]:
    global _client
    if _client is not None:
        return _client
    uri, _ = _get_config()
    try:
        _client = MongoClient(
            uri,
            serverSelectionTimeoutMS=2500,
            connectTimeoutMS=3000,
            socketTimeoutMS=5000,
        )
        return _client
    except Exception as e:
        logger.warning(f"Could not initialize MongoDB client: {e}")
        return None

def get_db():
    client = get_mongo_client()
    if not client:
        return None
    _, db_name = _get_config()
    return client[db_name]

def check_mongo_connection() -> Dict[str, Any]:
    """Test connectivity to MongoDB instance."""
    uri, db_name = _get_config()
    client = get_mongo_client()
    if not client:
        return {"connected": False, "uri": uri, "db": db_name, "error": "Client not initialized"}
    try:
        # ping admin command to test connection
        client.admin.command("ping")
        return {"connected": True, "uri": uri, "db": db_name, "error": None}
    except Exception as e:
        return {"connected": False, "uri": uri, "db": db_name, "error": str(e)}

def init_mongo_schema():
    """Create indexes for high-performance lookups on MongoDB collections."""
    db = get_db()
    if db is None:
        return
    try:
        # Index on papers
        db.papers.create_index("id", unique=True)
        db.papers.create_index("title")
        db.papers.create_index("year")
        # Index on searches
        db.searches.create_index([("created_at", -1)])
        # Index on reports
        db.reports.create_index([("created_at", -1)])
        db.reports.create_index("topic")
        logger.info("MongoDB indexes ensured.")
    except Exception as e:
        logger.debug(f"MongoDB index creation skipped (likely offline): {e}")

def save_papers_mongo(papers: List[Dict[str, Any]]) -> bool:
    """Save or update semi-structured papers in MongoDB."""
    db = get_db()
    if db is None:
        return False
    try:
        for p in papers:
            pid = p.get("id") or p.get("url") or p.get("title", "")
            if not pid:
                continue
            doc = {
                "id": pid,
                "title": p.get("title", ""),
                "summary": p.get("summary", ""),
                "authors": p.get("authors", []),
                "year": str(p.get("year", "")),
                "citations": int(p.get("citations", 0) or 0),
                "url": p.get("url", ""),
                "source": p.get("source", "arxiv"),
                "updated_at": datetime.utcnow()
            }
            db.papers.update_one({"id": pid}, {"$set": doc, "$setOnInsert": {"created_at": datetime.utcnow()}}, upsert=True)
        return True
    except Exception as e:
        logger.warning(f"Error saving papers to MongoDB: {e}")
        return False

def save_search_mongo(query: str, papers: List[Dict[str, Any]], repos: List[Dict[str, Any]]) -> bool:
    """Save search query record with nested paper and repo documents."""
    db = get_db()
    if db is None:
        return False
    try:
        doc = {
            "query": query,
            "total_papers": len(papers),
            "papers": papers[:20],
            "repos": repos,
            "created_at": datetime.utcnow()
        }
        db.searches.insert_one(doc)
        # Also store individual papers in the papers collection
        save_papers_mongo(papers)
        return True
    except Exception as e:
        logger.warning(f"Error saving search to MongoDB: {e}")
        return False

def save_report_mongo(topic: str, rtype: str, content: str, repos: List[Dict[str, Any]] = None, papers: List[Dict[str, Any]] = None) -> Optional[str]:
    """Save generated academic review, survey, or gap report as a MongoDB document."""
    db = get_db()
    if db is None:
        return None
    try:
        doc = {
            "topic": topic,
            "report_type": rtype,
            "content": content,
            "repos": repos or [],
            "papers": papers or [],
            "created_at": datetime.utcnow()
        }
        res = db.reports.insert_one(doc)
        return str(res.inserted_id)
    except Exception as e:
        logger.warning(f"Error saving report to MongoDB: {e}")
        return None

def get_reports_mongo(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve recent reports from MongoDB."""
    db = get_db()
    if db is None:
        return []
    try:
        cursor = db.reports.find({}, {"content": 0, "papers": 0, "repos": 0}).sort("created_at", -1).limit(limit)
        out = []
        for doc in cursor:
            out.append({
                "id": str(doc["_id"]),
                "topic": doc.get("topic", ""),
                "report_type": doc.get("report_type", ""),
                "created_at": doc.get("created_at", "").isoformat() if isinstance(doc.get("created_at"), datetime) else str(doc.get("created_at", ""))
            })
        return out
    except Exception as e:
        logger.warning(f"Error reading reports from MongoDB: {e}")
        return []

def get_report_by_id_mongo(report_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve full report document from MongoDB."""
    db = get_db()
    if db is None:
        return None
    try:
        from bson import ObjectId
        doc = db.reports.find_one({"_id": ObjectId(report_id)})
        if not doc:
            return None
        doc["id"] = str(doc.pop("_id"))
        if isinstance(doc.get("created_at"), datetime):
            doc["created_at"] = doc["created_at"].isoformat()
        return doc
    except Exception as e:
        logger.warning(f"Error reading report by id from MongoDB: {e}")
        return None

def get_searches_mongo(limit: int = 30) -> List[Dict[str, Any]]:
    """Retrieve recent searches from MongoDB."""
    db = get_db()
    if db is None:
        return []
    try:
        cursor = db.searches.find({}, {"papers": 0}).sort("created_at", -1).limit(limit)
        out = []
        for doc in cursor:
            out.append({
                "id": str(doc["_id"]),
                "query": doc.get("query", ""),
                "repos": doc.get("repos", []),
                "total_papers": doc.get("total_papers", 0),
                "created_at": doc.get("created_at", "").isoformat() if isinstance(doc.get("created_at"), datetime) else str(doc.get("created_at", ""))
            })
        return out
    except Exception as e:
        logger.warning(f"Error reading searches from MongoDB: {e}")
        return []

def save_chat_message_mongo(session_id: str, role: str, content: str, sources: List[Dict[str, Any]] = None) -> bool:
    """Save chat session messages in MongoDB."""
    db = get_db()
    if db is None:
        return False
    try:
        doc = {
            "session_id": session_id or "default",
            "role": role,
            "content": content,
            "sources": sources or [],
            "created_at": datetime.utcnow()
        }
        db.chat_sessions.insert_one(doc)
        return True
    except Exception as e:
        logger.warning(f"Error saving chat message to MongoDB: {e}")
        return False

def get_mongo_stats() -> Dict[str, Any]:
    """Retrieve collection counts and status from MongoDB."""
    status = check_mongo_connection()
    if not status["connected"]:
        return {
            "connected": False,
            "uri": status["uri"],
            "db": status["db"],
            "error": status["error"],
            "stats": {"papers": 0, "searches": 0, "reports": 0, "chat_sessions": 0}
        }
    db = get_db()
    try:
        stats = {
            "papers": db.papers.count_documents({}),
            "searches": db.searches.count_documents({}),
            "reports": db.reports.count_documents({}),
            "chat_sessions": db.chat_sessions.count_documents({})
        }
        return {"connected": True, "uri": status["uri"], "db": status["db"], "stats": stats}
    except Exception as e:
        return {"connected": False, "uri": status["uri"], "db": status["db"], "error": str(e), "stats": {}}
