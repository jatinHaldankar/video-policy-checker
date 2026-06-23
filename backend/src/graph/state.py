from typing import TypedDict, Optional, Any, Dict, List, Annotated
from pydantic import Field
import operator


class ComplianceIssue(TypedDict):
    category: str
    severity: str
    description: str
    timestamp: Optional[str]


class PharmaCheck(TypedDict):
    """Pharma-specific compliance check result."""
    check_name: str
    passed: bool
    details: str
    severity: str  # CRITICAL | HIGH | MEDIUM | LOW


class VideoAuditState(TypedDict):
    # Job tracking
    job_id: str
    video_name: str
    file_path: Optional[str]          # local temp path for uploaded file
    blob_name: Optional[str]          # name of the blob if staged in cloud

    # Video Indexer output
    video_id: Optional[str]           # Azure VI video ID
    video_metadata: Optional[Dict[str, Any]]
    transcript: str
    ocr_text: str

    # Pharma-specific checks
    pharma_checks: Annotated[
        List[PharmaCheck],
        operator.add,
    ]

    # Compliance output
    compliance_issues: Annotated[
        List[ComplianceIssue],
        operator.add,
    ]
    final_status: str      # PASS | WARN | FAIL
    final_report: str

    # Errors
    errors: Annotated[
        List[str],
        operator.add,
    ]
