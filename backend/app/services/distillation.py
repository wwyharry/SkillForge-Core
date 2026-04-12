from __future__ import annotations

import json
from collections import defaultdict

from app.schemas.job import CapabilityCluster, EvidenceRecord, ResourcePlan, SkillPlan, UsageStatus
from app.services.model_client import ModelApiClient
from app.services.model_config import ModelConfigService


class DistillationService:
    def __init__(self) -> None:
        self.model_config_service = ModelConfigService()

    def build_capabilities(self, evidences: list[EvidenceRecord]) -> tuple[list[CapabilityCluster], list[UsageStatus]]:
        config = self.model_config_service.get()
        client = ModelApiClient(config)
        if client.is_ready() and evidences:
            try:
                capabilities = self._build_capabilities_with_model(evidences, client)
                return capabilities, [UsageStatus(stage="cluster", kind="chat", provider=config.provider, used=True, status="used", detail=f"Clustered {len(evidences)} evidence records with external chat model.")]
            except Exception as exc:
                return self._build_capabilities_heuristic(evidences), [UsageStatus(stage="cluster", kind="chat", provider=config.provider, status="fallback", fallback_used=True, detail=str(exc)[:240])]
        return self._build_capabilities_heuristic(evidences), [UsageStatus(stage="cluster", kind="chat", provider=config.provider, status="skipped", detail="Chat model is not configured.")]

    def _build_capabilities_with_model(self, evidences: list[EvidenceRecord], client: ModelApiClient) -> list[CapabilityCluster]:
        prompt_payload = [
            {
                "id": item.id,
                "task": item.task,
                "subtask": item.subtask,
                "capability_hint": item.capability_hint,
                "decision_rules": item.decision_rules,
                "workflow_steps": item.workflow_steps,
                "topic_modules": item.topic_modules,
                "quantitative_signals": item.quantitative_signals,
                "terminology": item.terminology,
                "dependencies": item.dependencies,
                "exceptions": item.exceptions,
                "excerpt": item.excerpt,
                "source_path": item.source_path,
            }
            for item in evidences[:40]
        ]
        content = client.chat(
            system_prompt="Group workflow evidence into reusable capabilities. Return strict JSON array only.",
            user_prompt=(
                "Return a JSON array. Each item must contain: name, summary, evidence_ids, core_tasks, rules, suggested_packaging.\n"
                "Make names concrete and domain-specific. Preserve cross-module relations, thresholds, terminology, and exceptions in the grouping.\n"
                f"Evidence:\n{json.dumps(prompt_payload, ensure_ascii=False)}"
            ),
            temperature=0.2,
            max_tokens=min(client.config.max_tokens, 2000),
        )
        items = json.loads(self._extract_json_array(content))
        capabilities: list[CapabilityCluster] = []
        for index, item in enumerate(items, start=1):
            capabilities.append(
                CapabilityCluster(
                    id=f"cap-{index}",
                    name=str(item.get("name") or f"capability-{index}").strip().replace(" ", "-"),
                    summary=str(item.get("summary") or "Reusable workflow capability.").strip(),
                    evidence_ids=self._coerce_list(item.get("evidence_ids"), [e.id for e in evidences[:2]]),
                    core_tasks=self._coerce_list(item.get("core_tasks"), [evidences[0].task]),
                    rules=self._coerce_list(item.get("rules"), evidences[0].decision_rules[:3] or ["Review the source evidence."]),
                    suggested_packaging=str(item.get("suggested_packaging") or "standalone_skill").strip(),
                )
            )
        return capabilities or self._build_capabilities_heuristic(evidences)

    def _build_capabilities_heuristic(self, evidences: list[EvidenceRecord]) -> list[CapabilityCluster]:
        grouped: dict[str, list[EvidenceRecord]] = defaultdict(list)
        for evidence in evidences:
            grouped[evidence.capability_hint].append(evidence)

        capabilities: list[CapabilityCluster] = []
        for index, (name, items) in enumerate(grouped.items(), start=1):
            rules: list[str] = []
            tasks: list[str] = []
            evidence_ids: list[str] = []
            for item in items:
                rules.extend(item.decision_rules)
                tasks.append(item.task)
                evidence_ids.append(item.id)
            capabilities.append(
                CapabilityCluster(
                    id=f"cap-{index}",
                    name=name,
                    summary=f"Reusable workflow distilled from {len(items)} source documents related to {name}.",
                    evidence_ids=evidence_ids,
                    core_tasks=list(dict.fromkeys(tasks))[:6],
                    rules=list(dict.fromkeys(rules))[:8],
                    suggested_packaging="standalone_skill" if len(items) < 4 else "skill_family",
                )
            )
        return capabilities

    def build_skill_plans(self, capabilities: list[CapabilityCluster], evidences: list[EvidenceRecord]) -> list[SkillPlan]:
        evidence_by_id = {item.id: item for item in evidences}
        plans: list[SkillPlan] = []
        for capability in capabilities:
            related = [evidence_by_id[eid] for eid in capability.evidence_ids if eid in evidence_by_id]
            skill_name = capability.name.replace("_", "-")
            trigger_conditions = self._trigger_conditions(capability, related)
            workflow_outline = self._workflow_outline(related)
            decision_logic = self._decision_logic(capability, related)
            boundaries = self._boundaries(capability, related)
            key_terms = self._key_terms(related)
            quantitative_signals = self._quantitative_signals(related)
            dependencies = self._dependencies(related)
            exceptions = self._exceptions(related)
            plans.append(
                SkillPlan(
                    id=f"plan-{capability.id}",
                    skill_name=skill_name,
                    description_draft=self._description(capability, trigger_conditions, boundaries, quantitative_signals),
                    skill_md_topics=[
                        "trigger conditions",
                        "workflow",
                        "decision logic",
                        "references",
                        "examples",
                        "boundaries",
                        "terminology",
                        "quantitative signals",
                    ],
                    trigger_conditions=trigger_conditions,
                    workflow_outline=workflow_outline,
                    decision_logic=decision_logic,
                    boundaries=boundaries,
                    key_terms=key_terms,
                    quantitative_signals=quantitative_signals,
                    dependencies=dependencies,
                    exceptions=exceptions,
                    references=[
                        ResourcePlan(filename="decision-table.md", purpose="Concrete rules, thresholds, branching conditions, and escalation logic"),
                        ResourcePlan(filename="source-map.md", purpose="Coverage map from distilled guidance back to source documents and sections"),
                        ResourcePlan(filename="examples.md", purpose="Positive examples, negative examples, and edge-case examples with expected handling"),
                    ],
                    scripts=[
                        ResourcePlan(filename="analyze_inputs.py", purpose="Deterministic extraction of key inputs, thresholds, terminology flags, and gating conditions"),
                    ],
                    assets=[
                        ResourcePlan(filename="output-template.md", purpose="Output skeleton listing required sections, fields, metrics, dependencies, and references"),
                    ],
                    source_evidence_ids=capability.evidence_ids,
                )
            )
        return plans

    def _description(self, capability: CapabilityCluster, trigger_conditions: list[str], boundaries: list[str], quantitative_signals: list[str]) -> str:
        trigger_text = "; ".join(trigger_conditions[:3]) or "domain-specific requests"
        boundary_text = "; ".join(boundaries[:2]) or "handle only the documented workflow"
        metric_text = "; ".join(quantitative_signals[:2]) or "documented thresholds and parameters"
        return (
            f"Distilled workflow for {capability.name} tasks with explicit trigger conditions, decision logic, terminology, quantitative signals, examples, and source-backed references. "
            f"Use when requests match scenarios such as: {trigger_text}. Preserve parameters such as: {metric_text}. "
            f"Do not use when the task falls outside these boundaries: {boundary_text}."
        )

    def _trigger_conditions(self, capability: CapabilityCluster, related: list[EvidenceRecord]) -> list[str]:
        items: list[str] = []
        items.extend(capability.core_tasks[:4])
        for evidence in related[:4]:
            items.append(evidence.subtask)
            items.extend(evidence.topic_modules[:2])
        return self._dedupe_nonempty(items, limit=8)

    def _workflow_outline(self, related: list[EvidenceRecord]) -> list[str]:
        items: list[str] = []
        for evidence in related:
            items.extend(evidence.workflow_steps)
            items.extend(evidence.dependencies[:2])
        return self._dedupe_nonempty(items, limit=10)

    def _decision_logic(self, capability: CapabilityCluster, related: list[EvidenceRecord]) -> list[str]:
        items: list[str] = []
        items.extend(capability.rules)
        for evidence in related:
            items.extend(evidence.decision_rules)
            items.extend(evidence.quantitative_signals[:2])
        return self._dedupe_nonempty(items, limit=12)

    def _boundaries(self, capability: CapabilityCluster, related: list[EvidenceRecord]) -> list[str]:
        items = [
            f"Use only for {capability.name} workflows evidenced in the source documents.",
            "Escalate or defer when required inputs, thresholds, terminology, or approval authority are missing.",
        ]
        for evidence in related[:3]:
            items.extend(evidence.exceptions[:1])
            items.append(f"Source scope: {evidence.source_path}")
        return self._dedupe_nonempty(items, limit=8)

    def _key_terms(self, related: list[EvidenceRecord]) -> list[str]:
        items: list[str] = []
        for evidence in related:
            items.extend(evidence.terminology)
        return self._dedupe_nonempty(items, limit=14)

    def _quantitative_signals(self, related: list[EvidenceRecord]) -> list[str]:
        items: list[str] = []
        for evidence in related:
            items.extend(evidence.quantitative_signals)
        return self._dedupe_nonempty(items, limit=12)

    def _dependencies(self, related: list[EvidenceRecord]) -> list[str]:
        items: list[str] = []
        for evidence in related:
            items.extend(evidence.dependencies)
        return self._dedupe_nonempty(items, limit=10)

    def _exceptions(self, related: list[EvidenceRecord]) -> list[str]:
        items: list[str] = []
        for evidence in related:
            items.extend(evidence.exceptions)
        return self._dedupe_nonempty(items, limit=10)

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

    def _extract_json_array(self, text: str) -> str:
        start = text.find("[")
        end = text.rfind("]")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("Model did not return JSON array")
        return text[start:end + 1]

    def _coerce_list(self, value: object, fallback: list[str]) -> list[str]:
        if isinstance(value, list):
            items = [str(item).strip()[:220] for item in value if str(item).strip()]
            if items:
                return items[:8]
        return fallback
