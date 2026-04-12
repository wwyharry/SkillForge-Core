from __future__ import annotations

import json
import re
from collections import Counter

from app.schemas.job import EvidenceRecord, ParsedDocument, RetrievalTrace, UsageStatus
from app.services.model_client import ModelApiClient
from app.services.model_config import ModelConfigService
from app.services.retrieval import RetrievalService

STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "into", "when", "then", "using", "able", "will",
    "项目", "流程", "模板", "处理", "需要", "进行", "以及", "工作", "相关", "一个", "可以", "通过", "能力", "规则",
}

RULE_PATTERNS = [
    re.compile(r"\bmust\b", re.IGNORECASE),
    re.compile(r"\bshould\b", re.IGNORECASE),
    re.compile(r"\bapprove\b", re.IGNORECASE),
    re.compile(r"\bescalat", re.IGNORECASE),
    re.compile(r"必须"),
    re.compile(r"应当"),
    re.compile(r"审批"),
    re.compile(r"升级"),
]

THRESHOLD_PATTERNS = [
    re.compile(r"\b\d+(?:\.\d+)?%"),
    re.compile(r"\b\d+(?:\.\d+)?\s?(?:bp|bps|days?|hours?|minutes?|times?|x)\b", re.IGNORECASE),
    re.compile(r"(?:不少于|不低于|高于|低于|超过|至少|至多)\s*\d+(?:\.\d+)?"),
]

TERM_PATTERN = re.compile(r"\b[A-Z]{2,}[A-Z0-9_-]*\b|[A-Za-z][A-Za-z0-9_\-/]{5,}|[\u4e00-\u9fff]{2,10}")
SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?。！？；;])\s+|\n+")


class ExtractionService:
    def __init__(self) -> None:
        self.model_config_service = ModelConfigService()
        self.retrieval = RetrievalService()

    def build_evidences(self, documents: list[ParsedDocument]) -> tuple[list[EvidenceRecord], list[RetrievalTrace], list[UsageStatus]]:
        config = self.model_config_service.get()
        client = ModelApiClient(config)
        if client.is_ready():
            try:
                return self._build_evidences_with_model(documents, client)
            except Exception as exc:
                evidences = self._build_evidences_heuristic(documents)
                return evidences, [], [UsageStatus(stage="extract", kind="chat", provider=config.provider, status="fallback", fallback_used=True, detail=str(exc)[:240])]
        evidences = self._build_evidences_heuristic(documents)
        return evidences, [], [UsageStatus(stage="extract", kind="chat", provider=config.provider, status="skipped", detail="Chat model is not configured.")]

    def _build_evidences_with_model(self, documents: list[ParsedDocument], client: ModelApiClient) -> tuple[list[EvidenceRecord], list[RetrievalTrace], list[UsageStatus]]:
        evidences: list[EvidenceRecord] = []
        traces: list[RetrievalTrace] = []
        usages: list[UsageStatus] = []
        for index, document in enumerate(documents, start=1):
            query = document.title or document.file_path
            retrieved, retrieval_usage = self.retrieval.retrieve(query, documents, limit=6)
            traces.append(RetrievalTrace(scope="extract", query=query, target_id=document.id, items=retrieved))
            usages.append(UsageStatus(stage="extract", kind="embedding", provider=retrieval_usage.provider, used=retrieval_usage.used, fallback_used=retrieval_usage.fallback_used, status=retrieval_usage.status, detail=f"{document.id}: {retrieval_usage.detail}"))
            prompt = self._model_prompt(document, retrieved)
            content = client.chat(
                system_prompt=(
                    "You extract dense structured workflow evidence from repository documents. Return strict JSON only. "
                    "Preserve topic modules, quantitative thresholds, terminology, dependencies, and exceptions."
                ),
                user_prompt=prompt,
                temperature=0.1,
                max_tokens=min(client.config.max_tokens, 1500),
            )
            evidences.append(self._payload_to_evidence(index, document, json.loads(self._extract_json(content))))
        usages.append(UsageStatus(stage="extract", kind="chat", provider=client.config.provider, used=True, status="used", detail=f"Generated evidence for {len(evidences)} documents with external chat model."))
        return evidences, traces, usages

    def _payload_to_evidence(self, index: int, document: ParsedDocument, payload: dict) -> EvidenceRecord:
        sentences = self._sentences(document.text_content[:1800])
        return EvidenceRecord(
            id=f"ev-{index}",
            task=payload.get("task") or self._task_from_document(document, payload.get("capability_hint", "general-operational-skill")),
            subtask=payload.get("subtask") or self._subtask_from_document(document),
            capability_hint=payload.get("capability_hint") or self._capability_hint(document),
            confidence=float(payload.get("confidence") or self._confidence(document)),
            source_path=document.file_path,
            excerpt=document.excerpt,
            workflow_steps=self._coerce_list(payload.get("workflow_steps"), fallback=self._workflow_steps(sentences, document), limit=8),
            decision_rules=self._coerce_list(payload.get("decision_rules"), fallback=self._decision_rules(sentences), limit=10),
            topic_modules=self._coerce_list(payload.get("topic_modules"), fallback=self._topic_modules(document, sentences), limit=8),
            quantitative_signals=self._coerce_list(payload.get("quantitative_signals"), fallback=self._quantitative_signals(sentences), limit=10),
            terminology=self._coerce_list(payload.get("terminology"), fallback=self._terminology(document), limit=12),
            dependencies=self._coerce_list(payload.get("dependencies"), fallback=self._dependencies(sentences), limit=8),
            exceptions=self._coerce_list(payload.get("exceptions"), fallback=self._exceptions(sentences), limit=8),
            source_document_id=document.id,
        )

    def _build_evidences_heuristic(self, documents: list[ParsedDocument]) -> list[EvidenceRecord]:
        evidences: list[EvidenceRecord] = []
        for index, document in enumerate(documents, start=1):
            excerpt = document.text_content[:1800]
            sentences = self._sentences(excerpt)
            capability = self._capability_hint(document)
            evidences.append(
                EvidenceRecord(
                    id=f"ev-{index}",
                    task=self._task_from_document(document, capability),
                    subtask=self._subtask_from_document(document),
                    capability_hint=capability,
                    confidence=self._confidence(document),
                    source_path=document.file_path,
                    excerpt=document.excerpt,
                    workflow_steps=self._workflow_steps(sentences, document),
                    decision_rules=self._decision_rules(sentences),
                    topic_modules=self._topic_modules(document, sentences),
                    quantitative_signals=self._quantitative_signals(sentences),
                    terminology=self._terminology(document),
                    dependencies=self._dependencies(sentences),
                    exceptions=self._exceptions(sentences),
                    source_document_id=document.id,
                )
            )
        return evidences

    def _model_prompt(self, document: ParsedDocument, retrieved: list[dict]) -> str:
        excerpt = document.text_content[:2800]
        related = "\n\n".join(
            f"[{item['file_path']}] score={item['score']}\n{item['text']}" for item in retrieved if item["file_path"] != document.file_path
        ) or "No related chunks retrieved."
        return f"""
Analyze this document and return JSON with keys:
- task
- subtask
- capability_hint
- confidence
- workflow_steps
- decision_rules
- topic_modules
- quantitative_signals
- terminology
- dependencies
- exceptions

Requirements:
- Preserve concrete terminology and module names.
- Preserve thresholds, percentages, timing constraints, counts, and parameter values.
- Preserve conditional logic, escalation rules, and exception handling.
- Keep arrays short but content-dense.
- Do not use placeholders.

Document title: {document.title}
File path: {document.file_path}
Sections: {document.sections}
Primary excerpt:
{excerpt}

Related retrieved chunks:
{related}
""".strip()

    def _sentences(self, text: str) -> list[str]:
        parts = [part.strip() for part in SENTENCE_SPLIT_PATTERN.split(text or "")]
        return [part[:280] for part in parts if len(part) > 12][:24]

    def _task_from_document(self, document: ParsedDocument, capability: str) -> str:
        title = (document.title or "").strip()
        if title:
            return title[:120]
        stem = document.file_path.replace("\\", "/").split("/")[-1].rsplit(".", 1)[0].replace("_", " ").replace("-", " ").strip()
        return (stem or capability or "general workflow task")[:120]

    def _subtask_from_document(self, document: ParsedDocument) -> str:
        if document.sections:
            return str(document.sections[0])[:120]
        sentences = self._sentences(document.text_content[:800])
        return (sentences[0] if sentences else "Review source document details")[:120]

    def _capability_hint(self, document: ParsedDocument) -> str:
        terms = self._terminology(document)[:3]
        if terms:
            return "-".join(term.lower().replace(" ", "-") for term in terms)[:80]
        stem = self._task_from_document(document, "general-operational-skill").lower()
        slug = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", stem).strip("-")
        return slug[:80] or "general-operational-skill"

    def _confidence(self, document: ParsedDocument) -> float:
        base = 0.55
        if document.sections:
            base += 0.1
        if len(document.text_content) > 1200:
            base += 0.15
        if self._quantitative_signals(self._sentences(document.text_content[:1800])):
            base += 0.1
        if self._decision_rules(self._sentences(document.text_content[:1800])):
            base += 0.1
        return min(0.95, round(base, 2))

    def _workflow_steps(self, sentences: list[str], document: ParsedDocument) -> list[str]:
        items = self._dedupe_nonempty(sentences[:6], limit=8)
        return items or [f"Review {self._task_from_document(document, 'workflow')} and extract the actionable sequence."]

    def _decision_rules(self, sentences: list[str]) -> list[str]:
        matches = [sentence for sentence in sentences if any(pattern.search(sentence) for pattern in RULE_PATTERNS)]
        return self._dedupe_nonempty(matches, limit=10)

    def _topic_modules(self, document: ParsedDocument, sentences: list[str]) -> list[str]:
        items: list[str] = []
        items.extend(document.sections[:6])
        items.extend(self._terminology(document)[:6])
        if not items and document.title:
            items.append(document.title)
        return self._dedupe_nonempty(items, limit=8)

    def _quantitative_signals(self, sentences: list[str]) -> list[str]:
        items = [sentence for sentence in sentences if any(pattern.search(sentence) for pattern in THRESHOLD_PATTERNS)]
        return self._dedupe_nonempty(items, limit=10)

    def _terminology(self, document: ParsedDocument) -> list[str]:
        tokens = [token.strip() for token in TERM_PATTERN.findall(f"{document.title}\n{document.text_content[:2000]}")]
        counter = Counter(token for token in tokens if token.lower() not in STOPWORDS and len(token) > 1)
        return [item for item, _count in counter.most_common(12)]

    def _dependencies(self, sentences: list[str]) -> list[str]:
        matches = [sentence for sentence in sentences if re.search(r"\b(before|after|requires?|depends? on|input|approval|owner)\b|依赖|需要|前置", sentence, re.IGNORECASE)]
        return self._dedupe_nonempty(matches, limit=8)

    def _exceptions(self, sentences: list[str]) -> list[str]:
        matches = [sentence for sentence in sentences if re.search(r"\b(except|unless|fallback|otherwise|error|fail)\b|异常|例外|失败|回退", sentence, re.IGNORECASE)]
        return self._dedupe_nonempty(matches, limit=8)

    def _coerce_list(self, value: object, fallback: list[str], limit: int) -> list[str]:
        if isinstance(value, list):
            items = [str(item).strip()[:240] for item in value if str(item).strip()]
            if items:
                return items[:limit]
        return fallback[:limit]

    def _extract_json(self, text: str) -> str:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("Model did not return JSON object")
        return text[start:end + 1]

    def _dedupe_nonempty(self, values: list[str], limit: int) -> list[str]:
        cleaned: list[str] = []
        for value in values:
            text = str(value).strip()
            if not text or text in cleaned:
                continue
            cleaned.append(text[:240])
            if len(cleaned) >= limit:
                break
        return cleaned
