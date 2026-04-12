from __future__ import annotations

import math
import re
from collections import Counter

from app.schemas.job import ParsedDocument, UsageStatus
from app.services.model_client import ModelApiClient
from app.services.model_config import ModelConfigService

TOKEN_PATTERN = re.compile(r"[a-zA-Z\-]{3,}|[\u4e00-\u9fff]{2,}")
STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "into", "when", "then", "using", "able", "will",
    "project", "document", "process", "workflow", "skill", "guide",
    "项目", "流程", "模板", "处理", "需要", "进行", "以及", "工作", "相关", "一个", "可以", "通过", "能力", "规则",
}


class RetrievalService:
    def __init__(self) -> None:
        self.model_config_service = ModelConfigService()

    def retrieve(self, query: str, documents: list[ParsedDocument], limit: int = 6) -> tuple[list[dict], UsageStatus]:
        chunks = self._chunk_documents(documents)
        if not query.strip() or not chunks:
            return [], UsageStatus(stage="retrieval", kind="embedding", status="skipped", detail="Missing query or chunks.")

        embedded, usage = self._embedding_rank(query, chunks, limit)
        if embedded:
            return embedded, usage
        lexical = self._lexical_rank(query, chunks, limit)
        if usage.status == "fallback":
            usage.detail = f"{usage.detail} Falling back to lexical ranking."
        elif usage.status == "skipped":
            usage.detail = f"{usage.detail} Using lexical ranking only."
        return lexical, usage

    def _chunk_documents(self, documents: list[ParsedDocument], chunk_size: int = 900, overlap: int = 160) -> list[dict]:
        chunks: list[dict] = []
        for document in documents:
            text = document.text_content.strip()
            if not text:
                continue
            normalized = text.replace("\r", " ")
            start = 0
            index = 0
            while start < len(normalized):
                chunk_text = normalized[start:start + chunk_size].strip()
                if chunk_text:
                    chunks.append(
                        {
                            "document_id": document.id,
                            "file_path": document.file_path,
                            "title": document.title,
                            "text": chunk_text,
                            "index": index,
                        }
                    )
                if start + chunk_size >= len(normalized):
                    break
                start += max(1, chunk_size - overlap)
                index += 1
        return chunks

    def _embedding_rank(self, query: str, chunks: list[dict], limit: int) -> tuple[list[dict], UsageStatus]:
        config = self.model_config_service.get()
        client = ModelApiClient(config)
        if not client.embedding_ready():
            return [], UsageStatus(stage="retrieval", kind="embedding", provider=config.provider, status="skipped", detail="Embedding configuration is incomplete.")

        selected_chunks = chunks[:40]
        texts = [query] + [self._chunk_embedding_text(chunk) for chunk in selected_chunks]
        try:
            vectors = client.embed_texts(texts)
        except Exception as exc:
            return [], UsageStatus(stage="retrieval", kind="embedding", provider=config.provider, status="fallback", fallback_used=True, detail=str(exc)[:240])
        if len(vectors) != len(texts):
            return [], UsageStatus(stage="retrieval", kind="embedding", provider=config.provider, status="fallback", fallback_used=True, detail="Embedding response length mismatch.")

        query_vector = vectors[0]
        ranked: list[tuple[float, dict]] = []
        for chunk, vector in zip(selected_chunks, vectors[1:]):
            similarity = self._cosine_similarity(query_vector, vector)
            ranked.append((similarity, chunk))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [self._format_result(chunk, score) for score, chunk in ranked[:limit] if score > 0], UsageStatus(stage="retrieval", kind="embedding", provider=config.provider, used=True, status="used", detail=f"Embedded {len(texts)} texts for chunk retrieval.")

    def _lexical_rank(self, query: str, chunks: list[dict], limit: int) -> list[dict]:
        query_tokens = self._tokens(query)
        if not query_tokens:
            return []
        ranked: list[tuple[float, dict]] = []
        for chunk in chunks:
            text_tokens = self._tokens(f"{chunk['title']}\n{chunk['text']}")
            overlap = sum((query_tokens & text_tokens).values())
            if overlap <= 0:
                continue
            score = overlap / max(1, sum(query_tokens.values()))
            ranked.append((score, chunk))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [self._format_result(chunk, score) for score, chunk in ranked[:limit]]

    def _chunk_embedding_text(self, chunk: dict) -> str:
        return f"title: {chunk['title']}\npath: {chunk['file_path']}\ncontent: {chunk['text']}"

    def _tokens(self, text: str) -> Counter:
        items = [token.lower() for token in TOKEN_PATTERN.findall(text) if token.lower() not in STOPWORDS]
        return Counter(items)

    def _cosine_similarity(self, left: list[float], right: list[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        numerator = sum(a * b for a, b in zip(left, right))
        left_norm = math.sqrt(sum(a * a for a in left))
        right_norm = math.sqrt(sum(b * b for b in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return max(0.0, min(1.0, numerator / (left_norm * right_norm)))

    def _format_result(self, chunk: dict, score: float) -> dict:
        return {
            "document_id": chunk["document_id"],
            "file_path": chunk["file_path"],
            "title": chunk["title"],
            "score": round(score, 4),
            "text": chunk["text"][:700],
        }
