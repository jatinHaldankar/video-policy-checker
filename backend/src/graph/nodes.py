import json
import logging

from backend.src.graph.state import VideoAuditState, ComplianceIssue, PharmaCheck
from backend.src.services.llm_service import LLMService
from backend.src.services.search_service import SearchService
from backend.src.services.video_indexer import VideoIndexerService
from backend.src.services.blob_service import BlobService
from backend.src.config import settings
from langchain_core.messages import SystemMessage, HumanMessage
import os
from pathlib import Path

video_index_name = settings.AZURE_SEARCH_VIDEO_INDEX_NAME

llm_service = LLMService()
llm = llm_service.get_llm()
search_service = SearchService(index_name=video_index_name)
blob_service = BlobService()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

video_index_name = settings.AZURE_SEARCH_VIDEO_INDEX_NAME

# Lazy-initialized services — created on first use, NOT at import time.
# This prevents the server from crashing at startup if credentials are missing.
_llm_service = None
_llm = None
_search_service = None
blob_service = BlobService()


def _get_llm_service():
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


def _get_llm():
    global _llm
    if _llm is None:
        _llm = _get_llm_service().get_llm()
    return _llm


def _get_search_service():
    global _search_service
    if _search_service is None:
        _search_service = SearchService(index_name=video_index_name)
    return _search_service



# ---------------------------------------------------------------------------
# Node 1 — Upload & Index Video
# ---------------------------------------------------------------------------


def upload_node(state: VideoAuditState) -> dict:
    """
    Accepts a blob name (state['blob_name']) from Azure Storage staging.
    Processes either video (Azure VI) or document (Azure Doc Intelligence).
    """
    video_name = state.get("video_name", "pharma_review_asset")
    blob_name = state.get("blob_name")
    staging_container = settings.AZURE_STORAGE_CONTAINER_NAME or "staging-uploads"

    try:
        if not blob_name:
            raise ValueError("No blob name provided for processing.")

        logger.info(f"Processing staged blob: {blob_name}")
        ext = os.path.splitext(blob_name)[1].lower()
        video_exts = [".mp4", ".mov", ".avi", ".mkv", ".wmv"]
        doc_exts = [
            ".pdf",
            ".docx",
            ".doc",
            ".txt",
            ".jpg",
            ".jpeg",
            ".png",
            ".ppt",
            ".pptx",
            ".xls",
            ".xlsx",
        ]

        if ext in video_exts:
            vi_service = VideoIndexerService()

            # --- Generate SAS URL for Video Indexer ---
            sas_url = blob_service.generate_sas_url(staging_container, blob_name)

            # --- Upload to Azure Video Indexer via URL ---
            azure_vi_id = vi_service.upload_video_from_url(sas_url, video_name)
            logger.info(f"Video uploaded via SAS URL. Azure VI ID: {azure_vi_id}")

            # --- Wait for indexing ---
            raw_data = vi_service.process_video(azure_vi_id)
            logger.info("Video processing complete.")

            # --- Extract insights ---
            extracted = vi_service.extract_data(raw_data)
            return {
                "video_id": azure_vi_id,
                **extracted,
            }

        elif ext in doc_exts:
            from backend.src.services.doc_intel_service import (
                DocumentIntelligenceService,
            )

            doc_intel = DocumentIntelligenceService()

            logger.info(f"Downloading document from Blob Storage...")
            content = blob_service.download_blob(staging_container, blob_name)

            logger.info(
                f"Extracting document text using Azure Document Intelligence..."
            )
            extracted_text = doc_intel.extract_text(content, blob_name)

            return {
                "video_id": "document_upload",
                "transcript": extracted_text,
                "ocr_text": "",
            }
        else:
            raise ValueError(f"Unsupported extension: {ext}")

    except Exception as e:
        logger.error(f"upload_node error: {e}")
        return {
            "errors": [str(e)],
            "final_status": "FAIL",
            "transcript": "",
            "ocr_text": "",
        }


# ---------------------------------------------------------------------------
# Node 2 — Pharma Compliance Audit (RAG + LLM)
# ---------------------------------------------------------------------------


def _load_prompt(filename: str) -> str:
    """Helper to load prompt templates from the prompts directory."""
    try:
        # Use absolute path relative to this file
        base_path = Path(__file__).parent.parent / "prompts"
        prompt_path = base_path / filename
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to load prompt {filename}: {e}")
        return "You are a helpful assistant. Evaluation failed due to missing prompt template."


def pharma_audit_node(state: VideoAuditState) -> dict:
    """
    Performs RAG-augmented FDA pharma compliance audit on the extracted
    video transcript and OCR text.
    """
    transcript = state.get("transcript", "")

    if not transcript:
        logger.warning("No transcript available. Skipping pharma audit.")
        return {
            "final_status": "FAIL",
            "final_report": "Audit skipped: video processing produced no transcript.",
            "compliance_issues": [],
            "pharma_checks": [],
        }

    ocr_text = state.get("ocr_text", "")
    video_metadata = state.get("video_metadata", {})

    # --- RAG: retrieve relevant regulations ---

    query_context = (transcript + " " + ocr_text)[:500]
    query = (
        f"pharmaceutical drug advertisement FDA compliance requirements {query_context}"
    )

    embedding = _get_llm_service().embed_text(query)
    docs = _get_search_service().hybrid_search(query, embedding)

    retrieved_rules = ""
    for doc in docs:
        content = (
            doc.get("content", "")
            if isinstance(doc, dict)
            else getattr(doc, "content", "")
        )
        retrieved_rules += content + "\n\n"

    if not retrieved_rules.strip():
        retrieved_rules = (
            "No specific regulations retrieved. Apply standard FDA 21 CFR Part 202 "
            "direct-to-consumer advertising rules and ICH guidelines."
        )

    # --- Build LLM messages ---
    is_document = state.get("video_id") == "document_upload"
    prompt_file = "pharma_doc_audit.txt" if is_document else "pharma_video_audit.txt"
    prompt_template = _load_prompt(prompt_file)

    system_message = SystemMessage(
        content=prompt_template.format(retrieved_rules=retrieved_rules)
    )

    human_message = HumanMessage(
        content=f"""
VIDEO METADATA: {json.dumps(video_metadata, indent=2)}

TRANSCRIPT:
{transcript}

ON-SCREEN TEXT (OCR):
{ocr_text}
"""
    )

    try:
        response = _get_llm().invoke([system_message, human_message])
        raw = response.content.strip()

        # Strip markdown code fences if LLM wraps response
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        audit_data = json.loads(raw)

        return {
            "compliance_issues": audit_data.get("compliance_issues", []),
            "pharma_checks": audit_data.get("pharma_checks", []),
            "final_status": audit_data.get("status", "FAIL"),
            "final_report": audit_data.get("final_report", "No report generated."),
        }

    except json.JSONDecodeError as je:
        logger.error(f"JSON parse error from LLM: {je}")
        return {
            "final_status": "FAIL",
            "final_report": f"Audit failed: LLM returned invalid JSON. Raw: {raw[:200]}",
            "compliance_issues": [],
            "pharma_checks": [],
        }
    except Exception as e:
        logger.error(f"pharma_audit_node error: {e}")
        return {
            "final_status": "FAIL",
            "final_report": f"Audit failed: {str(e)}",
            "compliance_issues": [],
            "pharma_checks": [],
        }


# ---------------------------------------------------------------------------
# Node 3 — Cleanup (Cloud-Native)
# ---------------------------------------------------------------------------


def cleanup_node(state: VideoAuditState) -> dict:
    """
    Deletes the staged blob from Azure Storage once processing is finished.
    """
    blob_name = state.get("blob_name")
    staging_container = settings.AZURE_STORAGE_CONTAINER_NAME or "staging-uploads"

    if blob_name:
        logger.info(f"Cleaning up staged blob: {blob_name}")
        blob_service.delete_blob(staging_container, blob_name)

    return {}
