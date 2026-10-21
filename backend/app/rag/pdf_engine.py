import re
import math
import logging
from io import BytesIO
from typing import List, Dict, Any, Optional
import aiohttp
import pypdf

logger = logging.getLogger("pdf_engine")

class PDFChunkStore:
    def __init__(self):
        self.chunks: List[Dict[str, Any]] = []
        self.loaded_papers: List[Dict[str, Any]] = []

    def clear(self):
        self.chunks = []
        self.loaded_papers = []

    def get_stats(self) -> Dict[str, Any]:
        total_pages = sum(p.get("pages", 0) for p in self.loaded_papers)
        return {
            "loaded": len(self.chunks) > 0,
            "total_papers": len(self.loaded_papers),
            "papers": [p.get("name") for p in self.loaded_papers],
            "total_pages": total_pages,
            "total_chunks": len(self.chunks)
        }

    def add_pdf_bytes(self, pdf_bytes: bytes, filename: str) -> Dict[str, Any]:
        reader = pypdf.PdfReader(BytesIO(pdf_bytes))
        num_pages = len(reader.pages)
        new_chunks = []

        chunk_size = 700
        overlap = 120

        for page_idx, page in enumerate(reader.pages):
            page_num = page_idx + 1
            text = page.extract_text() or ""
            # Clean text
            text = re.sub(r"\s+", " ", text).strip()
            if not text:
                continue

            # Sliding window chunking
            start = 0
            while start < len(text):
                end = min(start + chunk_size, len(text))
                chunk_str = text[start:end].strip()
                if len(chunk_str) > 80:
                    new_chunks.append({
                        "id": f"{filename}_p{page_num}_{len(new_chunks)}",
                        "paper": filename,
                        "page": page_num,
                        "text": chunk_str
                    })
                if end == len(text):
                    break
                start += (chunk_size - overlap)

        self.chunks.extend(new_chunks)
        paper_info = {"name": filename, "pages": num_pages, "chunks": len(new_chunks)}
        self.loaded_papers.append(paper_info)
        return paper_info

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if not self.chunks:
            return []

        q_tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
        if not q_tokens:
            return self.chunks[:top_k]

        scored = []
        for chunk in self.chunks:
            c_tokens = re.findall(r"[a-z0-9]+", chunk["text"].lower())
            c_set = set(c_tokens)
            if not c_set:
                continue
            # Term overlap with sub-linear document length normalization
            overlap = len(q_tokens & c_set)
            if overlap == 0:
                continue
            score = overlap / (1 + math.log(1 + len(c_tokens)))
            scored.append((chunk, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [c for c, _ in scored[:top_k]]

pdf_store = PDFChunkStore()

async def download_arxiv_pdf(arxiv_id_or_url: str) -> Optional[bytes]:
    """Download full PDF binary directly from ArXiv."""
    # Extract ArXiv ID (e.g., from 'https://arxiv.org/abs/1706.03762' or '1706.03762' or '1706.03762v5')
    clean = arxiv_id_or_url.strip()
    m = re.search(r"(\d{4}\.\d{4,5}(?:v\d+)?)", clean)
    if m:
        aid = m.group(1)
    else:
        aid = clean.split("/")[-1].replace(".pdf", "")

    pdf_url = f"https://arxiv.org/pdf/{aid}.pdf"
    headers = {"User-Agent": "ResearchIQ/1.0 (academic research tool)"}

    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(pdf_url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as r:
                if r.status == 200:
                    return await r.read()
    except Exception as e:
        logger.warning(f"Could not download ArXiv PDF from {pdf_url}: {e}")
    return None
