from __future__ import annotations

from pathlib import Path

from app.core.config import settings
from app.schemas.job import ExportResult, GeneratedSkill


class ExportService:
    def export_generated_skills(self, generated_skills: list[GeneratedSkill], output_dir: str, overwrite: bool = False) -> ExportResult:
        target_dir = self._resolve_output_dir(output_dir)
        conflicts = self.list_conflicts(generated_skills, output_dir)
        if conflicts and not overwrite:
            preview = ", ".join(conflicts[:5])
            if len(conflicts) > 5:
                preview = f"{preview}, ..."
            raise FileExistsError(f"Conflicting files already exist in {target_dir}: {preview}")
        target_dir.mkdir(parents=True, exist_ok=True)

        written_files: list[str] = []
        for skill in generated_skills:
            for generated_file in skill.files:
                destination = target_dir / generated_file.path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(generated_file.content, encoding="utf-8")
                written_files.append(str(destination))

        return ExportResult(
            output_dir=str(target_dir),
            written_files=written_files,
            skill_names=[skill.skill_name for skill in generated_skills],
        )

    def list_conflicts(self, generated_skills: list[GeneratedSkill], output_dir: str) -> list[str]:
        target_dir = self._resolve_output_dir(output_dir)
        conflicts: list[str] = []
        for skill in generated_skills:
            for generated_file in skill.files:
                destination = target_dir / generated_file.path
                if destination.exists():
                    conflicts.append(str(destination.relative_to(target_dir)))
        return conflicts

    def _resolve_output_dir(self, output_dir: str) -> Path:
        candidate = Path(output_dir)
        if candidate.is_absolute():
            return candidate
        return settings.export_dir / candidate
