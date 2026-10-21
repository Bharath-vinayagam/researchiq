import os
import re
import logging
from typing import List, Dict, Any, Optional
import aiohttp

logger = logging.getLogger("hf_mcp")

class HuggingFaceMCP:
    BASE_MODELS = "https://huggingface.co/api/models"
    BASE_DATASETS = "https://huggingface.co/api/datasets"

    def _headers(self) -> Dict[str, str]:
        headers = {"User-Agent": "ResearchIQ/1.0 (academic research platform)"}
        token = os.getenv("HUGGINGFACE_TOKEN") or os.getenv("HF_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token.strip()}"
        return headers

    async def search_models(self, query: str, max_results: int = 6) -> List[Dict[str, Any]]:
        """Search pretrained open-source models on Hugging Face Hub."""
        clean_query = query.strip()
        if not clean_query:
            return []

        params = {
            "search": clean_query,
            "limit": max_results,
            "full": "false",
            "sort": "downloads",
            "direction": "-1"
        }

        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(self.BASE_MODELS, params=params, headers=self._headers(),
                                 timeout=aiohttp.ClientTimeout(total=12)) as r:
                    if r.status != 200:
                        logger.warning(f"Hugging Face models API returned status {r.status}")
                        return []
                    data = await r.json()

            results = []
            for item in data[:max_results]:
                mid = item.get("id") or item.get("_id", "")
                if not mid:
                    continue
                parts = mid.split("/")
                author = parts[0] if len(parts) > 1 else "community"
                name = parts[1] if len(parts) > 1 else mid

                # Look for linked ArXiv paper in tags
                arxiv_id = None
                tags = item.get("tags") or []
                for t in tags:
                    m = re.match(r"^arxiv:([0-9]+\.[0-9]+.*)", str(t))
                    if m:
                        arxiv_id = m.group(1)
                        break

                results.append({
                    "id": mid,
                    "name": name,
                    "author": author,
                    "url": f"https://huggingface.co/{mid}",
                    "downloads": item.get("downloads", 0),
                    "likes": item.get("likes", 0),
                    "pipeline_tag": item.get("pipeline_tag") or "general",
                    "private": item.get("private", False),
                    "tags": tags[:6],
                    "arxiv_id": arxiv_id
                })
            return results
        except Exception as e:
            logger.warning(f"Error querying Hugging Face models for '{query}': {e}")
            return []

    async def search_datasets(self, query: str, max_results: int = 6) -> List[Dict[str, Any]]:
        """Search benchmark and evaluation datasets on Hugging Face Hub."""
        clean_query = query.strip()
        if not clean_query:
            return []

        params = {
            "search": clean_query,
            "limit": max_results,
            "full": "false",
            "sort": "downloads",
            "direction": "-1"
        }

        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(self.BASE_DATASETS, params=params, headers=self._headers(),
                                 timeout=aiohttp.ClientTimeout(total=12)) as r:
                    if r.status != 200:
                        logger.warning(f"Hugging Face datasets API returned status {r.status}")
                        return []
                    data = await r.json()

            results = []
            for item in data[:max_results]:
                did = item.get("id") or item.get("_id", "")
                if not did:
                    continue
                parts = did.split("/")
                author = parts[0] if len(parts) > 1 else "community"
                name = parts[1] if len(parts) > 1 else did

                results.append({
                    "id": did,
                    "name": name,
                    "author": author,
                    "url": f"https://huggingface.co/datasets/{did}",
                    "downloads": item.get("downloads", 0),
                    "likes": item.get("likes", 0),
                    "tags": (item.get("tags") or [])[:5]
                })
            return results
        except Exception as e:
            logger.warning(f"Error querying Hugging Face datasets for '{query}': {e}")
            return []

    async def search_all(self, query: str, max_models: int = 6, max_datasets: int = 6) -> Dict[str, Any]:
        """Fetch both models and datasets concurrently."""
        import asyncio
        models, datasets = await asyncio.gather(
            self.search_models(query, max_models),
            self.search_datasets(query, max_datasets),
            return_exceptions=True
        )
        return {
            "models": models if isinstance(models, list) else [],
            "datasets": datasets if isinstance(datasets, list) else []
        }
