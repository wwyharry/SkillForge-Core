from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.schemas.job import JobCreate, JobMode
from app.schemas.model_config import ModelApiConfigForm
from app.services.exporter import ExportService
from app.services.jobs import JobService
from app.services.model_config import ModelConfigService

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="app/templates")
service = JobService()
exporter = ExportService()
model_config_service = ModelConfigService()

TERMINAL_STATUSES = {"completed", "failed"}


def _render_template(request: Request, name: str, context: dict) -> HTMLResponse:
    payload = {"request": request, **context}
    return HTMLResponse(templates.get_template(name).render(payload))


def _status_tone(status: str) -> str:
    if status == "failed":
        return "status-failed"
    if status == "completed":
        return "status-completed"
    if status == "queued":
        return "status-queued"
    return "status-running"


def _status_label(status: str) -> str:
    if status == "failed":
        return "Needs retry"
    if status == "completed":
        return "Ready to export"
    if status == "queued":
        return "Waiting in queue"
    return "Pipeline active"


def _summary_cards(jobs: list) -> list[dict[str, str]]:
    active = [job for job in jobs if job.status.value not in TERMINAL_STATUSES]
    completed = [job for job in jobs if job.status.value == "completed"]
    failed = [job for job in jobs if job.status.value == "failed"]
    average = round(sum(job.progress for job in jobs) / len(jobs)) if jobs else 0
    return [
        {"label": "Total Jobs", "value": str(len(jobs)), "detail": "All distillation runs tracked locally."},
        {"label": "Active Jobs", "value": str(len(active)), "detail": "Jobs still scanning, parsing, extracting, or compiling."},
        {"label": "Completed Jobs", "value": str(len(completed)), "detail": "Jobs with generated skill previews ready for review."},
        {"label": "Failed Jobs", "value": str(len(failed)), "detail": "Jobs that need retry or root-cause review."},
        {"label": "Average Progress", "value": f"{average}%", "detail": "Average pipeline completion across all recorded jobs."},
    ]


def _redirect_to_job(job_id: str, params: dict[str, str | int] | None = None) -> RedirectResponse:
    url = f"/jobs/{job_id}"
    if params:
        filtered = {key: value for key, value in params.items() if value not in (None, "")}
        if filtered:
            url = f"{url}?{urlencode(filtered)}"
    return RedirectResponse(url=url, status_code=303)


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    jobs = service.list_jobs()
    return _render_template(
        request,
        "dashboard.html",
        {
            "jobs": jobs[:8],
            "cards": _summary_cards(jobs),
            "status_tone": _status_tone,
            "status_label": _status_label,
        },
    )


@router.get("/settings/model-api", response_class=HTMLResponse)
def model_api_settings_page(request: Request, saved: int = 0):
    config = model_config_service.masked()
    if not config["extra_headers"]:
        config["extra_headers"] = [{"name": "", "value": ""}]
    return _render_template(
        request,
        "settings_model_api.html",
        {
            "config": config,
            "saved": saved == 1,
        },
    )


@router.post("/settings/model-api")
def save_model_api_settings(
    provider: str = Form("openai-compatible"),
    base_url: str = Form(""),
    api_key: str = Form(""),
    model_name: str = Form(""),
    embedding_model: str = Form(""),
    deployment_name: str = Form(""),
    api_version: str = Form(""),
    organization: str = Form(""),
    project: str = Form(""),
    timeout_seconds: int = Form(120),
    max_tokens: int = Form(4096),
    temperature: float = Form(0.2),
    top_p: float = Form(1.0),
    enabled: str | None = Form(default=None),
    verify_ssl: str | None = Form(default=None),
    use_streaming: str | None = Form(default=None),
    notes: str = Form(""),
    extra_header_names: list[str] = Form(default=[]),
    extra_header_values: list[str] = Form(default=[]),
):
    existing = model_config_service.get()
    form = ModelApiConfigForm(
        provider=provider,
        base_url=base_url,
        api_key=api_key or existing.api_key,
        model_name=model_name,
        embedding_model=embedding_model,
        deployment_name=deployment_name,
        api_version=api_version,
        organization=organization,
        project=project,
        timeout_seconds=timeout_seconds,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        enabled=enabled == "on",
        verify_ssl=verify_ssl == "on",
        use_streaming=use_streaming == "on",
        notes=notes,
        extra_header_names=extra_header_names,
        extra_header_values=extra_header_values,
    )
    model_config_service.save(form.to_config())
    return RedirectResponse(url="/settings/model-api?saved=1", status_code=303)


@router.get("/jobs/new", response_class=HTMLResponse)
def new_job_page(request: Request):
    return _render_template(
        request,
        "job_new.html",
        {"modes": [JobMode.explore.value, JobMode.compile.value]},
    )


@router.post("/jobs/new")
def create_job(
    name: str = Form(...),
    root_path: str = Form(...),
    goal: str = Form(...),
    mode: str = Form(JobMode.explore.value),
):
    job = service.create_job(JobCreate(name=name, root_path=root_path, goal=goal, mode=JobMode(mode)))
    return _redirect_to_job(job.id)


@router.get("/jobs/{job_id}", response_class=HTMLResponse)
def job_detail(request: Request, job_id: str, exported: int = 0, export_error: str = "", export_conflicts: int = 0):
    try:
        job = service.get_job(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc
    return _render_template(
        request,
        "job_detail.html",
        {
            "job": job,
            "exported": exported == 1,
            "export_error": export_error,
            "export_conflicts": export_conflicts == 1,
            "terminal_statuses": TERMINAL_STATUSES,
        },
    )


@router.post("/jobs/{job_id}/run")
def run_job_action(job_id: str):
    try:
        service.run_job(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc
    return _redirect_to_job(job_id)


@router.post("/jobs/{job_id}/retry")
def retry_job_action(job_id: str):
    try:
        service.run_job(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc
    return _redirect_to_job(job_id)


@router.post("/jobs/{job_id}/dispatch")
def dispatch_job_action(job_id: str):
    try:
        service.dispatch_job(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc
    return _redirect_to_job(job_id)


@router.get("/dialog/repository-directory")
def pick_repository_directory(current: str = ""):
    return pick_export_directory(current)


@router.get("/dialog/export-directory")
def pick_export_directory(current: str = ""):
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        initial_dir = ""
        if current:
            candidate = Path(current)
            initial_dir = str(candidate if candidate.is_dir() else candidate.parent)
        selected = filedialog.askdirectory(initialdir=initial_dir or None, mustexist=False)
        root.destroy()
        return JSONResponse({"ok": True, "path": selected or ""})
    except Exception as exc:
        return JSONResponse({"ok": False, "detail": str(exc)}, status_code=500)


@router.post("/jobs/{job_id}/export")
def export_job(job_id: str, output_dir: str = Form(...), overwrite: str | None = Form(default=None)):
    try:
        job = service.get_job(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc
    if not job.generated_skills:
        raise HTTPException(status_code=400, detail="No generated skills available for export")

    overwrite_flag = overwrite == "on"
    conflicts = exporter.list_conflicts(job.generated_skills, output_dir)
    if conflicts and not overwrite_flag:
        return JSONResponse(
            {
                "ok": False,
                "requires_confirmation": True,
                "detail": "Destination already contains one or more files.",
                "conflicts": conflicts,
            },
            status_code=200,
        )

    try:
        result = exporter.export_generated_skills(job.generated_skills, output_dir=output_dir, overwrite=overwrite_flag)
    except ValueError as exc:
        return JSONResponse({"ok": False, "detail": str(exc)}, status_code=400)
    except FileExistsError as exc:
        return JSONResponse(
            {
                "ok": False,
                "requires_confirmation": True,
                "detail": str(exc),
                "conflicts": conflicts,
            },
            status_code=200,
        )

    return JSONResponse(
        {
            "ok": True,
            "message": f"Generated skills exported to {result.output_dir}.",
            "output_dir": result.output_dir,
            "written_files": result.written_files,
            "skill_names": result.skill_names,
        }
    )
