from __future__ import annotations

import math
from pathlib import Path

from app.schemas.job import InventorySummary, JobConfig, UsageStatus
from app.services.model_client import ModelApiClient
from app.services.model_config import ModelConfigService


TEXT_EXTENSIONS = {".md", ".txt", ".pdf", ".docx", ".xlsx", ".pptx", ".json", ".yaml", ".yml", ".csv", ".py", ".js", ".ts"}
DOMAIN_KEYWORDS = {
    "report": "executive-reporting",
    "escalation": "customer-escalation",
    "onboarding": "customer-onboarding",
    "pricing": "pricing-approval",
    "contract": "contract-review",
    "runbook": "technical-runbooks",
    "playbook": "operational-playbooks",
}


class InventoryService:
    def __init__(self) -> None:
        self.model_config_service = ModelConfigService()

    def build_summary(self, root_path: str, config: JobConfig) -> InventorySummary:
        root = Path(root_path)
        if not root.exists():
            return InventorySummary(
                total_files=0,
                total_size_bytes=0,
                categories={},
                top_extensions={},
                suggested_domains=[],
                high_priority_files=[],
            )

        total_files = 0
        total_size = 0
        categories: dict[str, int] = {}
        extensions: dict[str, int] = {}
        high_priority_files: list[dict[str, object]] = []
        suggested_domains: dict[str, int] = {}

        for path in root.rglob("*"):
            if not path.is_file() or self._is_excluded(path):
                continue
            if path.stat().st_size > config.max_file_size_mb * 1024 * 1024:
                continue

            total_files += 1
            size = path.stat().st_size
            total_size += size
            ext = path.suffix.lower() or "[none]"
            extensions[ext] = extensions.get(ext, 0) + 1

            category = self._categorize(path)
            categories[category] = categories.get(category, 0) + 1

            rel = path.relative_to(root).as_posix()
            score = self._score(path, rel, ext)
            if score >= 70:
                high_priority_files.append({"path": rel, "score": score, "category": category, "size_bytes": size})

            lowered = rel.lower()
            for keyword, domain in DOMAIN_KEYWORDS.items():
                if keyword in lowered:
                    suggested_domains[domain] = suggested_domains.get(domain, 0) + 1

        high_priority_files = sorted(high_priority_files, key=lambda item: int(item["score"]), reverse=True)[:20]
        top_extensions = dict(sorted(extensions.items(), key=lambda item: item[1], reverse=True)[:12])
        suggested = [domain for domain, _ in sorted(suggested_domains.items(), key=lambda item: item[1], reverse=True)[:8]]

        return InventorySummary(
            total_files=total_files,
            total_size_bytes=total_size,
            categories=categories,
            top_extensions=top_extensions,
            suggested_domains=suggested,
            high_priority_files=high_priority_files,
        )

    def discover_candidate_files(self, root_path: str, config: JobConfig, goal: str = "", limit: int = 24) -> tuple[list[Path], UsageStatus]:
        root = Path(root_path)
        if not root.exists():
            return [], UsageStatus(stage="parse", kind="embedding", status="skipped", detail="Root path does not exist.")

        scored: list[tuple[int, Path]] = []
        candidate_rows: list[tuple[Path, str, int]] = []
        for path in root.rglob("*"):
            if not path.is_file() or self._is_excluded(path):
                continue
            if path.suffix.lower() not in TEXT_EXTENSIONS:
                continue
            if path.stat().st_size > config.max_file_size_mb * 1024 * 1024:
                continue
            rel = path.relative_to(root).as_posix()
            base_score = self._score(path, rel, path.suffix.lower())
            candidate_rows.append((path, rel, base_score))

        semantic_scores, usage = self._semantic_scores(goal, candidate_rows)
        for path, rel, base_score in candidate_rows:
            score = base_score + semantic_scores.get(rel, 0)
            scored.append((score, path))

        return [path for _, path in sorted(scored, key=lambda item: item[0], reverse=True)[:limit]], usage

    def _semantic_scores(self, goal: str, candidate_rows: list[tuple[Path, str, int]]) -> tuple[dict[str, int], UsageStatus]:
        if not goal.strip() or not candidate_rows:
            return {}, UsageStatus(stage="parse", kind="embedding", status="skipped", detail="Missing goal or candidate rows.")

        config = self.model_config_service.get()
        client = ModelApiClient(config)
        if not client.embedding_ready():
            return {}, UsageStatus(stage="parse", kind="embedding", provider=config.provider, status="skipped", detail="Embedding configuration is incomplete.")

        texts = [goal]
        row_keys: list[str] = []
        for path, rel, _ in candidate_rows[:48]:
            texts.append(self._embedding_text(path, rel))
            row_keys.append(rel)

        try:
            vectors = client.embed_texts(texts)
        except Exception as exc:
            return {}, UsageStatus(stage="parse", kind="embedding", provider=config.provider, status="fallback", fallback_used=True, detail=str(exc)[:240])
        if len(vectors) != len(texts):
            return {}, UsageStatus(stage="parse", kind="embedding", provider=config.provider, status="fallback", fallback_used=True, detail="Embedding response length mismatch.")

        goal_vector = vectors[0]
        scores: dict[str, int] = {}
        for rel, vector in zip(row_keys, vectors[1:]):
            similarity = self._cosine_similarity(goal_vector, vector)
            if similarity > 0:
                scores[rel] = round(similarity * 25)
        return scores, UsageStatus(stage="parse", kind="embedding", provider=config.provider, used=True, status="used", detail=f"Embedded {len(texts)} texts for semantic candidate ranking.")

    def _embedding_text(self, path: Path, rel: str) -> str:
        try:
            snippet = path.read_text(encoding="utf-8", errors="ignore")[:1200]
        except Exception:
            snippet = ""
        return f"path: {rel}\nfilename: {path.name}\ncontent: {snippet}"

    def _cosine_similarity(self, left: list[float], right: list[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        numerator = sum(a * b for a, b in zip(left, right))
        left_norm = math.sqrt(sum(a * a for a in left))
        right_norm = math.sqrt(sum(b * b for b in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return max(0.0, min(1.0, numerator / (left_norm * right_norm)))

    def _is_excluded(self, path: Path) -> bool:
        return any(excluded in path.parts for excluded in ["node_modules", ".git", "dist", "build", "archive", "__pycache__"])

    def _categorize(self, path: Path) -> str:
        ext = path.suffix.lower()
        if ext in {".py", ".js", ".ts", ".sh"}:
            return "script"
        if ext in {".md", ".txt", ".pdf", ".docx"}:
            return "knowledge_doc"
        if ext in {".xlsx", ".csv"}:
            return "spreadsheet"
        if ext in {".pptx"}:
            return "slides"
        if ext in {".png", ".jpg", ".jpeg", ".svg"}:
            return "asset"
        if ext in {".zip", ".exe", ".dll"}:
            return "noise"
        return "other"

    def _score(self, path: Path, rel: str, ext: str) -> int:
        score = 20
        lowered = rel.lower()
        if any(part in lowered for part in ["docs", "playbooks", "templates", "knowledge", "cases", "process", "references"]):
            score += 25
        if any(keyword in lowered for keyword in ["playbook", "workflow", "runbook", "guide", "template", "policy", "decision", "escalation", "report"]):
            score += 30
        if ext in TEXT_EXTENSIONS:
            score += 15
        if path.stat().st_size < 8_000_000:
            score += 10
        return min(score, 100)
