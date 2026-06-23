import uuid
import os
import logging
import threading
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv(override=True)

from backend.src.api.telemetry import setup_telemetry
from backend.src.graph.workflow import app as compliance_graph
from backend.src.services.blob_service import BlobService
from backend.src.services.db_service import DbService
from backend.src.config import settings

setup_telemetry()

logging.basicConfig(level=logging.INFO)
logging.getLogger("azure").setLevel(logging.WARNING)
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
logger = logging.getLogger("pharma-review-api")

# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Pharma Video Ad Review API",
    description=(
        "AI-powered MLR compliance review for pharmaceutical video advertisements. "
        "Checks FDA 21 CFR Part 202 fair-balance, unsubstantiated claims, prohibited language, "
        "required disclosures, and visual-audio consistency."
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Services
blob_service = BlobService()
db_service = DbService()

# ---------------------------------------------------------------------------
# Frontend Route
# ---------------------------------------------------------------------------

@app.get("/")
async def serve_frontend(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

# ---------------------------------------------------------------------------
# In-memory store (REPLACED BY DB)
# ---------------------------------------------------------------------------

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "500"))
STAGING_CONTAINER = settings.AZURE_STORAGE_CONTAINER_NAME or "staging-uploads"


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------


class ComplianceIssue(BaseModel):
    category: str
    severity: str
    description: str
    timestamp: Optional[str] = "N/A"


class PharmaCheck(BaseModel):
    check_name: str
    passed: bool
    details: str
    severity: str


class AuditResponse(BaseModel):
    job_id: str
    status: str  # queued | processing | completed | failed
    video_name: Optional[str] = None
    final_status: Optional[str] = None  # PASS | WARN | FAIL
    final_report: Optional[str] = None
    compliance_issues: List[ComplianceIssue] = []
    pharma_checks: List[PharmaCheck] = []
    errors: List[str] = []


class DocumentIndexResponse(BaseModel):
    filename: str
    chunks_indexed: int
    status: str


class DocumentListResponse(BaseModel):
    sources: List[Dict[str, str]]
    total: int


# ---------------------------------------------------------------------------
# Background processing
# ---------------------------------------------------------------------------


def run_audit_job(job_id: str, blob_name: str, video_name: str):
    """Runs the LangGraph compliance workflow in a background thread."""
    try:
        db_service.update_job(job_id, {"status": "processing"})

        initial_state = {
            "job_id": job_id,
            "video_name": video_name,
            "blob_name": blob_name,
            "errors": [],
            "compliance_issues": [],
            "pharma_checks": [],
        }

        result = compliance_graph.invoke(initial_state)

        db_service.update_job(
            job_id,
            {
                "status": "completed",
                "final_status": result.get("final_status", "FAIL"),
                "final_report": result.get("final_report", ""),
                "compliance_issues": result.get("compliance_issues", []),
                "pharma_checks": result.get("pharma_checks", []),
                "errors": result.get("errors", []),
            }
        )

        logger.info(f"Job {job_id} completed with status: {result.get('final_status')}")

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        db_service.update_job(
            job_id,
            {
                "status": "failed",
                "errors": [str(e)],
                "final_status": "FAIL",
                "final_report": f"Audit pipeline failed: {str(e)}",
            }
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.post(
    "/api/audit",
    response_model=AuditResponse,
    summary="Submit a video or document for pharma compliance review",
)
async def submit_audit(
    background_tasks: BackgroundTasks,
    video_file: UploadFile = File(
        ..., description="Upload a video or document file (.mp4, .pdf, .docx, etc.)"
    ),
    video_name: Optional[str] = Form(
        None, description="Friendly name for the asset / campaign"
    ),
):
    """
    Submit a pharmaceutical video ad or document for AI-powered MLR compliance review.

    Upload a file (multipart/form-data).
    Returns a `job_id` immediately — poll `/api/status/{job_id}` for results.
    """
    job_id = str(uuid.uuid4())
    unique_suffix = uuid.uuid4().hex[:6]
    derived_name = f"{video_name or video_file.filename}_{unique_suffix}"

    content = await video_file.read()
    size_mb = len(content) / (1024 * 1024)

    if size_mb > MAX_UPLOAD_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {size_mb:.1f} MB. Maximum allowed: {MAX_UPLOAD_MB} MB.",
        )

    # Upload to Blob Storage
    blob_name = f"{job_id}_{video_file.filename}"
    blob_service.upload_blob(STAGING_CONTAINER, blob_name, content)

    logger.info(f"Job {job_id}: Staged uploaded file ({size_mb:.1f} MB) in Blob Storage -> {blob_name}")

    # Register job in DB
    db_service.create_job(job_id, derived_name)

    # Launch background thread
    thread = threading.Thread(
        target=run_audit_job,
        args=(job_id, blob_name, derived_name),
        daemon=True,
    )
    thread.start()

    logger.info(f"Job {job_id} queued for video: {derived_name}")

    return AuditResponse(
        job_id=job_id,
        status="queued",
        video_name=derived_name,
    )


@app.get(
    "/api/status/{job_id}",
    response_model=AuditResponse,
    summary="Poll audit job status",
)
async def get_audit_status(job_id: str):
    """
    Poll the status of a pharma compliance review job.
    """
    job = db_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")

    return AuditResponse(
        job_id=job_id,
        status=job["status"],
        video_name=job.get("video_name"),
        final_status=job.get("final_status"),
        final_report=job.get("final_report"),
        compliance_issues=job.get("compliance_issues", []),
        pharma_checks=job.get("pharma_checks", []),
        errors=job.get("errors", []),
    )


@app.get("/api/health", summary="Health check")
async def health_check():
    return {
        "status": "ok",
        "service": "Pharma Video Ad Review API",
        "version": "2.0.0",
    }


@app.get("/api/jobs", summary="List all active jobs")
async def list_jobs():
    """Returns summary of all jobs."""
    jobs = db_service.list_jobs()
    return [
        {"job_id": j["job_id"], "status": j["status"], "video_name": j.get("video_name")}
        for j in jobs
    ]


"""
To run:
    uv run uvicorn backend.src.api.server:app --reload

API Docs: http://localhost:8000/docs
"""
